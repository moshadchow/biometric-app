import React from "react";

interface ImagePreviewPairProps {
  captured: string;
  reference: string;
}

const ImagePreviewPair: React.FC<ImagePreviewPairProps> = ({ captured, reference }) => (
  <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
    {[
      { src: captured, label: "Captured" },
      { src: reference, label: "Reference" },
    ].map(({ src, label }) => (
      <div
        key={label}
        style={{
          flex: 1,
          background: "#111",
          border: "1px solid #222",
          borderRadius: 10,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            fontSize: 10,
            color: "#555",
            padding: "5px 10px",
            textTransform: "uppercase" as const,
            letterSpacing: 1,
          }}
        >
          {label}
        </div>
        <img
          src={src}
          alt={label}
          style={{ width: "100%", display: "block", maxHeight: 200, objectFit: "cover" }}
        />
      </div>
    ))}
  </div>
);

export default ImagePreviewPair;
