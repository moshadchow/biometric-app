export const MATCH_THRESHOLD = parseFloat(
  import.meta.env.VITE_MATCH_THRESHOLD ?? "0.6"
);

export const MODEL_PATH: string =
  import.meta.env.VITE_MODEL_PATH ?? "/models";

// Quality thresholds
export const MIN_BRIGHTNESS = 60;
export const MAX_BRIGHTNESS = 220;
export const MIN_SHARPNESS = 20;
export const MIN_FACE_AREA = 0.05; // 5% of frame

// Detection
export const DETECTION_MIN_CONFIDENCE = 0.5;
export const COMPARISON_MIN_CONFIDENCE = 0.4;

// Capture
export const CAPTURE_JPEG_QUALITY = 0.92;
