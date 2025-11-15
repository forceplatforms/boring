"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileText, AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import { formatBytes } from "@/lib/utils";
import {
  UPLOAD_CONSTRAINTS,
  validateFiles,
  type UploadProgress,
} from "@/lib/api/documents";

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpload: (files: File[], indexName: string, options: {
    onProgress: (progress: UploadProgress) => void;
    signal: AbortSignal;
  }) => Promise<void>;
  isUploading?: boolean;
  defaultIndexName?: string;
}

export function UploadDialog({
  open,
  onOpenChange,
  onUpload,
  isUploading = false,
  defaultIndexName,
}: UploadDialogProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [indexName, setIndexName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Set default index name when dialog opens
  useEffect(() => {
    if (open && defaultIndexName) {
      setIndexName(defaultIndexName);
    }
  }, [open, defaultIndexName]);

  // Reset state when dialog closes
  useEffect(() => {
    if (!open) {
      setSelectedFiles([]);
      setIndexName(defaultIndexName || "");
      setError(null);
      setUploadProgress(0);
      abortControllerRef.current = null;
    }
  }, [open, defaultIndexName]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);

    // Validate file types (only PDFs)
    const pdfFiles = acceptedFiles.filter(
      (file) => file.type === "application/pdf"
    );

    if (pdfFiles.length !== acceptedFiles.length) {
      const rejectedCount = acceptedFiles.length - pdfFiles.length;
      toast.error(`${rejectedCount} non-PDF file(s) rejected`);
    }

    // Check if adding these files would exceed limits
    const newFiles = [...selectedFiles, ...pdfFiles];
    const validation = validateFiles(newFiles);

    if (!validation.valid) {
      const errorMsg = validation.errors[0]?.error || "Invalid files";
      setError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    setSelectedFiles(newFiles);
    if (pdfFiles.length > 0) {
      toast.success(`${pdfFiles.length} file(s) added`);
    }
  }, [selectedFiles]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    disabled: isUploading,
    maxSize: UPLOAD_CONSTRAINTS.MAX_FILE_SIZE,
  });

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setError(null);
  };

  const handleUpload = async () => {
    setError(null);

    // Validate
    if (selectedFiles.length === 0) {
      const errorMsg = "Please select at least one file";
      setError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    if (!indexName.trim()) {
      const errorMsg = "Please enter an index name";
      setError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    // Validate index name format
    const indexNameRegex = /^[a-z0-9_]+$/;
    if (!indexNameRegex.test(indexName.trim())) {
      const errorMsg = "Index name must contain only lowercase letters, numbers, and underscores";
      setError(errorMsg);
      toast.error(errorMsg);
      return;
    }

    // Final validation
    const validation = validateFiles(selectedFiles);
    if (!validation.valid) {
      const errorMsg = validation.errors.map(e => `${e.file}: ${e.error}`).join("; ");
      setError(errorMsg);
      toast.error("Validation failed", {
        description: errorMsg,
      });
      return;
    }

    // Create abort controller for cancellation
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      await onUpload(selectedFiles, indexName.trim(), {
        onProgress: (progress) => {
          setUploadProgress(progress.percentage);
        },
        signal: controller.signal,
      });

      // Success handled by parent component
      // Dialog will be closed by parent
    } catch (err: any) {
      // Only show error if not cancelled
      if (err.name !== "AbortError" && err.name !== "CanceledError") {
        const errorMsg = err.message || "Upload failed";
        setError(errorMsg);
        // Error toast handled by parent component
      }
    }
  };

  const handleCancel = () => {
    if (isUploading && abortControllerRef.current) {
      abortControllerRef.current.abort();
      toast.info("Upload cancelled");
      setUploadProgress(0);
    }
  };

  const handleClose = () => {
    if (!isUploading) {
      onOpenChange(false);
    } else {
      toast.warning("Please wait for upload to complete or cancel it first");
    }
  };

  // Calculate total size
  const totalSize = selectedFiles.reduce((sum, file) => sum + file.size, 0);
  const totalSizeMB = totalSize / 1024 / 1024;
  const maxSizeMB = UPLOAD_CONSTRAINTS.MAX_TOTAL_SIZE / 1024 / 1024;

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
          <DialogDescription>
            Upload PDF documents for compliance analysis and indexing
            <span className="block mt-1 text-xs">
              Max {UPLOAD_CONSTRAINTS.MAX_FILE_COUNT} files, {Math.round(UPLOAD_CONSTRAINTS.MAX_FILE_SIZE / 1024 / 1024)}MB per file, {Math.round(maxSizeMB)}MB total
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Index Name Input */}
          <div className="space-y-2">
            <Label htmlFor="indexName">Index Name *</Label>
            <Input
              id="indexName"
              placeholder="e.g., company-policies"
              value={indexName}
              onChange={(e) => {
                setIndexName(e.target.value);
                setError(null);
              }}
              disabled={isUploading}
            />
            <p className="text-xs text-muted-foreground">
              Lowercase letters, numbers, and underscores only
            </p>
          </div>

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={`
              relative rounded-lg border-2 border-dashed p-8 text-center
              transition-colors cursor-pointer
              ${
                isDragActive
                  ? "border-primary bg-primary/5"
                  : "border-border hover:border-primary/50 hover:bg-accent/5"
              }
              ${isUploading ? "opacity-50 cursor-not-allowed" : ""}
            `}
          >
            <input {...getInputProps()} />
            <div className="flex flex-col items-center gap-2">
              <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                <Upload className="h-6 w-6 text-primary" />
              </div>
              {isDragActive ? (
                <p className="text-sm font-medium">Drop files here...</p>
              ) : (
                <>
                  <p className="text-sm font-medium">
                    Drag & drop PDF files here
                  </p>
                  <p className="text-xs text-muted-foreground">
                    or click to browse
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Upload Progress */}
          {isUploading && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Uploading...</span>
                <span className="font-medium">{uploadProgress}%</span>
              </div>
              <Progress value={uploadProgress} className="h-2" />
              <p className="text-xs text-muted-foreground text-center">
                Uploading files to server. Processing will continue in background.
              </p>
            </div>
          )}

          {/* Error Message */}
          {error && !isUploading && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span className="flex-1">{error}</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setError(null)}
                className="h-auto p-1"
              >
                <X className="h-3 w-3" />
              </Button>
            </div>
          )}

          {/* Selected Files List */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Selected Files ({selectedFiles.length}/{UPLOAD_CONSTRAINTS.MAX_FILE_COUNT})</Label>
                <span className="text-xs text-muted-foreground">
                  Total: {formatBytes(totalSize)} / {Math.round(maxSizeMB)}MB
                </span>
              </div>
              <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-border p-3">
                {selectedFiles.map((file, index) => (
                  <div
                    key={index}
                    className="flex items-center gap-3 rounded-md bg-background-secondary p-2"
                  >
                    <FileText className="h-4 w-4 text-primary shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-sm font-medium">
                        {file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatBytes(file.size)}
                      </p>
                    </div>
                    {!isUploading && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 shrink-0"
                        onClick={() => removeFile(index)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            {isUploading ? (
              <>
                <Button
                  variant="destructive"
                  onClick={handleCancel}
                >
                  <XCircle className="h-4 w-4 mr-2" />
                  Cancel Upload
                </Button>
              </>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={handleClose}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleUpload}
                  disabled={selectedFiles.length === 0 || !indexName.trim()}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload {selectedFiles.length > 0 && `(${selectedFiles.length})`}
                </Button>
              </>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
