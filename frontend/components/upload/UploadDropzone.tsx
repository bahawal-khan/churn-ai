"use client";

import { useRef, useState } from "react";

import { Icon } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api/client";
import { cn } from "@/lib/utils";

const MAX_UPLOAD_SIZE_MB = 25;
const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

export interface UploadDropzoneProps<T> {
  onUpload: (file: File, onProgress: (fraction: number) => void) => Promise<T>;
  onSuccess: (result: T, file: File) => void;
  label?: string;
  hint?: string;
}

/** Drag-and-drop or click-to-browse `.csv` upload (`docs/FRONTEND_SPEC.md`
 * §10), mirroring `backend/services/file_service.py`'s 25 MB limit
 * client-side before any network call. Reused by `/upload` (training
 * datasets) and `/predict` batch (via the `onUpload` prop). */
export function UploadDropzone<T>({ onUpload, onSuccess, label, hint }: UploadDropzoneProps<T>) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);

  function validate(file: File): string | null {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      return "Only .csv files are supported.";
    }
    if (file.size === 0) {
      return "This file is empty.";
    }
    if (file.size > MAX_UPLOAD_SIZE_BYTES) {
      return `This file is too large. The maximum upload size is ${MAX_UPLOAD_SIZE_MB} MB.`;
    }
    return null;
  }

  async function handleFile(file: File) {
    setUploadError(null);
    setValidationError(null);
    setFileName(file.name);

    const error = validate(file);
    if (error) {
      setValidationError(error);
      return;
    }

    setProgress(0);
    try {
      const result = await onUpload(file, setProgress);
      onSuccess(result, file);
    } catch (err) {
      setUploadError(err instanceof ApiError ? err.message : "Upload failed. Please try again.");
    } finally {
      setProgress(null);
    }
  }

  return (
    <div className="flex flex-col gap-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragActive(false);
          const file = e.dataTransfer.files?.[0];
          if (file) handleFile(file);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
        }}
        className={cn(
          "flex min-h-[160px] cursor-pointer flex-col items-center justify-center gap-2 rounded-card border-2 border-dashed p-8 text-center transition-colors",
          dragActive ? "border-accent-primary bg-accent-primary-soft" : "border-border-subtle hover:border-border-strong"
        )}
      >
        <Icon name="upload" size={28} className="text-text-muted" />
        <p className="text-sm font-medium text-text-primary">{label ?? "Drag & drop a CSV file, or click to browse"}</p>
        <p className="text-xs text-text-muted">{hint ?? `.csv only, up to ${MAX_UPLOAD_SIZE_MB} MB`}</p>
        <input
          ref={inputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
      </div>

      {fileName && progress !== null && (
        <div className="flex items-center gap-2">
          <div className="h-2 flex-1 overflow-hidden rounded-pill bg-bg-elevated">
            <div
              className="h-full rounded-pill bg-accent-primary transition-[width]"
              style={{ width: `${Math.round(progress * 100)}%` }}
            />
          </div>
          <span className="w-10 text-right text-xs text-text-muted">{Math.round(progress * 100)}%</span>
        </div>
      )}

      {validationError && (
        <p role="alert" className="rounded-control bg-danger-soft p-2.5 text-sm text-danger">
          {validationError}
        </p>
      )}
      {uploadError && (
        <div className="flex items-center justify-between gap-2 rounded-control bg-danger-soft p-2.5 text-sm text-danger">
          <span>{uploadError}</span>
          <Button size="sm" variant="ghost" onClick={() => inputRef.current?.click()}>
            Retry
          </Button>
        </div>
      )}
    </div>
  );
}
