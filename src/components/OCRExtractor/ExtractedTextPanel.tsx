import React, { useState, useCallback } from "react";
import type { OCRSideResult } from "@/types";
import { OCR_MIN_CONFIDENCE_WARN } from "@/constants/ocr";

interface ExtractedTextPanelProps {
  sideResult: OCRSideResult;
  label: string;
}

const ExtractedTextPanel: React.FC<ExtractedTextPanelProps> = ({ sideResult, label }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(sideResult.combinedText).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }, [sideResult.combinedText]);

  const isLowConfidence = sideResult.averageConfidence < OCR_MIN_CONFIDENCE_WARN;
  const isEmpty = sideResult.combinedText.trim() === "";

  return (
    <div style={s.root}>
      <div style={s.header}>
        <span style={s.label}>{label}</span>
        <span
          style={{
            ...s.confidenceBadge,
            background: isLowConfidence ? "#2d0a0a" : "#0a2d1e",
            color: isLowConfidence ? "#ff6b6b" : "#00e5a0",
            border: `1px solid ${isLowConfidence ? "#7a2020" : "#1a6a40"}`,
          }}
        >
          {sideResult.averageConfidence}% confidence
        </span>
        <span style={s.timing}>{sideResult.processingTimeMs} ms</span>
        <button style={s.copyBtn} onClick={handleCopy} disabled={isEmpty}>
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>

      {isLowConfidence && (
        <div style={s.warning}>
          Low confidence — image quality may be poor. Try a higher-resolution scan.
        </div>
      )}

      {isEmpty ? (
        <div style={s.empty}>No text extracted</div>
      ) : sideResult.pages.length > 1 ? (
        sideResult.pages.map((page) => (
          <details key={page.pageNumber} style={s.details}>
            <summary style={s.summary}>
              Page {page.pageNumber}
              <span style={s.pageConfidence}>{page.confidence}% conf.</span>
            </summary>
            <pre style={s.textBlock}>{page.text}</pre>
          </details>
        ))
      ) : (
        <pre style={s.textBlock}>{sideResult.combinedText}</pre>
      )}
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    marginBottom: 16,
    border: "1px solid #1e1e1e",
    borderRadius: 10,
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    padding: "10px 14px",
    background: "#111",
    borderBottom: "1px solid #1e1e1e",
    flexWrap: "wrap",
  },
  label: {
    fontSize: 13,
    fontWeight: 600,
    color: "#e0e0e0",
    flex: 1,
  },
  confidenceBadge: {
    fontSize: 11,
    padding: "2px 8px",
    borderRadius: 20,
    fontWeight: 500,
  },
  timing: {
    fontSize: 11,
    color: "#555",
  },
  copyBtn: {
    background: "transparent",
    border: "1px solid #333",
    borderRadius: 6,
    color: "#888",
    fontSize: 11,
    padding: "3px 10px",
    cursor: "pointer",
    fontFamily: "inherit",
  },
  warning: {
    background: "#2d0a0a",
    color: "#ff9999",
    fontSize: 12,
    padding: "8px 14px",
    borderBottom: "1px solid #7a2020",
  },
  empty: {
    color: "#555",
    fontSize: 12,
    padding: "16px 14px",
    fontStyle: "italic",
  },
  details: {
    borderBottom: "1px solid #1a1a1a",
  },
  summary: {
    fontSize: 12,
    color: "#888",
    padding: "8px 14px",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    gap: 8,
    listStyle: "none",
    userSelect: "none",
  },
  pageConfidence: {
    fontSize: 11,
    color: "#555",
    marginLeft: "auto",
  },
  textBlock: {
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
};

export default ExtractedTextPanel;
