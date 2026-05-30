import React, { useRef, useState, useCallback, useEffect } from "react";
import { FaceCaptureProps, AppStatus, QualityReport } from "@/types";
import { useModels } from "@/hooks/useModels";
import { useCamera } from "@/hooks/useCamera";
import { useFaceDetection } from "@/hooks/useFaceDetection";
import { useFaceMatch } from "@/hooks/useFaceMatch";
import { captureFrameAsBase64 } from "@/services/imageConvert.service";
import { MODEL_PATH, MATCH_THRESHOLD } from "@/constants/thresholds";
import FaceOverlay from "./FaceOverlay";
import QualityIndicator from "./QualityIndicator";
import MatchResultPanel from "../MatchResult/MatchResult";
import ImagePreviewPair from "../MatchResult/ImagePreviewPair";
import Base64Output from "../Base64Output/Base64Output";

const FaceCapture: React.FC<FaceCaptureProps> = ({
  referenceImageSrc,
  matchThreshold = MATCH_THRESHOLD,
  onMatch,
  onProceed,
  modelPath = MODEL_PATH,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const overlayRef = useRef<HTMLCanvasElement>(null);
  const captureCanvasRef = useRef<HTMLCanvasElement>(null);

  const [status, setStatus] = useState<AppStatus>("loading");
  const [quality, setQuality] = useState<QualityReport | null>(null);
  const [capturedBase64, setCapturedBase64] = useState<string | null>(null);
  const [matchResult, setMatchResult] = useState<{ result: "Success" | "Fail"; distance: number } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const { ready: modelsReady, error: modelError } = useModels(modelPath);
  const { startCamera, stopCamera } = useCamera();
  const { compare } = useFaceMatch({ threshold: matchThreshold });

  // Model load result
  useEffect(() => {
    if (modelError) {
      setErrorMsg(modelError);
      setStatus("error");
    } else if (modelsReady) {
      setStatus("idle");
    }
  }, [modelsReady, modelError]);

  // Detection loop — active only while detecting
  useFaceDetection({
    videoRef,
    overlayRef,
    active: status === "detecting",
    onQualityUpdate: setQuality,
  });

  // Stop camera on unmount
  useEffect(() => () => stopCamera(), [stopCamera]);

  const handleStartCamera = useCallback(async () => {
    if (!videoRef.current) {
      console.error("Video element not available");
      return;
    }
    try {
      await startCamera(videoRef.current);
      setStatus("detecting");
    } catch (err) {
      console.error("Camera error:", err);
      setErrorMsg(err instanceof Error ? err.message : "Camera access denied or device unavailable.");
      setStatus("error");
    }
  }, [startCamera]);

  const handleCapture = useCallback(() => {
    if (!videoRef.current || !captureCanvasRef.current || !quality?.valid) return;
    const base64 = captureFrameAsBase64(videoRef.current, captureCanvasRef.current);
    setCapturedBase64(base64);
    stopCamera();
    setStatus("captured");
  }, [quality, stopCamera]);

  const handleCompare = useCallback(async () => {
    if (!capturedBase64) return;
    setStatus("comparing");
    const payload = await compare(capturedBase64, referenceImageSrc);
    if (payload.error && payload.result === "Fail") {
      setErrorMsg(payload.error);
    }
    if (payload.result !== null) {
      setMatchResult({ result: payload.result, distance: payload.distance });
      onMatch?.(payload.result, payload.distance, {
        capturedBase64,
        referenceImageSrc,
        matchThreshold,
        quality,
      });
    }
    setStatus("done");
  }, [capturedBase64, compare, matchThreshold, onMatch, quality, referenceImageSrc]);

  const handleReset = useCallback(() => {
    stopCamera();
    setCapturedBase64(null);
    setMatchResult(null);
    setQuality(null);
    setErrorMsg("");
    setStatus("idle");
  }, [stopCamera]);

  return (
    <div style={s.root}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.logo}>⬡</div>
        <h1 style={s.title}>Face Verification</h1>
        <StatusBadge status={status} result={matchResult?.result ?? null} />
      </div>

      {/* Video feed */}
      {(status === "idle" || status === "detecting" || status === "captured") && (
        <div style={s.videoWrap}>
          <video
            ref={videoRef}
            style={s.video}
            muted
            playsInline
            autoPlay
          />
          {status === "detecting" && (
            <>
              <FaceOverlay canvasRef={overlayRef} />
              {quality && (
                <div style={s.qualityBar}>
                  <QualityIndicator label="Brightness" value={quality.brightness} max={255} warnMin={60} warnMax={220} />
                  <QualityIndicator label="Sharpness"  value={Math.min(quality.sharpness, 500)} max={500} warnMin={20} warnMax={500} />
                  <QualityIndicator label="Face size"  value={quality.faceArea * 100} max={100} warnMin={5} warnMax={100} suffix="%" />
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Preview pair */}
      {capturedBase64 && (
        <ImagePreviewPair captured={capturedBase64} reference={referenceImageSrc} />
      )}

      {/* Match result */}
      {status === "done" && matchResult && (
        <MatchResultPanel
          result={matchResult.result}
          distance={matchResult.distance}
          threshold={matchThreshold}
          error={errorMsg}
        />
      )}

      {/* Error (non-comparison) */}
      {status === "error" && (
        <div style={s.error}>{errorMsg || "An unexpected error occurred."}</div>
      )}

      {/* Actions */}
      <div style={s.actions}>
        {status === "idle" && (
          <button style={s.btn} onClick={handleStartCamera}>Start camera</button>
        )}
        {status === "detecting" && (
          <button
            style={{ ...s.btn, opacity: quality?.valid ? 1 : 0.4, cursor: quality?.valid ? "pointer" : "not-allowed" }}
            onClick={handleCapture}
            disabled={!quality?.valid}
          >
            {quality?.valid ? "Capture face" : "Waiting for clear face…"}
          </button>
        )}
        {status === "captured" && (
          <button style={s.btn} onClick={handleCompare}>Compare faces</button>
        )}
        {status === "comparing" && (
          <button style={{ ...s.btn, opacity: 0.5 }} disabled>Comparing…</button>
        )}
        {status === "loading" && (
          <button style={{ ...s.btn, opacity: 0.5 }} disabled>Loading models…</button>
        )}
        {status === "done" && matchResult?.result === "Success" && onProceed && (
          <button style={s.btn} onClick={onProceed}>Proceed →</button>
        )}
        {(status === "done" || status === "error" || status === "captured") && (
          <button style={{ ...s.btn, ...s.btnSecondary }} onClick={handleReset}>Reset</button>
        )}
      </div>

      {/* Base64 output panel */}
      {capturedBase64 && <Base64Output dataUrl={capturedBase64} />}

      {/* Hidden canvas for capture */}
      <canvas ref={captureCanvasRef} style={{ display: "none" }} />
    </div>
  );
};

// ── Status badge ─────────────────────────────────────────────────────────────

const statusLabels: Record<AppStatus, string> = {
  loading:   "Loading models…",
  idle:      "Ready",
  detecting: "Detecting face…",
  captured:  "Face captured",
  comparing: "Comparing…",
  done:      "Complete",
  error:     "Error",
};

interface StatusBadgeProps {
  status: AppStatus;
  result: "Success" | "Fail" | null;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status, result }) => {
  const colors: Record<string, { bg: string; color: string }> = {
    loading:   { bg: "#1a1a1a", color: "#888" },
    idle:      { bg: "#1a1a1a", color: "#888" },
    detecting: { bg: "#0d2a3d", color: "#38b6ff" },
    captured:  { bg: "#1a2a1a", color: "#7cdd88" },
    comparing: { bg: "#2a2a0d", color: "#ffe56b" },
    done:      result === "Success" ? { bg: "#0f3d2a", color: "#00e5a0" } : { bg: "#3d0f0f", color: "#ff6b6b" },
    error:     { bg: "#3d0f0f", color: "#ff9999" },
  };
  const c = colors[status] ?? colors.idle;

  return (
    <div style={{ background: c.bg, color: c.color, fontSize: 12, padding: "3px 12px", borderRadius: 20, fontWeight: 500 }}>
      {status === "done" && result ? result : statusLabels[status]}
    </div>
  );
};

// ── Styles ────────────────────────────────────────────────────────────────────

const s: Record<string, React.CSSProperties> = {
  root: {
    fontFamily: "'DM Mono','Fira Code','Cascadia Code',monospace",
    background: "#0a0a0a",
    color: "#e0e0e0",
    maxWidth: 640,
    margin: "0 auto",
    padding: "2rem 1.5rem",
    borderRadius: 16,
    border: "1px solid #222",
    minHeight: 200,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: 20,
    flexWrap: "wrap" as const,
  },
  logo: {
    fontSize: 22,
    color: "#00e5a0",
    lineHeight: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    letterSpacing: "-0.5px",
    color: "#fff",
    margin: 0,
    flex: 1,
  },
  videoWrap: {
    position: "relative",
    width: "100%",
    borderRadius: 12,
    overflow: "hidden",
    background: "#111",
    marginBottom: 12,
  },
  video: {
    width: "100%",
    display: "block",
    transform: "scaleX(-1)",
  },
  qualityBar: {
    display: "flex",
    gap: 16,
    padding: "8px 14px",
    background: "#0d0d0d",
    borderTop: "1px solid #1e1e1e",
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap" as const,
    marginBottom: 16,
  },
  btn: {
    background: "#00e5a0",
    color: "#000",
    border: "none",
    borderRadius: 8,
    padding: "10px 22px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "inherit",
    letterSpacing: "0.2px",
    transition: "opacity 0.15s",
  },
  btnSecondary: {
    background: "transparent",
    color: "#999",
    border: "1px solid #333",
  },
  error: {
    background: "#3d0f0f",
    color: "#ff9999",
    padding: "12px 16px",
    borderRadius: 8,
    fontSize: 13,
    marginBottom: 12,
    border: "1px solid #7a2020",
    lineHeight: 1.6,
  },
};

export default FaceCapture;
