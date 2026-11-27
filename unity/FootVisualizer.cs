using UnityEngine;

/// <summary>
/// FootVisualizer — Animates a 3D slipper model based on movement predictions.
/// 
/// Attach to the same GameObject as FootMovementReceiver.
/// The script will create a simple slipper shape automatically if no model is assigned.
/// </summary>
[RequireComponent(typeof(FootMovementReceiver))]
public class FootVisualizer : MonoBehaviour
{
    [Header("Visual Settings")]
    public float animationSpeed = 5f;
    public float tiltAngle = 25f;
    public float stepHeight = 0.3f;
    public float twistAngle = 30f;

    [Header("Colors")]
    public Color stillColor      = new Color(0.3f, 0.8f, 0.3f);  // green
    public Color heelstrikeColor = new Color(0.9f, 0.3f, 0.3f);  // red
    public Color toeoffColor     = new Color(0.3f, 0.3f, 0.9f);  // blue
    public Color stepColor       = new Color(0.9f, 0.6f, 0.1f);  // orange
    public Color rollleftColor   = new Color(0.8f, 0.2f, 0.8f);  // purple
    public Color rollrightColor  = new Color(0.2f, 0.8f, 0.8f);  // cyan
    public Color twistColor      = new Color(0.9f, 0.9f, 0.2f);  // yellow

    private FootMovementReceiver _receiver;
    private Transform _slipperTransform;
    private Renderer  _slipperRenderer;
    private Transform _labelTransform;

    // Target pose
    private Vector3    _targetRotation = Vector3.zero;
    private Vector3    _targetPosition = Vector3.zero;
    private Color      _targetColor    = Color.green;
    private float      _stepTimer      = 0f;

    // UI
    private string _displayLabel = "Waiting...";
    private float  _displayConf  = 0f;

    void Start()
    {
        _receiver = GetComponent<FootMovementReceiver>();
        CreateSlipperModel();
    }

    void CreateSlipperModel()
    {
        // Create a slipper-like shape from primitives
        // Main sole (flattened cube)
        GameObject sole = GameObject.CreatePrimitive(PrimitiveType.Cube);
        sole.name = "SlipperSole";
        sole.transform.SetParent(transform);
        sole.transform.localPosition = Vector3.zero;
        sole.transform.localScale = new Vector3(0.4f, 0.05f, 0.8f);  // wide, thin, long

        // Toe cap (half sphere at front)
        GameObject toe = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        toe.name = "SlipperToe";
        toe.transform.SetParent(sole.transform);
        toe.transform.localPosition = new Vector3(0f, 0.3f, 0.45f);
        toe.transform.localScale = new Vector3(0.9f, 0.6f, 0.4f);

        // Heel bump
        GameObject heel = GameObject.CreatePrimitive(PrimitiveType.Sphere);
        heel.name = "SlipperHeel";
        heel.transform.SetParent(sole.transform);
        heel.transform.localPosition = new Vector3(0f, 0.2f, -0.45f);
        heel.transform.localScale = new Vector3(0.7f, 0.4f, 0.3f);

        // Sensor indicators (3 small spheres)
        string[] sensorNames = { "S0 (front)", "S1 (mid)", "S2 (back)" };
        float[] zPositions   = { 0.3f, 0f, -0.3f };
        for (int i = 0; i < 3; i++)
        {
            GameObject sensor = GameObject.CreatePrimitive(PrimitiveType.Sphere);
            sensor.name = sensorNames[i];
            sensor.transform.SetParent(sole.transform);
            sensor.transform.localPosition = new Vector3(0f, 1.2f, zPositions[i]);
            sensor.transform.localScale = new Vector3(0.15f, 0.15f, 0.15f);
            sensor.GetComponent<Renderer>().material.color = Color.red;
        }

        _slipperTransform = sole.transform;
        _slipperRenderer  = sole.GetComponent<Renderer>();

        // Set initial color
        SetAllColors(stillColor);
    }

