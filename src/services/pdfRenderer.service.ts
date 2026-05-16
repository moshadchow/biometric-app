import * as pdfjsLib from "pdfjs-dist";
import pdfjsWorkerUrl from "pdfjs-dist/build/pdf.worker.mjs?url";
import { PDF_RENDER_SCALE } from "@/constants/ocr";

let workerInitialized = false;

export function initPdfWorker(): void {
  if (workerInitialized) return;
  pdfjsLib.GlobalWorkerOptions.workerSrc = pdfjsWorkerUrl;
  workerInitialized = true;
}

export async function getPdfPageCount(file: File): Promise<number> {
  const data = await file.arrayBuffer();
  const doc = await pdfjsLib.getDocument({ data }).promise;
  const count = doc.numPages;
  doc.destroy();
  return count;
}

export async function renderPdfPageToCanvas(
  file: File,
  pageNumber: number,
  scale = PDF_RENDER_SCALE
): Promise<HTMLCanvasElement> {
  const data = await file.arrayBuffer();
  const doc = await pdfjsLib.getDocument({ data }).promise;
  const page = await doc.getPage(pageNumber);
  const viewport = page.getViewport({ scale });
  const canvas = document.createElement("canvas");
  canvas.width = Math.floor(viewport.width);
  canvas.height = Math.floor(viewport.height);
  await page.render({ canvas, viewport }).promise;
  page.cleanup();
  doc.destroy();
  return canvas;
}

export async function getAllPdfPagesAsCanvases(
  file: File,
  scale = PDF_RENDER_SCALE
): Promise<HTMLCanvasElement[]> {
  const count = await getPdfPageCount(file);
  const canvases: HTMLCanvasElement[] = [];
  for (let i = 1; i <= count; i++) {
    canvases.push(await renderPdfPageToCanvas(file, i, scale));
  }
  return canvases;
}
