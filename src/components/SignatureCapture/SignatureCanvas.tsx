import React, { useEffect, useRef, useState } from "react";
import { SIGNATURE_CANVAS_HEIGHT, SIGNATURE_CANVAS_WIDTH } from "@/constants/signature";
import type { SignatureImageAsset } from "@/types";

interface SignatureCanvasProps {
  label: string;
  helperText: string;
  disabled?: boolean;
  onSave: (asset: Omit<SignatureImageAsset, "source">) => void;
  onClear: () => void;
}

interface Point {
  x: number;
  y: number;
}

const SignatureCanvas: React.FC<SignatureCanvasProps> = ({
  label,
  helperText,
  disabled = false,
  onSave,
  onClear,
}) => {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const isDrawingRef = useRef(false);
  const lastPointRef = useRef<Point | null>(null);
  const strokeCountRef = useRef(0);
  const [hasInk, setHasInk] = useState(false);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, SIGNATURE_CANVAS_WIDTH, SIGNATURE_CANVAS_HEIGHT);
    context.lineCap = "round";
    context.lineJoin = "round";
    context.lineWidth = 2.4;
    context.strokeStyle = "#111111";
  }, []);

  const getPoint = (event: React.PointerEvent<HTMLCanvasElement>): Point => {
    const rect = event.currentTarget.getBoundingClientRect();
    const scaleX = SIGNATURE_CANVAS_WIDTH / rect.width;
    const scaleY = SIGNATURE_CANVAS_HEIGHT / rect.height;
    return {
      x: (event.clientX - rect.left) * scaleX,
      y: (event.clientY - rect.top) * scaleY,
    };
  };

  const drawLine = (context: CanvasRenderingContext2D, from: Point, to: Point) => {
    context.beginPath();
    context.moveTo(from.x, from.y);
    context.lineTo(to.x, to.y);
    context.stroke();
  };

  const handlePointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (disabled) return;

    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    const point = getPoint(event);
    isDrawingRef.current = true;
    lastPointRef.current = point;
    strokeCountRef.current += 1;
    setHasInk(true);
    event.currentTarget.setPointerCapture(event.pointerId);
    drawLine(context, point, point);
  };

  const handlePointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current || disabled) return;

    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    const previousPoint = lastPointRef.current;
    if (!canvas || !context || !previousPoint) return;

    const nextPoint = getPoint(event);
    drawLine(context, previousPoint, nextPoint);
    lastPointRef.current = nextPoint;
  };

  const finishStroke = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    lastPointRef.current = null;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
  };

  const clearCanvas = () => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;

    context.clearRect(0, 0, SIGNATURE_CANVAS_WIDTH, SIGNATURE_CANVAS_HEIGHT);
    context.fillStyle = "#ffffff";
    context.fillRect(0, 0, SIGNATURE_CANVAS_WIDTH, SIGNATURE_CANVAS_HEIGHT);
    strokeCountRef.current = 0;
    setHasInk(false);
    onClear();
  };

  const saveCanvas = () => {
    const canvas = canvasRef.current;
    if (!canvas || !hasInk) return;

    onSave({
      dataUrl: canvas.toDataURL("image/png"),
      mimeType: "image/png",
      width: SIGNATURE_CANVAS_WIDTH,
      height: SIGNATURE_CANVAS_HEIGHT,
    });
  };

  return (
    <div style={s.root}>
      <div style={s.header}>
        <div>
          <div style={s.label}>{label}</div>
          <div style={s.helper}>{helperText}</div>
        </div>
        <div style={s.badge}>{hasInk ? "Ink detected" : "Awaiting input"}</div>
      </div>

      <canvas
        ref={canvasRef}
        width={SIGNATURE_CANVAS_WIDTH}
        height={SIGNATURE_CANVAS_HEIGHT}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={finishStroke}
        onPointerCancel={finishStroke}
        style={{
          ...s.canvas,
          opacity: disabled ? 0.5 : 1,
          cursor: disabled ? "not-allowed" : "crosshair",
        }}
      />

      <div style={s.actions}>
        <button
          type="button"
          style={{
            ...s.button,
            opacity: hasInk && !disabled ? 1 : 0.45,
            cursor: hasInk && !disabled ? "pointer" : "not-allowed",
          }}
          disabled={!hasInk || disabled}
          onClick={saveCanvas}
        >
          Save Preview
        </button>
        <button
          type="button"
          style={{ ...s.button, ...s.secondaryButton }}
          onClick={clearCanvas}
        >
          Clear
        </button>
      </div>
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: 12,
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    alignItems: "center",
    flexWrap: "wrap",
  },
  label: {
    fontSize: 13,
    color: "#f5f5f5",
    fontWeight: 600,
  },
  helper: {
    fontSize: 11,
    color: "#7d7d7d",
    marginTop: 4,
    lineHeight: 1.5,
  },
  badge: {
    fontSize: 11,
    color: "#38b6ff",
    border: "1px solid #214f6d",
    background: "#0d2330",
    borderRadius: 999,
    padding: "4px 10px",
  },
  canvas: {
    width: "100%",
    maxWidth: "100%",
    minHeight: 220,
    borderRadius: 12,
    border: "1px dashed #2d2d2d",
    background: "#ffffff",
    touchAction: "none",
  },
  actions: {
    display: "flex",
    gap: 10,
    flexWrap: "wrap",
  },
  button: {
    background: "#00e5a0",
    color: "#050505",
    border: "none",
    borderRadius: 8,
    padding: "10px 16px",
    fontSize: 12,
    fontWeight: 700,
    fontFamily: "inherit",
  },
  secondaryButton: {
    background: "transparent",
    color: "#b5b5b5",
    border: "1px solid #2d2d2d",
  },
};

export default SignatureCanvas;
