import { useRef, useCallback } from "react";

interface UseCameraResult {
  startCamera: (videoEl: HTMLVideoElement) => Promise<void>;
  stopCamera: () => void;
  streamRef: React.MutableRefObject<MediaStream | null>;
}

export function useCamera(): UseCameraResult {
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async (videoEl: HTMLVideoElement) => {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        facingMode: "user",
      },
    });
    streamRef.current = stream;
    videoEl.srcObject = stream;
    await videoEl.play();
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  return { startCamera, stopCamera, streamRef };
}
