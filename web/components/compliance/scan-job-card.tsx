"use client";

import { Clock, CheckCircle2, XCircle, Loader2, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatDate } from "@/lib/utils";
import type { ScanJob } from "@/lib/types/api";

interface ScanJobCardProps {
  job: ScanJob;
  onClick?: () => void;
}

function getStatusIcon(status: string) {
  switch (status) {
    case "completed":
      return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-destructive" />;
    case "running":
      return <Loader2 className="h-5 w-5 text-primary animate-spin" />;
    case "pending":
      return <Clock className="h-5 w-5 text-muted-foreground" />;
    default:
      return <Clock className="h-5 w-5 text-muted-foreground" />;
  }
}

function getStatusVariant(status: string) {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "destructive";
    case "running":
      return "default";
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
    case "failed":
      return "Failed";
    case "running":
      return "Running";
    case "pending":
      return "Pending";
    default:
      return status;
  }
}

export function ScanJobCard({ job, onClick }: ScanJobCardProps) {
  const violationsCount = job.violations_count || 0;
  const hasViolations = violationsCount > 0;

  return (
    <Card
      className={`transition-all hover:border-primary/50 ${
        onClick ? "cursor-pointer" : ""
      }`}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          {/* Status Icon */}
          <div className="shrink-0 mt-1">{getStatusIcon(job.status)}</div>

          {/* Content */}
          <div className="flex-1 min-w-0 space-y-3">
            {/* Header */}
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant={getStatusVariant(job.status)}>
                    {getStatusLabel(job.status)}
                  </Badge>
                  {job.status === "completed" && hasViolations && (
                    <Badge variant="warning" className="gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      {violationsCount} {violationsCount === 1 ? "Issue" : "Issues"}
                    </Badge>
                  )}
                </div>
                <p className="text-sm font-medium truncate">
                  Framework: {job.framework_name || job.framework_id}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Index: <code className="font-mono">{job.document_index_name}</code>
                </p>
              </div>
            </div>

            {/* Progress/Results */}
            {job.status === "running" && job.progress !== undefined && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{Math.round(job.progress * 100)}%</span>
                </div>
                <div className="h-1.5 bg-background-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full bg-primary transition-all duration-300"
                    style={{ width: `${job.progress * 100}%` }}
                  />
                </div>
              </div>
            )}

            {job.status === "failed" && job.error_message && (
              <div className="text-xs text-destructive bg-destructive/10 rounded px-2 py-1">
                {job.error_message}
              </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <span>Started {formatDate(job.created_at)}</span>
              {job.completed_at && (
                <span>Completed {formatDate(job.completed_at)}</span>
              )}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
