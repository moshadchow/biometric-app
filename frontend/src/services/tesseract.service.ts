import { createWorker, PSM } from "tesseract.js";
import type Tesseract from "tesseract.js";
import { OCR_LANGUAGES, OCR_PAGE_SEPARATOR, OCR_MIN_IMAGE_HEIGHT, OCR_DPI } from "@/constants/ocr";
import type { DocumentSide, OCRPageResult, OCRSideResult, OCRProgressEvent } from "@/types";
import { getAllPdfPagesAsCanvases } from "./pdfRenderer.service";

type TesseractWorker = Tesseract.Worker;

let worker: TesseractWorker | null = null;
let currentProgressCallback: ((evt: OCRProgressEvent) => void) | null = null;
let currentSide: DocumentSide = "front";
const IGNORED_TESSERACT_WARNINGS = [
  "Parameter not found: segsearch_max_futile_classifications",
  "Parameter not found: classify_misfit_junk_penalty",
];
let tesseractWarningFilterInstalled = false;

function shouldIgnoreTesseractWarning(args: unknown[]): boolean {
  const text = args.map((arg) => String(arg)).join(" ");
  return IGNORED_TESSERACT_WARNINGS.some((warning) => text.includes(warning));
}

function installTesseractWarningFilter(): void {
  if (tesseractWarningFilterInstalled || typeof console === "undefined") {
    return;
  }
  const originalWarn = console.warn.bind(console);
  console.warn = (...args: unknown[]) => {
    if (shouldIgnoreTesseractWarning(args)) {
      return;
    }
    originalWarn(...args);
  };
  tesseractWarningFilterInstalled = true;
}

export function setProgressCallback(
  cb: ((evt: OCRProgressEvent) => void) | null,
  side: DocumentSide = "front"
): void {
  currentProgressCallback = cb;
  currentSide = side;
}

export async function initOCRWorker(): Promise<void> {
  if (worker !== null) return;
  installTesseractWarningFilter();
  worker = await createWorker(OCR_LANGUAGES, 1, {
    logger: (m: Tesseract.LoggerMessage) => {
      const message = "message" in m && typeof m.message === "string" ? m.message : "";
      if (message && IGNORED_TESSERACT_WARNINGS.some((warning) => message.includes(warning))) {
        return;
      }
      if (!currentProgressCallback) return;
      if (m.status === "recognizing text" || m.status === "loading language traineddata" || m.status === "initializing tesseract") {
        currentProgressCallback({
          side: currentSide,
          progress: Math.round((m.progress ?? 0) * 100),
          statusText: m.status,
        });
      }
    },
  });
  // PSM.AUTO_OSD lets Tesseract analyse the ID card layout — critical for cards with a
  // photo column alongside text columns, where SINGLE_BLOCK merges/drops mixed-script rows.
  // preserve_interword_spaces: prevents adjacent words/numbers from being merged.
  await worker.setParameters({
    user_defined_dpi: OCR_DPI,
    tessedit_pageseg_mode: PSM.AUTO_OSD,
    preserve_interword_spaces: "1",
  });
}

export async function terminateOCRWorker(): Promise<void> {
  if (worker !== null) {
    await worker.terminate();
    worker = null;
  }
}

export async function recognizeCanvas(
  canvas: HTMLCanvasElement,
  pageNumber: number
): Promise<OCRPageResult> {
  if (!worker) throw new Error("OCR worker not initialized");
  const result = await worker.recognize(canvas);
  return {
    pageNumber,
    text: result.data.text,
    confidence: result.data.confidence,
  };
}

export async function recognizeFile(
  file: File,
  onProgress: (evt: OCRProgressEvent) => void,
  side: DocumentSide
): Promise<OCRSideResult> {
  setProgressCallback(onProgress, side);

  const startTime = performance.now();
  const pages: OCRPageResult[] = [];

  if (file.type === "application/pdf") {
    const canvases = await getAllPdfPagesAsCanvases(file);
    const total = canvases.length;
    for (let i = 0; i < total; i++) {
      const canvas = canvases[i];
      // Wrap progress to map page progress into global progress
      setProgressCallback((evt) => {
        onProgress({
          ...evt,
          progress: Math.round((i / total) * 100 + (evt.progress / total)),
        });
      }, side);
      const pageResult = await recognizeCanvas(canvas, i + 1);
      pages.push(pageResult);
      // Free pixel buffer memory
      canvas.width = 0;
      canvas.height = 0;
    }
  } else {
    // Image file — load as HTMLImageElement and pass to Tesseract
    const imgUrl = URL.createObjectURL(file);
    try {
      const img = await loadImageElement(imgUrl);
      const canvas = document.createElement("canvas");
      const scale = img.naturalHeight < OCR_MIN_IMAGE_HEIGHT
        ? OCR_MIN_IMAGE_HEIGHT / img.naturalHeight
        : 1;
      canvas.width = Math.round(img.naturalWidth * scale);
      canvas.height = Math.round(img.naturalHeight * scale);
      const ctx = canvas.getContext("2d", { willReadFrequently: true })!;
      if (scale > 1) {
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
      }
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      enhanceForOCR(ctx, canvas.width, canvas.height);
      const pageResult = await recognizeCanvas(canvas, 1);
      pages.push(pageResult);
      canvas.width = 0;
      canvas.height = 0;
    } finally {
      URL.revokeObjectURL(imgUrl);
    }
  }

  setProgressCallback(null);

  const averageConfidence =
    pages.length > 0
      ? Math.round(pages.reduce((sum, p) => sum + p.confidence, 0) / pages.length)
      : 0;

  const combinedText = pages
    .map((p) =>
      pages.length > 1
        ? OCR_PAGE_SEPARATOR.replace("{n}", String(p.pageNumber)) + p.text
        : p.text
    )
    .join("")
    .trim();

  return {
    side,
    pages,
    combinedText,
    averageConfidence,
    processingTimeMs: Math.round(performance.now() - startTime),
  };
}

function loadImageElement(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load image: ${src}`));
    img.src = src;
  });
}

// Grayscale + contrast stretch to improve OCR on low-contrast ID card scans.
// Converts to greyscale then stretches the histogram to full 0–255 range.
function enhanceForOCR(ctx: CanvasRenderingContext2D, w: number, h: number): void {
  const imageData = ctx.getImageData(0, 0, w, h);
  const d = imageData.data;
  let min = 255, max = 0;
  // Convert to greyscale and find min/max
  for (let i = 0; i < d.length; i += 4) {
    const gray = Math.round(0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]);
    d[i] = d[i + 1] = d[i + 2] = gray;
    if (gray < min) min = gray;
    if (gray > max) max = gray;
  }
  // Stretch contrast to 0–255
  const range = max - min || 1;
  for (let i = 0; i < d.length; i += 4) {
    const stretched = Math.round(((d[i] - min) / range) * 255);
    d[i] = d[i + 1] = d[i + 2] = stretched;
  }
  ctx.putImageData(imageData, 0, 0);
}
