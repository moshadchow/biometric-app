import React from "react";

interface QualityIndicatorProps {
  label: string;
  value: number;
  max: number;
  warnMin: number;
  warnMax: number;
  suffix?: string;
}

const QualityIndicator: React.FC<QualityIndicatorProps> = ({
  label,
  value,
  max,
  warnMin,
  warnMax,
  suffix = "",
}) => {
  const pct = Math.min(100, (value / max) * 100);
  const ok = value >= warnMin && value <= warnMax;
  const color = ok ? "#00e5a0" : "#ff6b6b";

  return (
    <div style={{ flex: 1, minWidth: 80 }}>
      <div style={{ fontSize: 11, color: "#888", marginBottom: 3 }}>{label}</div>
      <div
        style={{
          background: "#1e1e1e",
          borderRadius: 4,
          height: 5,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: color,
            transition: "width 0.2s, background 0.2s",
          }}
        />
      </div>
      <div style={{ fontSize: 11, color, marginTop: 2 }}>
        {Math.round(value)}
        {suffix}
      </div>
    </div>
  );
};

export default QualityIndicator;
