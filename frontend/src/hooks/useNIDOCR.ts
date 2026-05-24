import { useState, useCallback, useEffect } from "react";
import type {
  OCRStatus,
  DocumentSide,
  UploadedFile,
  OCRProgressEvent,
} from "@/types";
import type { NIDExtractorResult } from "@/types";
import { validateNIDFile } from "@/services/nidFileValidation.service";
import { detectNIDCard, extractNIDFields, analyzeCardImageQuality } from "@/services/nidValidation.service";
import { createPreviewUrl } from "@/services/fileValidation.service";
import { initOCRWorker, terminateOCRWorker, recognizeFile } from "@/services/tesseract.service";
import { OCR_MERGE_SEPARATOR } from "@/constants/ocr";

export interface UseNIDOCRReturn {
  status: OCRStatus;
  workerReady: boolean;
  frontFile: UploadedFile | null;
  backFile: UploadedFile | null;
  progress: OCRProgressEvent | null;
  result: NIDExtractorResult | null;
  errorMsg: string;
  qualityWarning: string;
  handleFileSelect: (file: File, side: DocumentSide) => Promise<void>;
  handleClearFile: (side: DocumentSide) => void;
  handleProcess: () => Promise<void>;
  handleReset: () => void;
}

export function useNIDOCR(): UseNIDOCRReturn {
  const [status, setStatus] = useState<OCRStatus>("idle");
  const [workerReady, setWorkerReady] = useState(false);
  const [frontFile, setFrontFile] = useState<UploadedFile | null>(null);
  const [backFile, setBackFile] = useState<UploadedFile | null>(null);
  const [progress, setProgress] = useState<OCRProgressEvent | null>(null);
  const [result, setResult] = useState<NIDExtractorResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [qualityWarning, setQualityWarning] = useState<string>("");

  useEffect(() => {
    let cancelled = false;
    initOCRWorker().then(() => {
      if (!cancelled) setWorkerReady(true);
    });
    return () => {
      cancelled = true;
      terminateOCRWorker();
    };
  }, []);

  const handleFileSelect = useCallback(
    async (file: File, side: DocumentSide) => {
      const validationError = validateNIDFile(file);
      if (validationError) {
        setErrorMsg(validationError.message);
        setStatus("error");
        return;
      }

      setStatus("uploading");
      setErrorMsg("");
      if (side === "front") setQualityWarning("");

      // Revoke previous URL for this side
      if (side === "front" && frontFile?.previewUrl) URL.revokeObjectURL(frontFile.previewUrl);
      if (side === "back" && backFile?.previewUrl) URL.revokeObjectURL(backFile.previewUrl);

      const quality = await analyzeCardImageQuality(file);
      if (!quality.valid) {
        setErrorMsg(quality.reason ?? "Image quality is too low for NID card scanning.");
        setStatus("error");
        return;
      }
      if (quality.warning) {
        setQualityWarning(quality.warning);
      }

      const previewUrl = createPreviewUrl(file);
      const mimeType = file.type as "image/jpeg" | "image/png";
      const uploaded: UploadedFile = { side, file, previewUrl, mimeType };

      if (side === "front") setFrontFile(uploaded);
      else setBackFile(uploaded);

      setStatus("idle");
    },
    [frontFile, backFile]
  );

  const handleClearFile = useCallback((side: DocumentSide) => {
    if (side === "front") {
      setFrontFile((prev) => {
        if (prev?.previewUrl) URL.revokeObjectURL(prev.previewUrl);
        return null;
      });
      setQualityWarning("");
    } else {
      setBackFile((prev) => {
        if (prev?.previewUrl) URL.revokeObjectURL(prev.previewUrl);
        return null;
      });
    }
    setResult(null);
    setErrorMsg("");
    setStatus("idle");
  }, []);

  const handleProcess = useCallback(async () => {
    if (!frontFile) {
      setErrorMsg("Front side is required before processing.");
      setStatus("error");
      return;
    }

    setStatus("processing");
    setErrorMsg("");
    setProgress(null);

    try {
      const onProgress = (evt: OCRProgressEvent) => setProgress(evt);

      const frontResult = await recognizeFile(frontFile.file, onProgress, "front");
      const backResult = backFile
        ? await recognizeFile(backFile.file, onProgress, "back")
        : undefined;

      const frontDetection = detectNIDCard(frontResult.combinedText, "front");
      if (!frontDetection.isNID) {
        setErrorMsg(
          `This does not appear to be a Bangladesh National ID card (score: ${frontDetection.score}/100). ` +
          `Please upload a clear photo of the front of your NID card.`
        );
        setStatus("error");
        return;
      }

      const backDetection = backResult
        ? detectNIDCard(backResult.combinedText, "back")
        : undefined;

      const fields = extractNIDFields(
        frontResult.combinedText,
        backResult?.combinedText
      );

      const mergedText = backResult
        ? frontResult.combinedText + OCR_MERGE_SEPARATOR + backResult.combinedText
        : frontResult.combinedText;

      setResult({
        front: frontResult,
        back: backResult,
        mergedText,
        completedAt: new Date().toISOString(),
        fields,
        frontDetection,
        backDetection,
      });
      setStatus("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "OCR processing failed.");
      setStatus("error");
    } finally {
      setProgress(null);
    }
  }, [frontFile, backFile]);

  const handleReset = useCallback(() => {
    if (frontFile?.previewUrl) URL.revokeObjectURL(frontFile.previewUrl);
    if (backFile?.previewUrl) URL.revokeObjectURL(backFile.previewUrl);
    setFrontFile(null);
    setBackFile(null);
    setProgress(null);
    setResult(null);
    setErrorMsg("");
    setQualityWarning("");
    setStatus("idle");
  }, [frontFile, backFile]);

  return {
    status,
    workerReady,
    frontFile,
    backFile,
    progress,
    result,
    errorMsg,
    qualityWarning,
    handleFileSelect,
    handleClearFile,
    handleProcess,
    handleReset,
  };
}
