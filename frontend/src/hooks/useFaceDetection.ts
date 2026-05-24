import { useRef, useEffect, useCallback } from "react";
import { detectFaceWithLandmarks } from "@/services/faceApi.service";
import { analyzeQuality } from "@/services/imageQuality.service";
import { videoToCanvas } from "@/services/imageConvert.service";
import { QualityReport } from "@/types";

interface UseFaceDetectionOptions {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  overlayRef: React.RefObject<HTMLCanvasElement | null>;
  active: boolean;
  onQualityUpdate: (q: QualityReport | null) => void;
}

export function useFaceDetection({
  videoRef,
  overlayRef,
  active,
  onQualityUpdate,
}: UseFaceDetectionOptions) {
  const rafRef = useRef<number>(0);
  const tempCanvas = useRef<HTMLCanvasElement>(document.createElement("canvas"));

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
  }, []);

  useEffect(() => {
    if (!active) {
      stop();
      return;
    }

    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay) return;

    const detect = async () => {
      if (video.readyState < 2) {
        rafRef.current = requestAnimationFrame(detect);
        return;
      }

      overlay.width = video.videoWidth;
      overlay.height = video.videoHeight;
      const ctx = overlay.getContext("2d")!;
      ctx.clearRect(0, 0, overlay.width, overlay.height);

      const detection = await detectFaceWithLandmarks(video);

      if (detection) {
        const { box } = detection.detection;
        const pad = 20;

        // Bounding box
        ctx.strokeStyle = "#00e5a0";
        ctx.lineWidth = 3;
        ctx.beginPath();
        const bx = box.x - pad;
        const by = box.y - pad;
        const bw = box.width + pad * 2;
        const bh = box.height + pad * 2;
        ctx.roundRect(bx, by, bw, bh, 8);
        ctx.stroke();

        // Landmarks
        ctx.fillStyle = "rgba(0,229,160,0.7)";
        for (const pt of detection.landmarks.positions) {
          ctx.beginPath();
          ctx.arc(pt.x, pt.y, 2, 0, Math.PI * 2);
          ctx.fill();
        }

        // Quality analysis
        videoToCanvas(video, tempCanvas.current);
        const q = analyzeQuality(tempCanvas.current, box);
        onQualityUpdate(q);

        // Quality label above box
        ctx.font = "bold 13px monospace";
        ctx.fillStyle = q.valid ? "#00e5a0" : "#ff6b6b";
        ctx.fillText(q.valid ? "✓ Good quality" : `⚠ ${q.message}`, bx, by - 8);
      } else {
        onQualityUpdate(null);

        // Guidance overlay
        ctx.strokeStyle = "rgba(255,255,255,0.2)";
        ctx.lineWidth = 2;
        ctx.setLineDash([8, 6]);
        const cx = overlay.width / 2;
        const cy = overlay.height / 2;
        ctx.beginPath();
        ctx.ellipse(cx, cy, overlay.width * 0.18, overlay.height * 0.28, 0, 0, Math.PI * 2);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.font = "14px monospace";
        ctx.fillStyle = "rgba(255,255,255,0.5)";
        ctx.textAlign = "center";
        ctx.fillText("Position face in frame", cx, cy + overlay.height * 0.32);
        ctx.textAlign = "left";
      }

      rafRef.current = requestAnimationFrame(detect);
    };

    rafRef.current = requestAnimationFrame(detect);
    return () => cancelAnimationFrame(rafRef.current);
  }, [active, videoRef, overlayRef, onQualityUpdate, stop]);

  return { stop };
}
