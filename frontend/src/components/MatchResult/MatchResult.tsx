import React from "react";

interface MatchResultPanelProps {
  result: "Success" | "Fail";
  distance: number;
  threshold: number;
  error?: string;
}

const MatchResultPanel: React.FC<MatchResultPanelProps> = ({
  result,
  distance,
  threshold,
  error,
}) => {
  const isSuccess = result === "Success";

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 16,
        padding: "16px 20px",
        borderRadius: 10,
        marginBottom: 16,
        background: isSuccess ? "#0a2d1e" : "#2d0a0a",
        border: `1px solid ${isSuccess ? "#1a5c3a" : "#5c1a1a"}`,
      }}
    >
      <div style={{ fontSize: 36, lineHeight: 1 }}>{isSuccess ? "✅" : "❌"}</div>
      <div>
        <div
          style={{
            fontSize: 22,
            fontWeight: 700,
            color: isSuccess ? "#00e5a0" : "#ff6b6b",
            letterSpacing: "-0.5px",
          }}
        >
          {result}
        </div>
        {distance >= 0 && (
          <div style={{ fontSize: 12, color: "#666", marginTop: 3 }}>
            Distance: {distance.toFixed(4)} — threshold: {threshold}
          </div>
        )}
        {error && (
          <div style={{ fontSize: 12, color: "#ff9999", marginTop: 4 }}>{error}</div>
        )}
      </div>
    </div>
  );
};

export default MatchResultPanel;
