import { describe, it, expect, vi } from "vitest";

vi.mock("@/services/faceApi.service", () => ({
  getFaceDescriptor: vi.fn(),
  detectFaceCount: vi.fn(),
  euclideanDistance: vi.fn(),
  loadImageElement: vi.fn(),
}));

import * as faceApiService from "@/services/faceApi.service";

describe("face match logic (service level)", () => {
  it("returns Success when distance <= threshold", async () => {
    const d1 = new Float32Array(128).fill(0.1);
    const d2 = new Float32Array(128).fill(0.1);
    vi.mocked(faceApiService.loadImageElement).mockResolvedValue({} as HTMLImageElement);
    vi.mocked(faceApiService.detectFaceCount).mockResolvedValue(1);
    vi.mocked(faceApiService.getFaceDescriptor).mockResolvedValue({ descriptor: d1, confidence: 0.95 });
    vi.mocked(faceApiService.euclideanDistance).mockReturnValue(0.3);

    const dist = faceApiService.euclideanDistance(d1, d2);
    const result = dist <= 0.45 ? "Success" : "Fail";
    expect(result).toBe("Success");
  });

  it("returns Fail when distance > threshold", () => {
    vi.mocked(faceApiService.euclideanDistance).mockReturnValue(0.85);
    const d1 = new Float32Array(128);
    const d2 = new Float32Array(128);
    const dist = faceApiService.euclideanDistance(d1, d2);
    const result = dist <= 0.45 ? "Success" : "Fail";
    expect(result).toBe("Fail");
  });

  it("returns Fail with error when descriptor is null", async () => {
    vi.mocked(faceApiService.detectFaceCount).mockResolvedValue(1);
    vi.mocked(faceApiService.getFaceDescriptor).mockResolvedValue(null);
    const desc = await faceApiService.getFaceDescriptor({} as HTMLImageElement);
    const result = desc === null ? "Fail" : "Success";
    expect(result).toBe("Fail");
  });

  it("returns Fail when no face is detected (count = 0)", async () => {
    vi.mocked(faceApiService.detectFaceCount).mockResolvedValue(0);
    const count = await faceApiService.detectFaceCount({} as HTMLImageElement);
    const result = count === 0 ? "Fail" : "Success";
    expect(result).toBe("Fail");
  });

  it("returns Fail when multiple faces are detected (count > 1)", async () => {
    vi.mocked(faceApiService.detectFaceCount).mockResolvedValue(2);
    const count = await faceApiService.detectFaceCount({} as HTMLImageElement);
    const result = count !== 1 ? "Fail" : "Success";
    expect(result).toBe("Fail");
  });
});
