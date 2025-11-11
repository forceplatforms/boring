"use client";

import { useState } from "react";
import { Shield, MoreVertical, Trash2, Eye, CheckCircle2, Upload } from "lucide-react";
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
import { formatDate } from "@/lib/utils";
import type { ComplianceFramework } from "@/lib/types/api";

interface FrameworksTableProps {
  frameworks: ComplianceFramework[];
  onDelete?: (id: string) => void;
  onView?: (framework: ComplianceFramework) => void;
  onUploadDocuments?: (framework: ComplianceFramework) => void;
  isDeleting?: boolean;
}

export function FrameworksTable({
  frameworks,
  onDelete,
  onView,
  onUploadDocuments,
  isDeleting = false,
}: FrameworksTableProps) {
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

  if (frameworks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 mb-4">
          <Shield className="h-10 w-10 text-primary" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No frameworks found</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          Create your first compliance framework to start checking documents
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[40%]">Framework</TableHead>
            <TableHead>Requirements</TableHead>
            <TableHead>Index Name</TableHead>
            <TableHead>Created</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {frameworks.map((framework) => (
            <TableRow key={framework.id} className="group">
              <TableCell>
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Shield className="h-5 w-5 text-primary" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-sm">{framework.name}</p>
                    {framework.description && (
                      <p className="truncate text-xs text-muted-foreground">
                        {framework.description}
                      </p>
                    )}
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium">
                    {framework.compliance_todos.length}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    requirements
                  </span>
                </div>
              </TableCell>
              <TableCell>
                <code className="rounded bg-background-secondary px-2 py-1 text-xs font-mono">
                  {framework.framework_index_name}
                </code>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(framework.created_at)}
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
                      onClick={() => onUploadDocuments && onUploadDocuments(framework)}
                      className="gap-2"
                    >
                      <Upload className="h-4 w-4" />
                      Upload Documents
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => onView && onView(framework)}
                      className="gap-2"
                    >
                      <Eye className="h-4 w-4" />
                      View Details
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      onClick={() => handleDelete(framework.id)}
                      disabled={deletingId === framework.id}
                      className="gap-2 text-destructive focus:text-destructive"
                    >
                      <Trash2 className="h-4 w-4" />
                      {deletingId === framework.id ? "Deleting..." : "Delete"}
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
