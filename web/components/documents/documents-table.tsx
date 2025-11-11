"use client";

import { useState } from "react";
import { FileText, MoreVertical, Trash2, Eye, RefreshCw } from "lucide-react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDate, formatBytes } from "@/lib/utils";
import type { IngestedDocument } from "@/lib/types/api";

interface DocumentsTableProps {
  documents: IngestedDocument[];
  onDelete?: (id: string) => void;
  onView?: (document: IngestedDocument) => void;
  isDeleting?: boolean;
}

function getStatusVariant(status: string) {
  switch (status) {
    case "completed":
      return "success";
    case "processing":
      return "warning";
    case "failed":
      return "destructive";
    case "pending":
      return "secondary";
    default:
      return "default";
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case "completed":
      return "Completed";
    case "processing":
      return "Processing";
    case "failed":
      return "Failed";
    case "pending":
      return "Pending";
    default:
      return status;
  }
}

export function DocumentsTable({
  documents,
  onDelete,
  onView,
  isDeleting = false,
}: DocumentsTableProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (onDelete) {
      setDeletingId(id);
      try {
        await onDelete(id);
      } finally {
        setDeletingId(null);
      }
    }
  };

  if (documents.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 mb-4">
          <FileText className="h-10 w-10 text-primary" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No documents found</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Upload your first document to get started with compliance analysis
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[35%]">Document</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Index</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Size</TableHead>
            <TableHead>Uploaded</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id} className="group">
              <TableCell>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <FileText className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-sm">
                      {doc.filename}
                    </p>
                    {doc.metadata?.title && (
                      <p className="truncate text-xs text-muted-foreground">
                        {doc.metadata.title}
                      </p>
                    )}
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <Badge variant={getStatusVariant(doc.indexing_status)}>
                    {getStatusLabel(doc.indexing_status)}
                  </Badge>
                  {doc.indexing_status === "processing" && (
                    <RefreshCw className="h-3 w-3 animate-spin text-muted-foreground" />
                  )}
                </div>
              </TableCell>
              <TableCell>
                <span className="text-sm font-medium text-foreground">
                  {doc.index_name || "—"}
                </span>
              </TableCell>
              <TableCell>
                <span className="text-sm text-muted-foreground">
                  {doc.doc_type || "—"}
                </span>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {doc.file_size ? formatBytes(doc.file_size) : "—"}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(doc.created_at)}
              </TableCell>
              <TableCell className="text-right">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <MoreVertical className="h-4 w-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem
                      onClick={() => onView && onView(doc)}
                      className="gap-2"
                    >
                      <Eye className="h-4 w-4" />
                      View Details
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(doc.id)}
                      disabled={deletingId === doc.id}
                      className="gap-2 text-destructive focus:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                      {deletingId === doc.id ? "Deleting..." : "Delete"}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
