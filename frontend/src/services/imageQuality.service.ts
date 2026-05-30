import { QualityReport } from "@/types";
import { meanLuminance } from "@/utils/luminance";
import { laplacianVariance } from "@/utils/laplacianVariance";
import { clampBox } from "@/utils/clampBox";
import {
  MIN_BRIGHTNESS,
  MAX_BRIGHTNESS,
  MIN_SHARPNESS,
  MIN_FACE_AREA,
} from "@/constants/thresholds";

export function analyzeQuality(
  canvas: HTMLCanvasElement,
  faceBox: { x: number; y: number; width: number; height: number }
): QualityReport {
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) {
    return { brightness: 0, sharpness: 0, faceArea: 0, valid: false, message: "Canvas context unavailable" };
  }

  const { x, y, width: w, height: h } = clampBox(faceBox, canvas.width, canvas.height);
  const data = ctx.getImageData(x, y, w, h).data;
  const total = w * h;

  // Build grayscale array + measure brightness
  const gray: number[] = new Array(total);
  let lumSum = 0;
  for (let i = 0; i < total; i++) {
    const lum = 0.299 * data[i * 4] + 0.587 * data[i * 4 + 1] + 0.114 * data[i * 4 + 2];
    gray[i] = lum;
    lumSum += lum;
  }

  const brightness = total > 0 ? lumSum / total : 0;
  const sharpness = laplacianVariance(gray, w, h);
  const faceArea = (faceBox.width * faceBox.height) / (canvas.width * canvas.height);

  const issues: string[] = [];
  if (brightness < MIN_BRIGHTNESS) issues.push("too dark");
  if (brightness > MAX_BRIGHTNESS) issues.push("too bright / overexposed");
  if (sharpness < MIN_SHARPNESS) issues.push("image blurry");
  if (faceArea < MIN_FACE_AREA) issues.push("face too small — move closer");

  return {
    brightness,
    sharpness,
    faceArea,
    valid: issues.length === 0,
    message: issues.length ? issues.join(", ") : "Good",
  };
}
