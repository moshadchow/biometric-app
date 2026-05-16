import React, { useCallback } from "react";
import type { OCRExtractorResult } from "@/types";
import ExtractedTextPanel from "./ExtractedTextPanel";

interface OCRResultViewProps {
  result: OCRExtractorResult;
  onReset: () => void;
}

const OCRResultView: React.FC<OCRResultViewProps> = ({ result, onReset }) => {
  const handleDownload = useCallback(() => {
    const blob = new Blob([result.mergedText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const ts = result.completedAt.replace(/[:.]/g, "-").slice(0, 19);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ocr-result-${ts}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }, [result]);

  return (
    <div style={s.root}>
      <div style={s.successHeader}>
        <span style={s.checkmark}>✓</span>
        <span style={s.successText}>Extraction complete</span>
        <span style={s.timestamp}>
          {new Date(result.completedAt).toLocaleTimeString()}
        </span>
      </div>

      <ExtractedTextPanel sideResult={result.front} label="Front Page" />
      {result.back && (
        <ExtractedTextPanel sideResult={result.back} label="Back Page" />
      )}

      <details style={s.mergedDetails}>
        <summary style={s.mergedSummary}>Merged text (both sides)</summary>
        <pre style={s.mergedText}>{result.mergedText}</pre>
      </details>

      <div style={s.actions}>
        <button style={s.downloadBtn} onClick={handleDownload}>
          ↓ Download .txt
        </button>
        <button style={s.resetBtn} onClick={onReset}>
          Reset
        </button>
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    marginTop: 4,
  },
  successHeader: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 14px",
    background: "#0a2d1e",
    border: "1px solid #1a6a40",
    borderRadius: 10,
    marginBottom: 14,
  },
  checkmark: {
    color: "#00e5a0",
    fontSize: 16,
    fontWeight: 700,
  },
  successText: {
    color: "#00e5a0",
    fontSize: 13,
    fontWeight: 600,
    flex: 1,
  },
  timestamp: {
    fontSize: 11,
    color: "#555",
  },
  mergedDetails: {
    border: "1px solid #1e1e1e",
    borderRadius: 10,
    overflow: "hidden",
    marginBottom: 14,
  },
  mergedSummary: {
    fontSize: 12,
    color: "#666",
    padding: "10px 14px",
    cursor: "pointer",
    background: "#111",
    listStyle: "none",
    userSelect: "none",
  },
  mergedText: {
    margin: 0,
    padding: "12px 14px",
    background: "#0d0d0d",
    color: "#e0e0e0",
    fontSize: 12,
    fontFamily: "'DM Mono','Fira Code','Cascadia Code',monospace",
    whiteSpace: "pre-wrap",
    wordBreak: "break-word",
    maxHeight: 300,
    overflowY: "auto",
    lineHeight: 1.6,
    unicodeBidi: "plaintext",
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  downloadBtn: {
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
  },
  resetBtn: {
    background: "transparent",
    color: "#999",
    border: "1px solid #333",
    borderRadius: 8,
    padding: "10px 22px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
    fontFamily: "inherit",
  },
};

export default OCRResultView;
