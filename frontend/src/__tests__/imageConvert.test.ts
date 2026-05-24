import { describe, it, expect } from "vitest";
import { base64ToBytes } from "@/services/imageConvert.service";

describe("base64ToBytes", () => {
  it("converts a simple base64 data URL to Uint8Array", () => {
    // "Hello" in base64 = SGVsbG8=
    const dataUrl = "data:text/plain;base64,SGVsbG8=";
    const bytes = base64ToBytes(dataUrl);
    expect(bytes).toBeInstanceOf(Uint8Array);
    expect(Array.from(bytes)).toEqual([72, 101, 108, 108, 111]); // "Hello"
  });

  it("handles raw base64 without data: prefix", () => {
    const bytes = base64ToBytes("SGVsbG8=");
    expect(Array.from(bytes)).toEqual([72, 101, 108, 108, 111]);
  });

  it("returns correct byte length", () => {
    // 3 bytes → 4 base64 chars
    const bytes = base64ToBytes("AAEC"); // 0x00, 0x01, 0x02
    expect(bytes.length).toBe(3);
  });
});
