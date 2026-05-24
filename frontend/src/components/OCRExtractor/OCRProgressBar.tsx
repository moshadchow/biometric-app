import React from "react";
import type { OCRProgressEvent, OCRStatus } from "@/types";

interface OCRProgressBarProps {
  progress: OCRProgressEvent | null;
  status: OCRStatus;
}

const OCRProgressBar: React.FC<OCRProgressBarProps> = ({ progress, status }) => {
  if (status !== "processing") return null;

  const pct = progress?.progress ?? 0;
  const isLoading = progress?.statusText?.includes("loading") ?? false;
  const barColor = isLoading ? "#ffe56b" : "#00e5a0";
  const sideLabel = progress?.side === "back" ? "Back page" : "Front page";

  return (
    <div style={s.root}>
      <div style={s.header}>
        <span style={s.sideLabel}>{sideLabel}</span>
        <span style={{ ...s.statusText, color: isLoading ? "#ffe56b" : "#888" }}>
          {progress?.statusText ?? "initializing…"}
        </span>
        <span style={s.pct}>{pct}%</span>
      </div>
      <div style={s.track}>
        <div
          style={{
            ...s.fill,
            width: `${pct}%`,
            background: barColor,
          }}
        />
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    marginBottom: 12,
  },
  header: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    marginBottom: 6,
  },
  sideLabel: {
    fontSize: 12,
    color: "#e0e0e0",
    fontWeight: 600,
  },
  statusText: {
    fontSize: 11,
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  pct: {
    fontSize: 11,
    color: "#666",
    minWidth: 32,
    textAlign: "right",
  },
  track: {
    background: "#1e1e1e",
    borderRadius: 4,
    height: 8,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    borderRadius: 4,
    transition: "width 0.3s ease, background 0.3s",
  },
};

export default OCRProgressBar;
