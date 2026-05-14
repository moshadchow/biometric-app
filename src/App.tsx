import React, { useState } from "react";
import FaceCapture from "@/components/FaceCapture";
import { MatchResult } from "@/types";

/**
 * Demo App — swap REFERENCE_IMAGE_URL for a real hosted image URL
 * or a base64 data URL containing a face to compare against.
 *
 * For local testing, add your reference image to public/reference.jpg
 * and set the URL to "/reference.jpg".
 */
const REFERENCE_IMAGE_URL = "/reference.jpg";

const App: React.FC = () => {
  const [lastResult, setLastResult] = useState<{ result: MatchResult; score: number } | null>(null);

  const handleMatch = (result: MatchResult, score: number) => {
    setLastResult({ result, score });
    console.log(`[FaceCapture] result=${result}  distance=${score.toFixed(4)}`);
  };

  return (
    <div style={{ width: "100%", maxWidth: 640 }}>
      <FaceCapture
        referenceImageSrc={REFERENCE_IMAGE_URL}
        matchThreshold={0.6}
        modelPath="/models"
        onMatch={handleMatch}
      />

      {lastResult && (
        <div
          style={{
            marginTop: 12,
            padding: "10px 16px",
            background: "#111",
            border: "1px solid #222",
            borderRadius: 8,
            fontSize: 12,
            color: "#666",
            fontFamily: "monospace",
          }}
        >
          Last result via onMatch callback:{" "}
          <span style={{ color: lastResult.result === "Success" ? "#00e5a0" : "#ff6b6b" }}>
            {lastResult.result}
          </span>
          {lastResult.score >= 0 && ` — distance: ${lastResult.score.toFixed(4)}`}
        </div>
      )}
    </div>
  );
};

export default App;
