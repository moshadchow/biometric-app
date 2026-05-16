import React, { useRef, useState, useCallback } from "react";
import type { DocumentSide, UploadedFile } from "@/types";
import { OCR_ACCEPTED_EXTENSIONS, OCR_ACCEPTED_MIME_TYPES } from "@/constants/ocr";
import { formatFileSize } from "@/services/fileValidation.service";

interface FileUploadZoneProps {
  side: DocumentSide;
  uploadedFile: UploadedFile | null;
  onFileSelect: (file: File, side: DocumentSide) => void;
  onClear: (side: DocumentSide) => void;
  disabled?: boolean;
  label: string;
  acceptedExtensions?: string;
  acceptedMimeTypes?: readonly string[];
  acceptedLabel?: string;
}

const FileUploadZone: React.FC<FileUploadZoneProps> = ({
  side,
  uploadedFile,
  onFileSelect,
  onClear,
  disabled = false,
  label,
  acceptedExtensions,
  acceptedMimeTypes,
  acceptedLabel,
}) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);

  const handleClick = useCallback(() => {
    if (!disabled) inputRef.current?.click();
  }, [disabled]);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) onFileSelect(file, side);
      // Reset input so the same file can be re-selected
      e.target.value = "";
    },
    [onFileSelect, side]
  );

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => setIsDragging(false), []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (!file) return;
      const allowed = acceptedMimeTypes ?? (OCR_ACCEPTED_MIME_TYPES as readonly string[]);
      if (!allowed.includes(file.type)) return;
      onFileSelect(file, side);
    },
    [onFileSelect, side]
  );

  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onClear(side);
    },
    [onClear, side]
  );

  return (
    <div style={s.wrapper}>
      <div style={s.sideLabel}>{label}</div>
      <div
        style={{
          ...s.zone,
          borderColor: isDragging ? "#00e5a0" : uploadedFile ? "#333" : "#2a2a2a",
          background: isDragging ? "#0a1a12" : uploadedFile ? "#0d0d0d" : "#111",
          cursor: disabled ? "default" : "pointer",
          opacity: disabled ? 0.5 : 1,
        }}
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {uploadedFile ? (
          <div style={s.preview}>
            <button style={s.clearBtn} onClick={handleClear} title="Remove file">
              ×
            </button>
            {uploadedFile.mimeType === "application/pdf" ? (
              <div style={s.pdfPreview}>
                <div style={s.pdfIcon}>PDF</div>
                <div style={s.fileName}>{uploadedFile.file.name}</div>
                <div style={s.fileMeta}>
                  {uploadedFile.pageCount != null && (
                    <span style={s.badge}>{uploadedFile.pageCount} page{uploadedFile.pageCount !== 1 ? "s" : ""}</span>
                  )}
                  <span style={s.fileSize}>{formatFileSize(uploadedFile.file.size)}</span>
                </div>
              </div>
            ) : (
              <div style={s.imgPreview}>
                <img
                  src={uploadedFile.previewUrl}
                  alt="preview"
                  style={s.img}
                />
                <div style={s.fileName}>{uploadedFile.file.name}</div>
                <div style={s.fileSize}>{formatFileSize(uploadedFile.file.size)}</div>
              </div>
            )}
          </div>
        ) : (
          <div style={s.empty}>
            <div style={s.uploadIcon}>↑</div>
            <div style={s.hint}>Drop file or click to upload</div>
            <div style={s.accepted}>{acceptedLabel ?? "JPG, PNG, PDF · max 20 MB"}</div>
          </div>
        )}
      </div>
      <input
        ref={inputRef}
        type="file"
        accept={acceptedExtensions ?? OCR_ACCEPTED_EXTENSIONS}
        style={{ display: "none" }}
        onChange={handleFileChange}
        disabled={disabled}
      />
    </div>
  );
};

const s: Record<string, React.CSSProperties> = {
  wrapper: {
    flex: 1,
    minWidth: 0,
    display: "flex",
    flexDirection: "column",
    gap: 6,
  },
  sideLabel: {
    fontSize: 11,
    fontWeight: 600,
    color: "#666",
    letterSpacing: "0.5px",
    textTransform: "uppercase",
  },
  zone: {
    border: "1px dashed",
    borderRadius: 10,
    minHeight: 160,
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "border-color 0.15s, background 0.15s",
    position: "relative",
    overflow: "hidden",
  },
  empty: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    padding: "24px 16px",
  },
  uploadIcon: {
    fontSize: 28,
    color: "#444",
    lineHeight: 1,
  },
  hint: {
    fontSize: 13,
    color: "#666",
  },
  accepted: {
    fontSize: 11,
    color: "#444",
  },
  preview: {
    width: "100%",
    height: "100%",
    position: "relative",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: 12,
  },
  clearBtn: {
    position: "absolute",
    top: 8,
    right: 8,
    background: "#1e1e1e",
    border: "1px solid #333",
    borderRadius: "50%",
    color: "#999",
    width: 22,
    height: 22,
    fontSize: 14,
    lineHeight: "20px",
    textAlign: "center",
    cursor: "pointer",
    padding: 0,
    zIndex: 2,
    fontFamily: "inherit",
  },
  imgPreview: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 6,
    width: "100%",
  },
  img: {
    maxHeight: 120,
    maxWidth: "100%",
    borderRadius: 6,
    objectFit: "cover",
  },
  pdfPreview: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 8,
    padding: 8,
  },
  pdfIcon: {
    background: "#1e1e1e",
    border: "1px solid #333",
    borderRadius: 6,
    padding: "8px 14px",
    fontSize: 13,
    fontWeight: 700,
    color: "#ff9999",
    letterSpacing: 1,
  },
  fileName: {
    fontSize: 11,
    color: "#888",
    textAlign: "center",
    wordBreak: "break-all",
    maxWidth: "100%",
  },
  fileMeta: {
    display: "flex",
    alignItems: "center",
    gap: 8,
  },
  badge: {
    background: "#1a2a1a",
    border: "1px solid #2a4a2a",
    borderRadius: 20,
    padding: "2px 8px",
    fontSize: 11,
    color: "#00e5a0",
  },
  fileSize: {
    fontSize: 11,
    color: "#555",
  },
};

export default FileUploadZone;
