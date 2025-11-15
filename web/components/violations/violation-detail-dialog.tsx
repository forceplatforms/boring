"use client";

import { AlertTriangle, FileText, Shield, Calendar, User, TrendingUp, Lightbulb, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

function getSeverityConfig(severity: string) {
  switch (severity) {
    case "critical":
      return {
        bg: "bg-red-500/10",
        bgGradient: "bg-gradient-to-br from-red-500/5 to-transparent",
        glow: "bg-red-500",
        icon: "text-red-600",
      };
    case "high":
      return {
        bg: "bg-orange-500/10",
        bgGradient: "bg-gradient-to-br from-orange-500/5 to-transparent",
        glow: "bg-orange-500",
        icon: "text-orange-600",
      };
    case "medium":
      return {
        bg: "bg-yellow-500/10",
        bgGradient: "bg-gradient-to-br from-yellow-500/5 to-transparent",
        glow: "bg-yellow-500",
        icon: "text-yellow-600",
      };
    default:
      return {
        bg: "bg-blue-500/10",
        bgGradient: "bg-gradient-to-br from-blue-500/5 to-transparent",
        glow: "bg-blue-500",
        icon: "text-blue-600",
      };
  }
}

function getStatusConfig(status: string) {
  switch (status) {
    case "open":
      return { label: "Open" };
    case "assigned":
      return { label: "Assigned" };
    case "in_progress":
      return { label: "In Progress" };
    case "remediated":
      return { label: "Remediated" };
    case "false_positive":
      return { label: "False Positive" };
    default:
      return { label: status };
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

  const severityConfig = getSeverityConfig(violation.severity);
  const statusConfig = getStatusConfig(violation.status);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto p-0">
        {/* Header with Gradient */}
        <div className={`relative ${severityConfig.bgGradient} px-8 py-6 border-b`}>
          <div className="absolute top-0 right-0 w-64 h-64 ${severityConfig.glow} rounded-full blur-3xl opacity-20 -mr-32 -mt-32" />
          <DialogHeader className="relative">
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-4">
                <div className={`h-14 w-14 rounded-2xl ${severityConfig.bg} flex items-center justify-center`}>
                  <AlertTriangle className={`h-7 w-7 ${severityConfig.icon}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant={getSeverityVariant(violation.severity)} className="text-xs font-semibold">
                      {violation.severity.toUpperCase()}
                    </Badge>
                    <Badge variant={getStatusVariant(violation.status)} className="text-xs">
                      {getStatusLabel(violation.status)}
                    </Badge>
                  </div>
                  <DialogTitle className="text-2xl font-bold">
                    {violation.rule_citation}
                  </DialogTitle>
                  <DialogDescription className="mt-1">
                    Comprehensive analysis of the compliance violation
                  </DialogDescription>
                </div>
              </div>
            </div>
          </DialogHeader>
        </div>

        <div className="px-8 py-6 space-y-8">
          {/* Key Info Cards */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="p-4 rounded-xl bg-muted/50 border">
              <div className="flex items-center gap-2 text-muted-foreground mb-2">
                <FileText className="h-4 w-4" />
                <span className="text-xs font-medium uppercase tracking-wide">Document</span>
              </div>
              <p className="font-semibold text-sm">{violation.source_document_name || "Unknown"}</p>
            </div>

            <div className="p-4 rounded-xl bg-muted/50 border">
              <div className="flex items-center gap-2 text-muted-foreground mb-2">
                <Calendar className="h-4 w-4" />
                <span className="text-xs font-medium uppercase tracking-wide">Detected</span>
              </div>
              <p className="font-semibold text-sm">{formatDate(violation.created_at)}</p>
            </div>

            {violation.confidence_score !== null && (
              <div className="p-4 rounded-xl bg-muted/50 border">
                <div className="flex items-center gap-2 text-muted-foreground mb-2">
                  <TrendingUp className="h-4 w-4" />
                  <span className="text-xs font-medium uppercase tracking-wide">Confidence</span>
                </div>
                <p className="font-semibold text-sm">{Math.round(violation.confidence_score * 100)}%</p>
              </div>
            )}
          </div>

          {/* Finding Summary */}
          {violation.finding_summary && (
            <div className="space-y-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Finding Summary</h3>
              <p className="text-base leading-relaxed p-4 rounded-xl bg-destructive/5 border border-destructive/10">
                {violation.finding_summary}
              </p>
            </div>
          )}

          {/* Gap Analysis */}
          {violation.evidence?.gap_analysis && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Shield className="h-5 w-5 text-destructive" />
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Gap Analysis</h3>
              </div>
              <div className="p-5 bg-gradient-to-br from-destructive/10 to-destructive/5 border-2 border-destructive/20 rounded-xl">
                <p className="text-sm leading-relaxed">{violation.evidence.gap_analysis}</p>
              </div>
            </div>
          )}

          {/* Evidence */}
          {violation.evidence && (
            <div className="space-y-6">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Evidence</h3>

              <div className="grid gap-6 md:grid-cols-2">
                {/* Framework Requirement */}
                {violation.evidence.target_quote && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-primary">
                      <Shield className="h-4 w-4" />
                      <span className="text-xs font-semibold uppercase tracking-wide">Framework Requirement</span>
                    </div>
                    <div className="p-5 rounded-xl bg-gradient-to-br from-primary/10 to-primary/5 border-l-4 border-primary">
                      <p className="text-sm leading-relaxed italic">
                        "{violation.evidence.target_quote}"
                      </p>
                      {violation.evidence.source_section && (
                        <p className="text-xs text-muted-foreground mt-3">
                          Section: {violation.evidence.source_section}
                        </p>
                      )}
                    </div>
                  </div>
                )}

                {/* Your Document Content */}
                {violation.evidence.source_quote && (
                  <div className="space-y-3">
                    <div className="flex items-center gap-2 text-destructive">
                      <FileText className="h-4 w-4" />
                      <span className="text-xs font-semibold uppercase tracking-wide">Your Document</span>
                    </div>
                    <div className="p-5 rounded-xl bg-gradient-to-br from-destructive/10 to-destructive/5 border-l-4 border-destructive">
                      <p className="text-sm leading-relaxed italic">
                        "{violation.evidence.source_quote}"
                      </p>
                      {violation.evidence.source_page && (
                        <p className="text-xs text-muted-foreground mt-3">
                          Page {violation.evidence.source_page}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Additional Metadata */}
          {(violation.assigned_to || violation.updated_at) && (
            <div className="grid gap-4 md:grid-cols-2">
              {violation.assigned_to && (
                <div className="p-4 rounded-xl bg-muted/50 border">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <User className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Assigned To</span>
                  </div>
                  <p className="font-semibold text-sm">{violation.assigned_to}</p>
                </div>
              )}

              {violation.updated_at && (
                <div className="p-4 rounded-xl bg-muted/50 border">
                  <div className="flex items-center gap-2 text-muted-foreground mb-2">
                    <Calendar className="h-4 w-4" />
                    <span className="text-xs font-medium uppercase tracking-wide">Last Updated</span>
                  </div>
                  <p className="font-semibold text-sm">{formatDate(violation.updated_at)}</p>
                </div>
              )}
            </div>
          )}

          {/* Recommendations */}
          {violation.recommendations && violation.recommendations.length > 0 && (
            <div className="space-y-4">
              <div className="flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-amber-600" />
                <h3 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">Recommendations</h3>
              </div>
              <div className="space-y-3">
                {violation.recommendations.map((rec, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-4 p-4 rounded-xl bg-amber-500/5 border border-amber-500/20"
                  >
                    <div className="h-7 w-7 shrink-0 flex items-center justify-center rounded-lg bg-amber-600/20 text-amber-700 text-sm font-bold">
                      {index + 1}
                    </div>
                    <p className="text-sm leading-relaxed pt-0.5">{rec}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
