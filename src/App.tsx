import React, { useState } from "react";
import Stepper from "@/components/Stepper";
import type { StepConfig } from "@/components/Stepper";
import FaceCapture from "@/components/FaceCapture";
import NIDExtractor from "@/components/NIDExtractor";
import SignatureCapture from "@/components/SignatureCapture";
import type { NIDExtractorResult, StoredSignatureRecord } from "@/types";

const REFERENCE_IMAGE_URL = "/reference.jpg";

const App: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [nidResult, setNidResult] = useState<NIDExtractorResult | null>(null);

  const steps: StepConfig[] = [
    {
      id: "face-verification",
      label: "Face Verification",
      component: (
        <FaceCapture
          referenceImageSrc={REFERENCE_IMAGE_URL}
          modelPath="/models"
          onMatch={(result, score) => {
            console.log(`[App] onMatch - result: ${result}, score: ${score.toFixed(4)}`);
          }}
          onProceed={() => setActiveStep(1)}
        />
      ),
    },
    {
      id: "ocr-extraction",
      label: "OCR Extraction",
      component: (
        <NIDExtractor
          onComplete={(result) => {
            setNidResult(result);
            setActiveStep(2);
          }}
        />
      ),
    },
    {
      id: "signature-capture",
      label: "Signature Capture",
      component: (
        <SignatureCapture
          nidResult={nidResult}
          onComplete={(record: StoredSignatureRecord) => {
            console.log(`[App] signature stored - ${record.id}`);
          }}
        />
      ),
    },
  ];

  return (
    <div style={s.root}>
      <Stepper
        steps={steps}
        activeIndex={activeStep}
        onStepChange={setActiveStep}
      />
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  root: {
    width: "100%",
    maxWidth: 1180,
    margin: "0 auto",
    padding: "2rem 1rem",
  },
};

export default App;
