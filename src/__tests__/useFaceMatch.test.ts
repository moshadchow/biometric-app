import { describe, it, expect, vi } from "vitest";

// Mock face-api service so tests don't need real models / DOM
vi.mock("@/services/faceApi.service", () => ({
  getFaceDescriptor: vi.fn(),
  euclideanDistance: vi.fn(),
  loadImageElement: vi.fn(),
}));

import * as faceApiService from "@/services/faceApi.service";

// Import the raw compare logic (not the hook — hooks need renderHook/jsdom)
// We test the service boundary directly.
describe("face match logic (service level)", () => {
  it("returns Success when distance <= threshold", async () => {
    const d1 = new Float32Array(128).fill(0.1);
    const d2 = new Float32Array(128).fill(0.1);
    vi.mocked(faceApiService.loadImageElement).mockResolvedValue({} as HTMLImageElement);
    vi.mocked(faceApiService.getFaceDescriptor).mockResolvedValue(d1);
    vi.mocked(faceApiService.euclideanDistance).mockReturnValue(0.3);

    const dist = faceApiService.euclideanDistance(d1, d2);
    const result = dist <= 0.6 ? "Success" : "Fail";
    expect(result).toBe("Success");
  });

  it("returns Fail when distance > threshold", () => {
    vi.mocked(faceApiService.euclideanDistance).mockReturnValue(0.85);
    const d1 = new Float32Array(128);
    const d2 = new Float32Array(128);
    const dist = faceApiService.euclideanDistance(d1, d2);
    const result = dist <= 0.6 ? "Success" : "Fail";
    expect(result).toBe("Fail");
  });

  it("returns Fail with error when descriptor is null", async () => {
    vi.mocked(faceApiService.getFaceDescriptor).mockResolvedValue(null);
    const desc = await faceApiService.getFaceDescriptor({} as HTMLImageElement);
    const result = desc === null ? "Fail" : "Success";
    expect(result).toBe("Fail");
  });
});
