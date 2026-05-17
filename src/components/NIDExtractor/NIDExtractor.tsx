import React from "react";
import type { NIDExtractorResult, OCRStatus } from "@/types";
import { useNIDOCR } from "@/hooks/useNIDOCR";
import FileUploadZone from "@/components/OCRExtractor/FileUploadZone";
import OCRProgressBar from "@/components/OCRExtractor/OCRProgressBar";
import NIDResultView from "./NIDResultView";
import {
  NID_ACCEPTED_EXTENSIONS,
  NID_ACCEPTED_MIME_TYPES,
} from "@/services/nidFileValidation.service";

interface NIDExtractorProps {
  onComplete?: (result: NIDExtractorResult) => void;
}

const NIDExtractor: React.FC<NIDExtractorProps> = ({ onComplete }) => {
  const {
    status,
    workerReady,
    frontFile,
    backFile,
    progress,
    result,
    errorMsg,
    qualityWarning,
    handleFileSelect,
    handleClearFile,
    handleProcess,
    handleReset,
  } = useNIDOCR();

  const handleProcessClick = async () => {
    await handleProcess();
  };

  return (
    <div style={s.root}>
      <div style={s.header}>
        <div style={s.logo}>NID</div>
        <div style={s.titleGroup}>
          <h1 style={s.title}>NID Card Extraction</h1>
          <span style={s.subtitle}>Bangladesh National ID Card</span>
        </div>
        <NIDStatusBadge status={status} />
      </div>

      {status !== "done" && (
        <div style={s.uploadRow}>
          <FileUploadZone
            side="front"
            uploadedFile={frontFile}
            onFileSelect={handleFileSelect}
            onClear={handleClearFile}
            disabled={status === "processing"}
            label="Front Side *"
            acceptedExtensions={NID_ACCEPTED_EXTENSIONS}
            acceptedMimeTypes={NID_ACCEPTED_MIME_TYPES}
            acceptedLabel="JPG, PNG - max 20 MB"
          />
          <FileUploadZone
            side="back"
            uploadedFile={backFile}
            onFileSelect={handleFileSelect}
            onClear={handleClearFile}
            disabled={status === "processing"}
            label="Back Side (optional)"
            acceptedExtensions={NID_ACCEPTED_EXTENSIONS}
            acceptedMimeTypes={NID_ACCEPTED_MIME_TYPES}
            acceptedLabel="JPG, PNG - max 20 MB"
          />
        </div>
      )}

      {qualityWarning && status !== "done" && (
        <div style={s.qualityWarn}>{qualityWarning}</div>
      )}

      <OCRProgressBar progress={progress} status={status} />

      {(status === "error" || (errorMsg && status !== "processing")) && (
        <div style={s.error}>{errorMsg || "An unexpected error occurred."}</div>
      )}

      {status === "done" && result && (
        <>
          <NIDResultView result={result} onReset={handleReset} />
          {onComplete && (
            <div style={s.actions}>
              <button style={s.btn} onClick={() => onComplete(result)}>
                Proceed to Signature
              </button>
            </div>
          )}
        </>
      )}

      {status !== "done" && (
        <div style={s.actions}>
          {!workerReady && status !== "processing" && (
            <button style={{ ...s.btn, opacity: 0.5 }} disabled>
              Loading OCR engine...
            </button>
          )}
          {workerReady && (status === "idle" || status === "error") && (
            <button
              style={{
                ...s.btn,
                opacity: frontFile ? 1 : 0.4,
                cursor: frontFile ? "pointer" : "not-allowed",
              }}
              onClick={handleProcessClick}
              disabled={!frontFile}
            >
              {frontFile ? "Extract NID Data" : "Upload front side first"}
            </button>
          )}
          {status === "processing" && (
            <button style={{ ...s.btn, opacity: 0.5 }} disabled>
              Processing...
            </button>
          )}
          {status === "error" && (
            <button style={{ ...s.btn, ...s.btnSecondary }} onClick={handleReset}>
              Reset
            </button>
          )}
        </div>
      )}
    </div>
  );
};

const nidStatusLabels: Record<OCRStatus, string> = {
  idle: "Ready",
  uploading: "Loading...",
  processing: "Extracting...",
  done: "Complete",
  error: "Error",
};

const NIDStatusBadge: React.FC<{ status: OCRStatus }> = ({ status }) => {
  const colorMap: Record<OCRStatus, { bg: string; color: string }> = {
    idle: { bg: "#1a1a1a", color: "#888" },
    uploading: { bg: "#0d2a3d", color: "#38b6ff" },
    processing: { bg: "#2a2a0d", color: "#ffe56b" },
    done: { bg: "#0f3d2a", color: "#00e5a0" },
    error: { bg: "#3d0f0f", color: "#ff9999" },
  };
  const c = colorMap[status] ?? colorMap.idle;
  return (
    <div
      style={{
        background: c.bg,
        color: c.color,
        fontSize: 12,
        padding: "3px 12px",
        borderRadius: 20,
        fontWeight: 500,
      }}
    >
      {nidStatusLabels[status]}
    </div>
  );
};

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
    fontSize: 14,
    color: "#00e5a0",
    lineHeight: 1,
    fontWeight: 700,
    letterSpacing: "1px",
  },
  titleGroup: {
    display: "flex",
    flexDirection: "column",
    gap: 2,
    flex: 1,
  },
  title: {
    fontSize: 20,
    fontWeight: 600,
    letterSpacing: "-0.5px",
    color: "#fff",
    margin: 0,
  },
  subtitle: {
    fontSize: 11,
    color: "#555",
    letterSpacing: "0.3px",
  },
  uploadRow: {
    display: "flex",
    gap: 12,
    marginBottom: 12,
    flexWrap: "wrap",
  },
  qualityWarn: {
    background: "#2a2a0d",
    color: "#ffe56b",
    border: "1px solid #555520",
    borderRadius: 8,
    fontSize: 12,
    padding: "9px 14px",
    marginBottom: 12,
    lineHeight: 1.5,
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
    marginTop: 12,
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

export default NIDExtractor;
