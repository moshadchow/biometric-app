import { CAPTURE_JPEG_QUALITY } from "@/constants/thresholds";

/**
 * Capture current video frame to a base64 JPEG data URL.
 */
export function captureFrameAsBase64(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement
): string {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Cannot get 2D context from canvas");
  ctx.drawImage(video, 0, 0);
  return canvas.toDataURL("image/jpeg", CAPTURE_JPEG_QUALITY);
}

/**
 * Draw video frame to canvas and return it (for quality analysis).
 */
export function videoToCanvas(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement
): HTMLCanvasElement {
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext("2d")?.drawImage(video, 0, 0);
  return canvas;
}

/**
 * Convert a base64 data URL to a raw Uint8Array byte array.
 */
export function base64ToBytes(dataUrl: string): Uint8Array {
  const b64 = dataUrl.includes(",") ? dataUrl.split(",")[1] : dataUrl;
  const binary = atob(b64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Returns a human-readable preview of the byte array.
 */
export function bytesPreview(dataUrl: string): string {
  const bytes = base64ToBytes(dataUrl);
  const preview = Array.from(bytes.slice(0, 20)).join(", ");
  return `[${preview} …]  (${bytes.length.toLocaleString()} total bytes)`;
}
