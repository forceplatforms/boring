"use client";

import { useEffect, useState } from "react";
import { FileText, CheckCircle2, Clock, AlertCircle, Loader2, XCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { useDocuments } from "@/lib/hooks/use-documents";
import { formatBytes } from "@/lib/utils";
import type { IngestedDocument } from "@/lib/types/api";

interface DocumentsStatusCardProps {
  frameworkIndexName?: string;
  limit?: number;
}

export function DocumentsStatusCard({
  frameworkIndexName,
  limit = 5,
}: DocumentsStatusCardProps) {
  // Fetch documents with polling for pending/processing documents
  const { data: documents, isLoading } = useDocuments(
    frameworkIndexName ? { index_name: frameworkIndexName, limit } : { limit },
    {
      refetchInterval: (query) => {
        const data = query.state.data;
        // Poll every 3 seconds if there are documents being processed
        const hasProcessing = data?.items?.some(
          (doc) => doc.indexing_status === "pending" || doc.indexing_status === "indexing"
        );
        return hasProcessing ? 3000 : false;
      },
    }
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "indexing":
      case "processing":
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />;
      case "pending":
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      completed: "default",
      indexing: "secondary",
      processing: "secondary",
      pending: "outline",
      failed: "destructive",
    };

    const labels: Record<string, string> = {
      completed: "Completed",
      indexing: "Processing",
      processing: "Processing",
      pending: "Pending",
      failed: "Failed",
    };

    return (
      <Badge variant={variants[status] || "outline"}>
        {labels[status] || status}
      </Badge>
    );
  };

  const getProcessingProgress = (status: string): number => {
    switch (status) {
      case "pending":
        return 10;
      case "indexing":
      case "processing":
        return 50;
      case "completed":
        return 100;
      case "failed":
        return 0;
      default:
        return 0;
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  const docs = documents?.items || [];

  if (docs.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Documents</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileText className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">
              No documents uploaded yet
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Upload documents to see them here
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Recent Documents</CardTitle>
          <Badge variant="outline">{docs.length} document(s)</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {docs.map((doc) => {
            const isProcessing =
              doc.indexing_status === "pending" ||
              doc.indexing_status === "indexing" ||
              doc.indexing_status === "processing";
            const progress = getProcessingProgress(doc.indexing_status);

            return (
              <div
                key={doc.id}
                className={`
                  rounded-lg border p-4 transition-all
                  ${isProcessing ? "border-primary/50 bg-primary/5" : "border-border"}
                `}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5">{getStatusIcon(doc.indexing_status)}</div>
                  <div className="flex-1 min-w-0 space-y-2">
                    {/* Document name and status */}
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm truncate">{doc.filename}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {formatBytes(doc.file_size)} • {doc.index_name || "No index"}
                        </p>
                      </div>
                      {getStatusBadge(doc.indexing_status)}
                    </div>

                    {/* Progress bar for processing documents */}
                    {isProcessing && (
                      <div className="space-y-1.5">
                        <Progress value={progress} className="h-1.5" />
                        <p className="text-xs text-muted-foreground">
                          {doc.indexing_status === "pending"
                            ? "Queued for processing..."
                            : "Processing document in background..."}
                        </p>
                      </div>
                    )}

                    {/* Completed info */}
                    {doc.indexing_status === "completed" && doc.num_pages && (
                      <p className="text-xs text-muted-foreground">
                        ✓ Indexed {doc.num_pages} page(s) successfully
                      </p>
                    )}

                    {/* Failed info */}
                    {doc.indexing_status === "failed" && doc.error_message && (
                      <p className="text-xs text-red-600">
                        Error: {doc.error_message}
                      </p>
                    )}

                    {/* Timestamps */}
                    <div className="flex items-center gap-3 text-xs text-muted-foreground">
                      <span>
                        Uploaded: {new Date(doc.created_at).toLocaleTimeString()}
                      </span>
                      {doc.updated_at !== doc.created_at && (
                        <span>
                          Updated: {new Date(doc.updated_at).toLocaleTimeString()}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
