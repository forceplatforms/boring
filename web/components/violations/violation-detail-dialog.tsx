"use client";

import { AlertTriangle, FileText, Shield } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { Violation } from "@/lib/types/api";

interface ViolationDetailDialogProps {
  violation: Violation | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
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

export function ViolationDetailDialog({
  violation,
  open,
  onOpenChange,
}: ViolationDetailDialogProps) {
  if (!violation) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-destructive" />
            Compliance Violation Details
          </DialogTitle>
          <DialogDescription>
            Detailed analysis of the compliance gap
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Status Badges */}
          <div className="flex items-center gap-2">
            <Badge variant={getSeverityVariant(violation.severity)}>
              {violation.severity} severity
            </Badge>
            <Badge variant={getStatusVariant(violation.status)}>
              {getStatusLabel(violation.status)}
            </Badge>
          </div>

          {/* Requirement */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Shield className="h-4 w-4 text-primary" />
              <h3 className="font-semibold">Requirement</h3>
            </div>
            <p className="text-sm bg-background-secondary rounded-lg p-3">
              {violation.requirement}
            </p>
          </div>

          {/* Gap Analysis */}
          {violation.evidence?.gap_analysis && (
            <div className="space-y-2">
              <h3 className="font-semibold">Gap Analysis</h3>
              <p className="text-sm bg-destructive/5 border border-destructive/20 rounded-lg p-3">
                {violation.evidence.gap_analysis}
              </p>
            </div>
          )}

          {/* Evidence */}
          {violation.evidence && (
            <div className="space-y-4">
              <h3 className="font-semibold">Evidence</h3>

              {/* Target Quote (Requirement) */}
              {violation.evidence.target_quote && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1 w-1 rounded-full bg-primary" />
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Framework Requirement
                    </p>
                  </div>
                  <div className="bg-background-secondary rounded-lg p-4 border-l-4 border-primary">
                    <p className="text-sm leading-relaxed">
                      {violation.evidence.target_quote}
                    </p>
                  </div>
                </div>
              )}

              {/* Source Quote (Document) */}
              {violation.evidence.source_quote && (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="h-1 w-1 rounded-full bg-destructive" />
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Document Content
                    </p>
                  </div>
                  <div className="bg-background-secondary rounded-lg p-4 border-l-4 border-destructive">
                    <p className="text-sm leading-relaxed">
                      {violation.evidence.source_quote}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Metadata */}
          <div className="grid gap-4 md:grid-cols-2 text-sm">
            <div className="space-y-1">
              <p className="text-muted-foreground">Document</p>
              <div className="flex items-center gap-2">
                <FileText className="h-4 w-4 text-primary" />
                <p className="font-medium">
                  {violation.document_name || "Unknown"}
                </p>
              </div>
            </div>

            <div className="space-y-1">
              <p className="text-muted-foreground">Detected</p>
              <p className="font-medium">{formatDate(violation.created_at)}</p>
            </div>

            {violation.assigned_to && (
              <div className="space-y-1">
                <p className="text-muted-foreground">Assigned To</p>
                <p className="font-medium">{violation.assigned_to}</p>
              </div>
            )}

            {violation.updated_at && (
              <div className="space-y-1">
                <p className="text-muted-foreground">Last Updated</p>
                <p className="font-medium">{formatDate(violation.updated_at)}</p>
              </div>
            )}
          </div>

          {/* Recommendations */}
          {violation.recommendations && violation.recommendations.length > 0 && (
            <div className="space-y-2">
              <h3 className="font-semibold">Recommendations</h3>
              <ul className="space-y-2">
                {violation.recommendations.map((rec, index) => (
                  <li
                    key={index}
                    className="flex items-start gap-2 text-sm bg-background-secondary rounded-lg p-3"
                  >
                    <div className="h-5 w-5 shrink-0 flex items-center justify-center rounded-full bg-primary/10 text-primary text-xs font-medium mt-0.5">
                      {index + 1}
                    </div>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
