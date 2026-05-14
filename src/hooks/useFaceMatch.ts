import { useCallback } from "react";
import {
  getFaceDescriptor,
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
        const [capturedImg, referenceImg] = await Promise.all([
          loadImageElement(capturedSrc),
          loadImageElement(referenceSrc),
        ]);

        const [capturedDesc, referenceDesc] = await Promise.all([
          getFaceDescriptor(capturedImg),
          getFaceDescriptor(referenceImg),
        ]);

        if (!capturedDesc) {
          return { result: "Fail", distance: -1, error: "No face detected in captured image." };
        }
        if (!referenceDesc) {
          return { result: "Fail", distance: -1, error: "No face detected in reference image." };
        }

        const distance = euclideanDistance(capturedDesc, referenceDesc);
        const result: MatchResult = distance <= threshold ? "Success" : "Fail";
        return { result, distance };
      } catch (err) {
        return { result: "Fail", distance: -1, error: String(err) };
      }
    },
    [threshold]
  );

  return { compare };
}
