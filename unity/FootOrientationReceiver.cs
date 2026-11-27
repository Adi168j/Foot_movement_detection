using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// FootOrientationReceiver — Mirrors the physical slipper orientation in Unity.
/// 
/// Receives "pitch,roll,yaw,label,confidence[,angvel]" from stream_orientation.py via UDP.
/// The 3D slipper rotates in real-time to match the physical slipper.
/// 
/// Setup:
///   1. Create empty GameObject, attach this script
///   2. Run: py stream_orientation.py
///   3. Press Play in Unity
///   4. Move your slipper — the 3D model follows!
/// </summary>
public class FootOrientationReceiver : MonoBehaviour
{
    [Header("Network")]
    public int listenPort = 5065;

    [Header("Smoothing")]
    [Range(0.02f, 0.3f)]
    [Tooltip("Lower = snappier, Higher = smoother. Try 0.08 for responsive, 0.15 for smooth.")]
    public float smoothTime = 0.08f;

    [Header("Orientation (read-only)")]
    public float pitch;
    public float roll;
    public float yaw;
    public string movementLabel = "still";
    public float confidence = 0f;
    public float angularVelocity = 0f;

    [Header("Colors per Movement")]
    public Color stillColor      = new Color(0.3f, 0.8f, 0.3f);
    public Color heelstrikeColor = new Color(0.9f, 0.3f, 0.3f);
    public Color toeoffColor     = new Color(0.3f, 0.3f, 0.9f);
    public Color stepColor       = new Color(0.9f, 0.6f, 0.1f);
    public Color rollleftColor   = new Color(0.8f, 0.2f, 0.8f);
    public Color rollrightColor  = new Color(0.2f, 0.8f, 0.8f);
    public Color twistColor      = new Color(0.9f, 0.9f, 0.2f);

    // Internal
    private float _targetPitch, _targetRoll, _targetYaw;
    private float _pendingAngVel;
    private string _pendingLabel;
    private float _pendingConf;
    private bool _hasPending;
    private readonly object _lock = new object();

    private UdpClient _udpClient;
    private Thread _receiveThread;
    private bool _running = true;

    private Transform _slipperTransform;
    private Renderer[] _renderers;

    // SmoothDamp velocities (for natural springy motion)
    private float _velPitch, _velRoll, _velYaw;

    void Start()
    {
        CreateSlipper();

        _udpClient = new UdpClient(listenPort);
        _receiveThread = new Thread(ReceiveLoop) { IsBackground = true };
        _receiveThread.Start();
        Debug.Log($"[FootOrientation] Listening on UDP port {listenPort}");
    }

    void CreateSlipper()
    {
        // Pivot object (this is what rotates)
        GameObject pivot = new GameObject("SlipperPivot");
        pivot.transform.SetParent(transform);
        pivot.transform.localPosition = Vector3.zero;
        _slipperTransform = pivot.transform;

        // Sole
        GameObject sole = GameObject.CreatePrimitive(PrimitiveType.Cube);
        sole.name = "Sole";
        sole.transform.SetParent(pivot.transform);
        sole.transform.localPosition = Vector3.zero;
        sole.transform.localScale = new Vector3(0.5f, 0.06f, 1.0f);

        // Toe area
        GameObject toe = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        toe.name = "Toe";
        toe.transform.SetParent(pivot.transform);
        toe.transform.localPosition = new Vector3(0f, 0.02f, 0.42f);
        toe.transform.localScale = new Vector3(0.45f, 0.08f, 0.25f);

        // Heel bump
        GameObject heel = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        heel.name = "Heel";
        heel.transform.SetParent(pivot.transform);
        heel.transform.localPosition = new Vector3(0f, 0.02f, -0.42f);
        heel.transform.localScale = new Vector3(0.35f, 0.08f, 0.2f);

        // Strap
        GameObject strap = GameObject.CreatePrimitive(PrimitiveType.Cube);
        strap.name = "Strap";
        strap.transform.SetParent(pivot.transform);
        strap.transform.localPosition = new Vector3(0f, 0.1f, 0.1f);
        strap.transform.localScale = new Vector3(0.48f, 0.04f, 0.15f);

        // Sensor dots (red spheres showing where IMUs are)
        CreateSensor(pivot.transform, "S0", new Vector3(0f, 0.04f, 0.3f));
        CreateSensor(pivot.transform, "S1", new Vector3(0f, 0.04f, 0f));
        CreateSensor(pivot.transform, "S2", new Vector3(0f, 0.04f, -0.3f));

        // Direction arrow (shows front of slipper)
        GameObject arrow = GameObject.CreatePrimitive(PrimitiveType.Cube);
        arrow.name = "FrontArrow";
        arrow.transform.SetParent(pivot.transform);
        arrow.transform.localPosition = new Vector3(0f, 0.04f, 0.55f);
        arrow.transform.localScale = new Vector3(0.08f, 0.02f, 0.1f);
        arrow.GetComponent<Renderer>().material.color = Color.white;

        _renderers = pivot.GetComponentsInChildren<Renderer>();

        // Floor grid reference
        GameObject floor = GameObject.CreatePrimitive(PrimitiveType.Plane);
        floor.name = "Floor";
        floor.transform.SetParent(transform);
        floor.transform.localPosition = new Vector3(0f, -0.5f, 0f);
        floor.transform.localScale = new Vector3(0.3f, 1f, 0.3f);
        floor.GetComponent<Renderer>().material.color = new Color(0.15f, 0.15f, 0.15f);
    }

