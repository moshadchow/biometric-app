import { describe, it, expect } from "vitest";
import { laplacianVariance } from "@/utils/laplacianVariance";
import { meanLuminance } from "@/utils/luminance";
import { clampBox } from "@/utils/clampBox";

describe("meanLuminance", () => {
  it("returns 0 for black image", () => {
    const data = new Uint8ClampedArray(4 * 4 * 4); // 4x4 all zeros
    expect(meanLuminance(data, 16)).toBe(0);
  });

  it("returns ~255 for white image", () => {
    const data = new Uint8ClampedArray(4 * 4 * 4).fill(255);
    expect(meanLuminance(data, 16)).toBeCloseTo(255, 0);
  });

  it("returns 0 for zero pixelCount", () => {
    const data = new Uint8ClampedArray(0);
    expect(meanLuminance(data, 0)).toBe(0);
  });
});

describe("laplacianVariance", () => {
  it("returns 0 for uniform image (no edges)", () => {
    const w = 10, h = 10;
    const gray = new Array(w * h).fill(128);
    expect(laplacianVariance(gray, w, h)).toBe(0);
  });

  it("returns > 0 for image with edges", () => {
    const w = 10, h = 10;
    const gray = Array.from({ length: w * h }, (_, i) => (i % 2 === 0 ? 0 : 255));
    expect(laplacianVariance(gray, w, h)).toBeGreaterThan(0);
  });
});

describe("clampBox", () => {
  it("clamps box within canvas bounds", () => {
    const box = clampBox({ x: -10, y: -10, width: 50, height: 50 }, 100, 100);
    expect(box.x).toBe(0);
    expect(box.y).toBe(0);
  });

  it("clips width/height that overflow canvas", () => {
    const box = clampBox({ x: 80, y: 80, width: 50, height: 50 }, 100, 100);
    expect(box.width).toBe(20);
    expect(box.height).toBe(20);
  });
});
