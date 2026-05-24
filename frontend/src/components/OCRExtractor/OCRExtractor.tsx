import React from "react";
import type { OCRExtractorProps, OCRStatus } from "@/types";
import { useOCR } from "@/hooks/useOCR";
import FileUploadZone from "./FileUploadZone";
import OCRProgressBar from "./OCRProgressBar";
import OCRResultView from "./OCRResultView";

const OCRExtractor: React.FC<OCRExtractorProps> = ({ onComplete }) => {
  const {
    status,
    frontFile,
    backFile,
    progress,
    result,
    errorMsg,
    handleFileSelect,
    handleClearFile,
    handleProcess,
    handleReset,
  } = useOCR();

  const handleProcessClick = async () => {
    await handleProcess();
    if (result) onComplete?.(result);
  };

  const handleResetClick = () => {
    handleReset();
  };

  return (
    <div style={s.root}>
      {/* Header */}
      <div style={s.header}>
        <div style={s.logo}>◈</div>
        <h1 style={s.title}>OCR Extraction</h1>
        <OCRStatusBadge status={status} />
      </div>

      {/* Upload zones */}
      {status !== "done" && (
        <div style={s.uploadRow}>
          <FileUploadZone
            side="front"
            uploadedFile={frontFile}
            onFileSelect={handleFileSelect}
            onClear={handleClearFile}
            disabled={status === "processing"}
            label="Front Page"
          />
          <FileUploadZone
            side="back"
            uploadedFile={backFile}
            onFileSelect={handleFileSelect}
            onClear={handleClearFile}
            disabled={status === "processing"}
            label="Back Page (optional)"
          />
        </div>
      )}

      {/* Progress */}
      <OCRProgressBar progress={progress} status={status} />

      {/* Error */}
      {(status === "error" || (errorMsg && status !== "processing")) && (
        <div style={s.error}>{errorMsg || "An unexpected error occurred."}</div>
      )}

      {/* Results */}
      {status === "done" && result && (
        <OCRResultView result={result} onReset={handleResetClick} />
      )}

      {/* Actions */}
      {status !== "done" && (
        <div style={s.actions}>
          {(status === "idle" || status === "error") && (
            <button
              style={{
                ...s.btn,
                opacity: frontFile ? 1 : 0.4,
                cursor: frontFile ? "pointer" : "not-allowed",
              }}
              onClick={handleProcessClick}
              disabled={!frontFile}
            >
              {frontFile ? "Extract text" : "Upload front page first"}
            </button>
          )}
          {status === "processing" && (
            <button style={{ ...s.btn, opacity: 0.5 }} disabled>
              Processing…
            </button>
          )}
          {(status === "error") && (
            <button style={{ ...s.btn, ...s.btnSecondary }} onClick={handleResetClick}>
              Reset
            </button>
          )}
        </div>
      )}
    </div>
  );
};

// ── Inline status badge ───────────────────────────────────────────────────────

const ocrStatusLabels: Record<OCRStatus, string> = {
  idle: "Ready",
  uploading: "Loading file…",
  processing: "Processing…",
  done: "Complete",
  error: "Error",
};

const OCRStatusBadge: React.FC<{ status: OCRStatus }> = ({ status }) => {
  const colorMap: Record<OCRStatus, { bg: string; color: string }> = {
    idle:       { bg: "#1a1a1a", color: "#888" },
    uploading:  { bg: "#0d2a3d", color: "#38b6ff" },
    processing: { bg: "#2a2a0d", color: "#ffe56b" },
    done:       { bg: "#0f3d2a", color: "#00e5a0" },
    error:      { bg: "#3d0f0f", color: "#ff9999" },
  };
  const c = colorMap[status] ?? colorMap.idle;
  return (
    <div style={{ background: c.bg, color: c.color, fontSize: 12, padding: "3px 12px", borderRadius: 20, fontWeight: 500 }}>
      {ocrStatusLabels[status]}
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
    flexWrap: "wrap",
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
  uploadRow: {
    display: "flex",
    gap: 12,
    marginBottom: 16,
    flexWrap: "wrap",
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    marginTop: 4,
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

export default OCRExtractor;
