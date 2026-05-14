export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Clamp a face bounding box to stay within canvas dimensions.
 */
export function clampBox(box: BoundingBox, canvasWidth: number, canvasHeight: number): BoundingBox {
  const x = Math.max(0, Math.round(box.x));
  const y = Math.max(0, Math.round(box.y));
  const width = Math.min(canvasWidth - x, Math.round(box.width));
  const height = Math.min(canvasHeight - y, Math.round(box.height));
  return { x, y, width, height };
}
