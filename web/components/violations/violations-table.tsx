"use client";

import { useState } from "react";
import { AlertTriangle, MoreVertical, Eye, Check } from "lucide-react";
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
import type { Violation } from "@/lib/types/api";

interface ViolationsTableProps {
  violations: Violation[];
  onView?: (violation: Violation) => void;
  onAcknowledge?: (id: string) => void;
  isUpdating?: boolean;
}

function getSeverityVariant(
  severity: string
): "critical" | "high" | "medium" | "low" {
  switch (severity) {
    case "critical":
      return "critical";
    case "high":
      return "high";
    case "medium":
      return "medium";
    case "low":
      return "low";
    default:
      return "low";
  }
}

function getStatusVariant(status: string) {
  switch (status) {
    case "open":
      return "destructive";
    case "assigned":
      return "warning";
    case "in_progress":
      return "info";
    case "remediated":
      return "success";
    case "false_positive":
      return "secondary";
    default:
      return "default";
  }
}

function getStatusLabel(status: string) {
  switch (status) {
    case "open":
      return "Open";
    case "assigned":
      return "Assigned";
    case "in_progress":
      return "In Progress";
    case "remediated":
      return "Remediated";
    case "false_positive":
      return "False Positive";
    default:
      return status;
  }
}

export function ViolationsTable({
  violations,
  onView,
  onAcknowledge,
  isUpdating = false,
}: ViolationsTableProps) {
  const [acknowledgingId, setAcknowledgingId] = useState<string | null>(null);

  const handleAcknowledge = async (id: string) => {
    if (onAcknowledge) {
      setAcknowledgingId(id);
      try {
        await onAcknowledge(id);
      } finally {
        setAcknowledgingId(null);
      }
    }
  };

  if (violations.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-full bg-green-500/10 mb-4">
          <Check className="h-10 w-10 text-green-500" />
        </div>
        <h3 className="text-lg font-semibold mb-2">No violations found</h3>
        <p className="text-sm text-muted-foreground max-w-sm">
          All compliance checks passed successfully
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="w-[35%]">Requirement</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Status</TableHead>
            <TableHead>Document</TableHead>
            <TableHead>Detected</TableHead>
            <TableHead className="text-right">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {violations.map((violation) => (
            <TableRow key={violation.id} className="group">
              <TableCell>
                <div className="flex items-start gap-3">
                  <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium line-clamp-2">
                      {violation.rule_citation}
                    </p>
                    {violation.finding_summary && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                        {violation.finding_summary}
                      </p>
                    )}
                  </div>
                </div>
              </TableCell>
              <TableCell>
                <Badge variant={getSeverityVariant(violation.severity)}>
                  {violation.severity}
                </Badge>
              </TableCell>
              <TableCell>
                <Badge variant={getStatusVariant(violation.status)}>
                  {getStatusLabel(violation.status)}
                </Badge>
              </TableCell>
              <TableCell>
                <p className="text-sm truncate max-w-[200px]">
                  {violation.source_document_name || "Unknown"}
                </p>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {formatDate(violation.created_at)}
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
                      onClick={() => onView && onView(violation)}
                      className="gap-2"
                    >
                      <Eye className="h-4 w-4" />
                      View Details
                    </DropdownMenuItem>
                    {violation.status === "open" && (
                      <DropdownMenuItem
                        onClick={() => handleAcknowledge(violation.id)}
                        disabled={acknowledgingId === violation.id}
                        className="gap-2"
                      >
                        <Check className="h-4 w-4" />
                        {acknowledgingId === violation.id
                          ? "Acknowledging..."
                          : "Acknowledge"}
                      </DropdownMenuItem>
                    )}
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
