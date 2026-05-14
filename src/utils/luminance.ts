/**
 * Compute mean luminance (0–255) from raw RGBA ImageData bytes.
 */
export function meanLuminance(data: Uint8ClampedArray, pixelCount: number): number {
  let sum = 0;
  for (let i = 0; i < pixelCount; i++) {
    const r = data[i * 4];
    const g = data[i * 4 + 1];
    const b = data[i * 4 + 2];
    sum += 0.299 * r + 0.587 * g + 0.114 * b;
  }
  return pixelCount > 0 ? sum / pixelCount : 0;
}
