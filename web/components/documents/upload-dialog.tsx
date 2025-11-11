"use client";

import { useState, useCallback, useEffect } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, X, FileText, AlertCircle } from "lucide-react";
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
import { formatBytes } from "@/lib/utils";

interface UploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onUpload: (files: File[], indexName: string) => void;
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

  // Set default index name when dialog opens
  useEffect(() => {
    if (open && defaultIndexName) {
      setIndexName(defaultIndexName);
    }
  }, [open, defaultIndexName]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setError(null);

    // Validate file types (only PDFs)
    const pdfFiles = acceptedFiles.filter(
      (file) => file.type === "application/pdf"
    );

    if (pdfFiles.length !== acceptedFiles.length) {
      setError("Only PDF files are supported");
    }

    setSelectedFiles((prev) => [...prev, ...pdfFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
    },
    disabled: isUploading,
  });

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleUpload = () => {
    if (selectedFiles.length === 0) {
      setError("Please select at least one file");
      return;
    }

    if (!indexName.trim()) {
      setError("Please enter an index name");
      return;
    }

    onUpload(selectedFiles, indexName);
  };

  const handleClose = () => {
    if (!isUploading) {
      setSelectedFiles([]);
      setIndexName("");
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
          <DialogDescription>
            Upload PDF documents for compliance analysis and indexing
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Index Name Input */}
          <div className="space-y-2">
            <Label htmlFor="indexName">Index Name</Label>
            <Input
              id="indexName"
              placeholder="e.g., company-policies"
              value={indexName}
              onChange={(e) => setIndexName(e.target.value)}
              disabled={isUploading}
            />
            <p className="text-xs text-muted-foreground">
              Documents will be indexed under this name for vector search
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

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Selected Files List */}
          {selectedFiles.length > 0 && (
            <div className="space-y-2">
              <Label>Selected Files ({selectedFiles.length})</Label>
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
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isUploading}
            >
              Cancel
            </Button>
            <Button onClick={handleUpload} disabled={isUploading}>
              {isUploading ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
                  Uploading...
                </>
              ) : (
                <>
                  <Upload className="h-4 w-4 mr-2" />
                  Upload {selectedFiles.length > 0 && `(${selectedFiles.length})`}
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
