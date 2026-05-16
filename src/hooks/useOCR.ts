import { useState, useCallback, useEffect } from "react";
import type {
  OCRStatus,
  DocumentSide,
  UploadedFile,
  OCRProgressEvent,
  OCRExtractorResult,
} from "@/types";
import {
  validateOCRFile,
  createPreviewUrl,
} from "@/services/fileValidation.service";
import { initPdfWorker, getPdfPageCount } from "@/services/pdfRenderer.service";
import {
  initOCRWorker,
  terminateOCRWorker,
  recognizeFile,
} from "@/services/tesseract.service";
import { OCR_MERGE_SEPARATOR } from "@/constants/ocr";

export interface UseOCRReturn {
  status: OCRStatus;
  frontFile: UploadedFile | null;
  backFile: UploadedFile | null;
  progress: OCRProgressEvent | null;
  result: OCRExtractorResult | null;
  errorMsg: string;
  handleFileSelect: (file: File, side: DocumentSide) => Promise<void>;
  handleClearFile: (side: DocumentSide) => void;
  handleProcess: () => Promise<void>;
  handleReset: () => void;
}

export function useOCR(): UseOCRReturn {
  const [status, setStatus] = useState<OCRStatus>("idle");
  const [frontFile, setFrontFile] = useState<UploadedFile | null>(null);
  const [backFile, setBackFile] = useState<UploadedFile | null>(null);
  const [progress, setProgress] = useState<OCRProgressEvent | null>(null);
  const [result, setResult] = useState<OCRExtractorResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>("");

  useEffect(() => {
    initPdfWorker();
    initOCRWorker();
    return () => {
      terminateOCRWorker();
    };
  }, []);

  const handleFileSelect = useCallback(
    async (file: File, side: DocumentSide) => {
      const validationError = validateOCRFile(file);
      if (validationError) {
        setErrorMsg(validationError.message);
        setStatus("error");
        return;
      }

      setStatus("uploading");
      setErrorMsg("");

      // Revoke previous URL for this side
      if (side === "front" && frontFile?.previewUrl) {
        URL.revokeObjectURL(frontFile.previewUrl);
      }
      if (side === "back" && backFile?.previewUrl) {
        URL.revokeObjectURL(backFile.previewUrl);
      }

      const previewUrl = createPreviewUrl(file);
      const mimeType = file.type as UploadedFile["mimeType"];

      let pageCount: number | undefined;
      if (file.type === "application/pdf") {
        try {
          pageCount = await getPdfPageCount(file);
        } catch {
          setErrorMsg("Could not read the PDF. The file may be corrupted.");
          setStatus("error");
          URL.revokeObjectURL(previewUrl);
          return;
        }
      }

      const uploaded: UploadedFile = { side, file, previewUrl, mimeType, pageCount };

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
      setErrorMsg("Front page is required before processing.");
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

      const mergedText = backResult
        ? frontResult.combinedText + OCR_MERGE_SEPARATOR + backResult.combinedText
        : frontResult.combinedText;

      setResult({
        front: frontResult,
        back: backResult,
        mergedText,
        completedAt: new Date().toISOString(),
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
    setStatus("idle");
  }, [frontFile, backFile]);

  return {
    status,
    frontFile,
    backFile,
    progress,
    result,
    errorMsg,
    handleFileSelect,
    handleClearFile,
    handleProcess,
    handleReset,
  };
}
