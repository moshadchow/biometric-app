import { useCallback } from "react";
import {
  getFaceDescriptor,
  detectFaceCount,
  euclideanDistance,
  loadImageElement,
} from "@/services/faceApi.service";
import { FaceMatchPayload, MatchResult } from "@/types";
import { MATCH_THRESHOLD } from "@/constants/thresholds";

interface UseFaceMatchOptions {
  threshold?: number;
}

export function useFaceMatch({ threshold = MATCH_THRESHOLD }: UseFaceMatchOptions = {}) {
  const compare = useCallback(
    async (capturedSrc: string, referenceSrc: string): Promise<FaceMatchPayload> => {
      try {
        // ── Step 1: Load both images ─────────────────────────────────────────
        const [capturedImg, referenceImg] = await Promise.all([
          loadImageElement(capturedSrc),
          loadImageElement(referenceSrc),
        ]);

        // ── Step 2: Count faces (multi-face / no-face guard) ─────────────────
        // detectFaceCount uses only the SSD detector — cheaper than full descriptor pipeline.
        // Reject here to avoid paying 3-network cost on bad inputs.
        const [capturedCount, referenceCount] = await Promise.all([
          detectFaceCount(capturedImg),
          detectFaceCount(referenceImg),
        ]);

        console.log(`[useFaceMatch] face counts — captured: ${capturedCount}, reference: ${referenceCount}`);

        if (capturedCount === 0) {
          console.log("[useFaceMatch] REJECT — no face detected in captured image");
          return { result: "Fail", distance: -1, error: "No face detected in captured image." };
        }
        if (capturedCount > 1) {
          console.log(`[useFaceMatch] REJECT — ${capturedCount} faces in captured image`);
          return {
            result: "Fail",
            distance: -1,
            error: `Multiple faces detected in captured image (${capturedCount}). Ensure only one face is visible.`,
          };
        }
        if (referenceCount === 0) {
          console.log("[useFaceMatch] REJECT — no face detected in reference image");
          return { result: "Fail", distance: -1, error: "No face detected in reference image." };
        }
        if (referenceCount > 1) {
          console.log(`[useFaceMatch] REJECT — ${referenceCount} faces in reference image`);
          return {
            result: "Fail",
            distance: -1,
            error: `Multiple faces detected in reference image (${referenceCount}). Use a reference photo with exactly one face.`,
          };
        }

        // ── Step 3: Extract descriptors (confidence-gated) ───────────────────
        const [capturedResult, referenceResult] = await Promise.all([
          getFaceDescriptor(capturedImg),
          getFaceDescriptor(referenceImg),
        ]);

        if (!capturedResult) {
          console.log("[useFaceMatch] REJECT — captured descriptor failed confidence gate");
          return {
            result: "Fail",
            distance: -1,
            error: "Captured face detection confidence too low. Ensure good lighting and a clear, unobstructed face.",
          };
        }
        if (!referenceResult) {
          console.log("[useFaceMatch] REJECT — reference descriptor failed confidence gate");
          return {
            result: "Fail",
            distance: -1,
            error: "Reference image face detection confidence too low. Use a well-lit, clear reference photo.",
          };
        }

        console.log(
          `[useFaceMatch] confidence — captured: ${capturedResult.confidence.toFixed(3)}, reference: ${referenceResult.confidence.toFixed(3)}`
        );

        // ── Step 4: Compute distance and apply threshold ─────────────────────
        const distance = euclideanDistance(capturedResult.descriptor, referenceResult.descriptor);
        const result: MatchResult = distance <= threshold ? "Success" : "Fail";

        console.log(
          `[useFaceMatch] distance: ${distance.toFixed(4)} | threshold: ${threshold} | result: ${result}`
        );

        return { result, distance };
      } catch (err) {
        console.log(`[useFaceMatch] ERROR — ${String(err)}`);
        return { result: "Fail", distance: -1, error: String(err) };
      }
    },
    [threshold]
  );

  return { compare };
}
