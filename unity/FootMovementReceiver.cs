using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// FootMovementReceiver — Receives movement predictions from predict_live.py via UDP.
/// 
/// Setup:
///   1. Create an empty GameObject in Unity
///   2. Attach this script to it
///   3. Run: py predict_live.py --unity
///   4. Predictions arrive as events you can use to trigger animations/haptics
///   
/// The Python script sends "label,confidence" (e.g. "heelstrike,0.93") to UDP port 5065.
/// </summary>
public class FootMovementReceiver : MonoBehaviour
{
    [Header("Network Settings")]
    public int listenPort = 5065;

    [Header("Current Prediction (read-only)")]
    public string currentMovement = "still";
    public float  currentConfidence = 0f;
    public string previousMovement = "still";

    // Thread-safe message passing
    private string _pendingLabel = null;
    private float  _pendingConf  = 0f;
    private readonly object _lock = new object();

    private UdpClient _udpClient;
    private Thread    _receiveThread;
    private bool      _running = true;

    void Start()
    {
        _udpClient = new UdpClient(listenPort);
        _receiveThread = new Thread(ReceiveLoop)
        {
            IsBackground = true
        };
        _receiveThread.Start();
        Debug.Log($"[FootMovement] Listening on UDP port {listenPort}");
    }

    void Update()
    {
        // Check for new predictions on the main thread
        lock (_lock)
        {
            if (_pendingLabel != null)
            {
                previousMovement  = currentMovement;
                currentMovement   = _pendingLabel;
                currentConfidence = _pendingConf;
                _pendingLabel     = null;

                if (currentMovement != previousMovement)
                {
                    Debug.Log($"[FootMovement] {currentMovement} ({currentConfidence:P0})");
                    OnMovementChanged(currentMovement, currentConfidence);
                }
            }
        }
    }

    /// <summary>
    /// Called on the main thread whenever the predicted movement changes.
    /// Override or extend this to trigger your own logic.
    /// </summary>
    protected virtual void OnMovementChanged(string movement, float confidence)
    {
        // Example: trigger animations, haptics, or game events based on movement
        //
        // switch (movement)
        // {
        //     case "heelstrike": TriggerHaptic(0.8f); break;
        //     case "toeoff":     PlayAnimation("toeoff"); break;
        //     case "rollleft":   TiltPlatform(-15f); break;
        //     case "rollright":  TiltPlatform(15f); break;
        //     case "twist":      RotatePlatform(); break;
        //     case "step":       PlayStepSound(); break;
        //     case "still":      ResetPose(); break;
        // }
    }

    private void ReceiveLoop()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);

        while (_running)
        {
            try
            {
                byte[] data = _udpClient.Receive(ref remoteEP);
                string msg  = Encoding.UTF8.GetString(data);

                // Parse "label,confidence"
                string[] parts = msg.Split(',');
                if (parts.Length >= 2)
                {
                    string label = parts[0].Trim();
                    float  conf  = 0f;
                    float.TryParse(parts[1].Trim(), out conf);

                    lock (_lock)
                    {
                        _pendingLabel = label;
                        _pendingConf  = conf;
                    }
                }
            }
            catch (SocketException)
            {
                // Socket closed during shutdown
                break;
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[FootMovement] Receive error: {e.Message}");
            }
        }
    }

    void OnDestroy()
    {
        _running = false;
        _udpClient?.Close();
        _receiveThread?.Join(500);
        Debug.Log("[FootMovement] Stopped.");
    }
}
