import * as faceapi from "@vladmandic/face-api";
import { DETECTION_MIN_CONFIDENCE, COMPARISON_MIN_CONFIDENCE } from "@/constants/thresholds";

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

export async function getFaceDescriptor(
  source: HTMLImageElement | HTMLCanvasElement
): Promise<Float32Array | null> {
  const result = await faceapi
    .detectSingleFace(source, new faceapi.SsdMobilenetv1Options({ minConfidence: COMPARISON_MIN_CONFIDENCE }))
    .withFaceLandmarks()
    .withFaceDescriptor();
  return result?.descriptor ?? null;
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