    void Update()
    {
        string movement = _receiver.currentMovement;
        float  conf     = _receiver.currentConfidence;

        // Update target pose based on movement
        switch (movement)
        {
            case "still":
                _targetRotation = Vector3.zero;
                _targetPosition = Vector3.zero;
                _targetColor = stillColor;
                _displayLabel = "STILL";
                break;

            case "heelstrike":
                _targetRotation = new Vector3(-tiltAngle, 0f, 0f);  // tip forward (heel down)
                _targetPosition = new Vector3(0f, -0.1f, 0f);
                _targetColor = heelstrikeColor;
                _displayLabel = "HEEL STRIKE";
                break;

            case "toeoff":
                _targetRotation = new Vector3(tiltAngle, 0f, 0f);  // tip backward (toe down)
                _targetPosition = new Vector3(0f, 0.1f, 0f);
                _targetColor = toeoffColor;
                _displayLabel = "TOE OFF";
                break;

            case "step":
                _stepTimer += Time.deltaTime * 3f;
                float bob = Mathf.Abs(Mathf.Sin(_stepTimer)) * stepHeight;
                _targetRotation = new Vector3(Mathf.Sin(_stepTimer) * 15f, 0f, 0f);
                _targetPosition = new Vector3(0f, bob, 0f);
                _targetColor = stepColor;
                _displayLabel = "STEPPING";
                break;

            case "rollleft":
                _targetRotation = new Vector3(0f, 0f, tiltAngle);  // roll left
                _targetPosition = Vector3.zero;
                _targetColor = rollleftColor;
                _displayLabel = "ROLL LEFT";
                break;

            case "rollright":
                _targetRotation = new Vector3(0f, 0f, -tiltAngle); // roll right
                _targetPosition = Vector3.zero;
                _targetColor = rollrightColor;
                _displayLabel = "ROLL RIGHT";
                break;

            case "twist":
                _stepTimer += Time.deltaTime * 4f;
                _targetRotation = new Vector3(0f, Mathf.Sin(_stepTimer) * twistAngle, 0f);
                _targetPosition = Vector3.zero;
                _targetColor = twistColor;
                _displayLabel = "TWIST";
                break;

            default:
                _displayLabel = movement.ToUpper();
                break;
        }

        _displayConf = conf;

        // Reset step timer when not stepping/twisting
        if (movement != "step" && movement != "twist")
            _stepTimer = 0f;

        // Smooth animation
        Quaternion targetQuat = Quaternion.Euler(_targetRotation);
        _slipperTransform.localRotation = Quaternion.Slerp(
            _slipperTransform.localRotation, targetQuat, Time.deltaTime * animationSpeed);
        _slipperTransform.localPosition = Vector3.Lerp(
            _slipperTransform.localPosition, _targetPosition, Time.deltaTime * animationSpeed);

        // Smooth color
        SetAllColors(Color.Lerp(_slipperRenderer.material.color, _targetColor, Time.deltaTime * animationSpeed));
    }

    void SetAllColors(Color color)
    {
        foreach (Renderer r in GetComponentsInChildren<Renderer>())
        {
            if (!r.gameObject.name.StartsWith("S"))  // don't color sensor indicators
                r.material.color = color;
        }
    }

    void OnGUI()
    {
        // Big label at top of screen
        GUIStyle titleStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 48,
            fontStyle = FontStyle.Bold,
            alignment = TextAnchor.MiddleCenter
        };
        titleStyle.normal.textColor = Color.white;

        GUIStyle subStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 24,
            alignment = TextAnchor.MiddleCenter
        };
        subStyle.normal.textColor = Color.gray;

        // Draw shadow + text
        Rect titleRect = new Rect(0, 20, Screen.width, 60);
        GUI.Label(titleRect, _displayLabel, titleStyle);

        Rect confRect = new Rect(0, 80, Screen.width, 40);
        GUI.Label(confRect, $"Confidence: {_displayConf:P0}", subStyle);

        // Instructions at bottom
        GUIStyle instrStyle = new GUIStyle(GUI.skin.label)
        {
            fontSize = 16,
            alignment = TextAnchor.LowerCenter
        };
        instrStyle.normal.textColor = new Color(1f, 1f, 1f, 0.5f);
        Rect instrRect = new Rect(0, Screen.height - 40, Screen.width, 30);
        GUI.Label(instrRect, "Run: py predict_live.py --unity", instrStyle);
    }
}
