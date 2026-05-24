import React from "react";

interface FaceOverlayProps {
  canvasRef: React.RefObject<HTMLCanvasElement>;
}

const FaceOverlay: React.FC<FaceOverlayProps> = ({ canvasRef }) => (
  <canvas
    ref={canvasRef}
    style={{
      position: "absolute",
      inset: 0,
      width: "100%",
      height: "100%",
      transform: "scaleX(-1)",
      pointerEvents: "none",
    }}
  />
);

export default FaceOverlay;
