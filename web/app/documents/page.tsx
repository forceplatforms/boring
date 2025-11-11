"use client";

import { useState } from "react";
import { Upload, RefreshCw, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { UploadDialog } from "@/components/documents/upload-dialog";
import { DocumentsTable } from "@/components/documents/documents-table";
import {
  useDocuments,
  useDocumentStats,
  useIngestDocuments,
  useDeleteDocument,
} from "@/lib/hooks/use-documents";
import type { UploadProgress } from "@/lib/api/documents";

export default function DocumentsPage() {
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);

  // Fetch documents and stats
  const { data: documents, isLoading, error, refetch } = useDocuments();
  const { data: stats } = useDocumentStats();

  // Mutations
  const ingestMutation = useIngestDocuments();
  const deleteMutation = useDeleteDocument();

  const handleUpload = async (
    files: File[],
    indexName: string,
    options: {
      onProgress: (progress: UploadProgress) => void;
      signal: AbortSignal;
    }
  ) => {
    try {
      await ingestMutation.mutateAsync({
        files,
        indexName,
        onProgress: options.onProgress,
        signal: options.signal,
      });

      setUploadDialogOpen(false);
      toast.success("Upload successful!", {
        description: `${files.length} file(s) uploaded and indexed successfully`,
      });
    } catch (error: any) {
      // Only show error if not cancelled
      if (error.name !== "AbortError" && error.name !== "CanceledError") {
        console.error("Upload failed:", error);
        toast.error("Upload failed", {
          description: error.message || "An error occurred during upload",
        });
      }
      throw error; // Re-throw so dialog can handle it
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Document deleted successfully");
    } catch (error: any) {
      console.error("Delete failed:", error);
      toast.error("Delete failed", {
        description: error.message || "An error occurred while deleting",
      });
    }
  };

  // Calculate stats from data
  const totalDocs = documents?.items?.length || 0;
  const processingDocs =
    documents?.items?.filter((doc) => doc.indexing_status === "processing")
      .length || 0;
  const completedDocs =
    documents?.items?.filter((doc) => doc.indexing_status === "completed")
      .length || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground mt-1">
            Manage and ingest compliance documents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
          </Button>
          <Button className="gap-2" onClick={() => setUploadDialogOpen(true)}>
            <Upload className="h-4 w-4" />
            Upload Documents
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Documents
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDocs}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {totalDocs === 0 ? "No documents yet" : "Documents ingested"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Processing
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{processingDocs}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Documents being indexed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Completed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{completedDocs}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Ready for analysis
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">
                Failed to load documents
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                {error instanceof Error ? error.message : "Unknown error"}
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Documents Table */}
      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Loading documents...
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <DocumentsTable
              documents={documents?.items || []}
              onDelete={handleDelete}
              isDeleting={deleteMutation.isPending}
            />
          </CardContent>
        </Card>
      )}

      {/* Upload Dialog */}
      <UploadDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        onUpload={handleUpload}
        isUploading={ingestMutation.isPending}
      />
    </div>
  );
}
