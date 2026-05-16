export const MATCH_THRESHOLD = parseFloat(
  import.meta.env.VITE_MATCH_THRESHOLD ?? "0.45"
);

export const MODEL_PATH: string =
  import.meta.env.VITE_MODEL_PATH ?? "/models";

// Quality thresholds
export const MIN_BRIGHTNESS = 60;
export const MAX_BRIGHTNESS = 220;
export const MIN_SHARPNESS = 40;
export const MIN_FACE_AREA = 0.05; // 5% of frame

// Detection (live camera overlay loop)
export const DETECTION_MIN_CONFIDENCE = 0.5;

// Comparison (descriptor extraction during face matching)
export const COMPARISON_MIN_CONFIDENCE = 0.6;

// Minimum detection score required to trust a descriptor for comparison.
// Detections below this score are treated as if no face was found.
export const DESCRIPTOR_CONFIDENCE_GATE = 0.6;

// Capture
export const CAPTURE_JPEG_QUALITY = 0.92;