    void CreateSensor(Transform parent, string sensorName, Vector3 pos)
    {
        GameObject s = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        s.name = sensorName;
        s.transform.SetParent(parent);
        s.transform.localPosition = pos;
        s.transform.localScale = new Vector3(0.06f, 0.06f, 0.06f);
        s.GetComponent<Renderer>().material.color = Color.red;
        // No collision needed
        Destroy(s.GetComponent<Collider>());
    }

    void Update()
    {
        // Read latest data from network thread
        lock (_lock)
        {
            if (_hasPending)
            {
                movementLabel = _pendingLabel;
                confidence = _pendingConf;
                angularVelocity = _pendingAngVel;
                _hasPending = false;
            }
        }

        // SmoothDamp interpolation — much more natural than Lerp
        // Gives springy, responsive motion with natural deceleration
        pitch = Mathf.SmoothDamp(pitch, _targetPitch, ref _velPitch, smoothTime);
        roll  = Mathf.SmoothDamp(roll,  _targetRoll,  ref _velRoll,  smoothTime);
        yaw   = Mathf.SmoothDamp(yaw,   _targetYaw,   ref _velYaw,   smoothTime);

        // Apply rotation: pitch = X, yaw = Y, roll = Z
        // Python already maps IMU axes to Unity axes, so apply directly
        _slipperTransform.localRotation = Quaternion.Euler(pitch, yaw, roll);

        // Color based on movement
        Color targetColor = GetMovementColor(movementLabel);
        foreach (Renderer r in _renderers)
        {
            if (r.gameObject.name.StartsWith("S") || r.gameObject.name == "FrontArrow")
                continue;
            r.material.color = Color.Lerp(r.material.color, targetColor, Time.deltaTime * 5f);
        }
    }

    Color GetMovementColor(string movement)
    {
        switch (movement)
        {
            case "still":      return stillColor;
            case "heelstrike": return heelstrikeColor;
            case "toeoff":     return toeoffColor;
            case "step":       return stepColor;
            case "rollleft":   return rollleftColor;
            case "rollright":  return rollrightColor;
            case "twist":      return twistColor;
            default:           return Color.gray;
        }
    }

    private void ReceiveLoop()
    {
        IPEndPoint remoteEP = new IPEndPoint(IPAddress.Any, 0);
        while (_running)
        {
            try
            {
                byte[] data = _udpClient.Receive(ref remoteEP);
                string msg = Encoding.UTF8.GetString(data);

                // Parse "pitch,roll,yaw,label,confidence[,angvel]"
                string[] parts = msg.Split(',');
                if (parts.Length >= 5)
                {
                    float p = 0f, r = 0f, y = 0f, c = 0f, av = 0f;
                    float.TryParse(parts[0], System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out p);
                    float.TryParse(parts[1], System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out r);
                    float.TryParse(parts[2], System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out y);
                    float.TryParse(parts[4], System.Globalization.NumberStyles.Float,
                        System.Globalization.CultureInfo.InvariantCulture, out c);

                    // Angular velocity (optional 6th field)
                    if (parts.Length >= 6)
                    {
                        float.TryParse(parts[5], System.Globalization.NumberStyles.Float,
                            System.Globalization.CultureInfo.InvariantCulture, out av);
                    }

                    _targetPitch = p;
                    _targetRoll  = r;
                    _targetYaw   = y;

                    lock (_lock)
                    {
                        _pendingLabel = parts[3].Trim();
                        _pendingConf  = c;
                        _pendingAngVel = av;
                        _hasPending   = true;
                    }
                }
            }
            catch (SocketException) { break; }
            catch (Exception e)
            {
                Debug.LogWarning($"[FootOrientation] Error: {e.Message}");
            }
        }
    }

    void OnGUI()
    {

        // Orientation values
        GUIStyle dataStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 16,
            alignment = TextAnchor.MiddleLeft
        };
        dataStyle.normal.textColor = new Color(1f, 1f, 1f, 0.7f);
        GUI.Label(new Rect(15, Screen.height - 80, 300, 25),
            $"Pitch: {pitch:+0.0;-0.0}°", dataStyle);
        GUI.Label(new Rect(15, Screen.height - 55, 300, 25),
            $"Roll:  {roll:+0.0;-0.0}°", dataStyle);
        GUI.Label(new Rect(15, Screen.height - 30, 300, 25),
            $"Yaw:   {yaw:+0.0;-0.0}°", dataStyle);

        // Instructions
        GUIStyle instrStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 14,
            alignment = TextAnchor.LowerRight
        };
        instrStyle.normal.textColor = new Color(1f, 1f, 1f, 0.4f);
        GUI.Label(new Rect(0, Screen.height - 30, Screen.width - 15, 25),
            "py stream_orientation.py", instrStyle);
    }

    void OnDestroy()
    {
        _running = false;
        _udpClient?.Close();
        _receiveThread?.Join(500);
    }
}
