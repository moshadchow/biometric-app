import * as faceapi from "@vladmandic/face-api";
import {
  DETECTION_MIN_CONFIDENCE,
  COMPARISON_MIN_CONFIDENCE,
  DESCRIPTOR_CONFIDENCE_GATE,
} from "@/constants/thresholds";

let modelsLoaded = false;

export async function loadModels(modelPath: string): Promise<void> {
  if (modelsLoaded) return;
  await Promise.all([
    faceapi.nets.ssdMobilenetv1.loadFromUri(modelPath),
    faceapi.nets.faceLandmark68Net.loadFromUri(modelPath),
    faceapi.nets.faceRecognitionNet.loadFromUri(modelPath),
  ]);
  modelsLoaded = true;
}

export async function detectFaceWithLandmarks(
  source: HTMLVideoElement | HTMLCanvasElement | HTMLImageElement
) {
  return faceapi
    .detectSingleFace(source, new faceapi.SsdMobilenetv1Options({ minConfidence: DETECTION_MIN_CONFIDENCE }))
    .withFaceLandmarks();
}

export interface FaceDescriptorResult {
  descriptor: Float32Array;
  confidence: number;
}

/**
 * Extract a 128-d face descriptor from a still image.
 * Returns null if no face is found or detection confidence is below DESCRIPTOR_CONFIDENCE_GATE.
 */
export async function getFaceDescriptor(
  source: HTMLImageElement | HTMLCanvasElement
): Promise<FaceDescriptorResult | null> {
  const result = await faceapi
    .detectSingleFace(source, new faceapi.SsdMobilenetv1Options({ minConfidence: COMPARISON_MIN_CONFIDENCE }))
    .withFaceLandmarks()
    .withFaceDescriptor();

  if (!result) return null;

  const confidence = result.detection.score;
  if (confidence < DESCRIPTOR_CONFIDENCE_GATE) {
    console.log(
      `[faceApi] descriptor rejected — confidence ${confidence.toFixed(3)} < gate ${DESCRIPTOR_CONFIDENCE_GATE}`
    );
    return null;
  }

  return { descriptor: result.descriptor, confidence };
}

/**
 * Count how many faces are detected in a still image.
 * Uses detectAllFaces (not detectSingleFace) — the only API that reveals multiple faces.
 */
export async function detectFaceCount(
  source: HTMLImageElement | HTMLCanvasElement
): Promise<number> {
  const results = await faceapi.detectAllFaces(
    source,
    new faceapi.SsdMobilenetv1Options({ minConfidence: COMPARISON_MIN_CONFIDENCE })
  );
  return results.length;
}

export function euclideanDistance(a: Float32Array, b: Float32Array): number {
  return faceapi.euclideanDistance(a, b);
}

export function loadImageElement(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
    img.src = src;
  });
}
