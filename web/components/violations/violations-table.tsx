"use client";

import { useState } from "react";
import { AlertTriangle, Eye, Check, MoreVertical, FileText, Calendar, TrendingUp } from "lucide-react";
import { Card } from "@/components/ui/card";
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

function getSeverityConfig(severity: string) {
  switch (severity) {
    case "critical":
      return {
        variant: "critical" as const,
        bg: "bg-red-500/10",
        border: "border-red-500/20",
        icon: "text-red-600",
      };
    case "high":
      return {
        variant: "high" as const,
        bg: "bg-orange-500/10",
        border: "border-orange-500/20",
        icon: "text-orange-600",
      };
    case "medium":
      return {
        variant: "medium" as const,
        bg: "bg-yellow-500/10",
        border: "border-yellow-500/20",
        icon: "text-yellow-600",
      };
    case "low":
      return {
        variant: "low" as const,
        bg: "bg-blue-500/10",
        border: "border-blue-500/20",
        icon: "text-blue-600",
      };
    default:
      return {
        variant: "low" as const,
        bg: "bg-gray-500/10",
        border: "border-gray-500/20",
        icon: "text-gray-600",
      };
  }
}

function getStatusConfig(status: string) {
  switch (status) {
    case "open":
      return {
        variant: "destructive" as const,
        label: "Open",
      };
    case "assigned":
      return {
        variant: "warning" as const,
        label: "Assigned",
      };
    case "in_progress":
      return {
        variant: "info" as const,
        label: "In Progress",
      };
    case "remediated":
      return {
        variant: "success" as const,
        label: "Remediated",
      };
    case "false_positive":
      return {
        variant: "secondary" as const,
        label: "False Positive",
      };
    default:
      return {
        variant: "default" as const,
        label: status,
      };
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
      <Card className="border-none shadow-sm">
        <div className="flex flex-col items-center justify-center py-24 text-center">
          <div className="h-24 w-24 rounded-full bg-gradient-to-br from-green-500/20 to-emerald-500/20 flex items-center justify-center mb-6">
            <Check className="h-12 w-12 text-green-600" />
          </div>
          <h3 className="text-xl font-semibold mb-2">No violations found</h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            All compliance checks passed successfully. Your documents are fully compliant.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {violations.map((violation) => {
        const severityConfig = getSeverityConfig(violation.severity);
        const statusConfig = getStatusConfig(violation.status);

        return (
          <Card
            key={violation.id}
            className={`group relative overflow-hidden border-l-4 ${severityConfig.border} hover:shadow-lg transition-all duration-200 cursor-pointer`}
            onClick={() => onView && onView(violation)}
          >
            <div className="p-6">
              <div className="flex items-start justify-between gap-6">
                {/* Left Content */}
                <div className="flex-1 min-w-0 space-y-4">
                  {/* Header */}
                  <div className="flex items-start gap-4">
                    <div className={`h-12 w-12 rounded-xl ${severityConfig.bg} flex items-center justify-center shrink-0`}>
                      <AlertTriangle className={`h-6 w-6 ${severityConfig.icon}`} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant={severityConfig.variant} className="text-xs font-semibold">
                          {violation.severity.toUpperCase()}
                        </Badge>
                        <Badge variant={statusConfig.variant} className="text-xs">
                          {statusConfig.label}
                        </Badge>
                        {violation.confidence_score !== null && (
                          <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <TrendingUp className="h-3 w-3" />
                            <span>{Math.round(violation.confidence_score * 100)}% confidence</span>
                          </div>
                        )}
                      </div>
                      <h3 className="text-lg font-semibold leading-tight mb-2">
                        {violation.rule_citation}
                      </h3>
                      {violation.finding_summary && (
                        <p className="text-sm text-muted-foreground line-clamp-2">
                          {violation.finding_summary}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Metadata */}
                  <div className="flex items-center gap-6 text-sm text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4" />
                      <span className="truncate max-w-[200px]">
                        {violation.source_document_name || "Unknown document"}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Calendar className="h-4 w-4" />
                      <span>{formatDate(violation.created_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Right Actions */}
                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      onView && onView(violation);
                    }}
                    className="gap-2 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Eye className="h-4 w-4" />
                    View Details
                  </Button>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          onView && onView(violation);
                        }}
                        className="gap-2"
                      >
                        <Eye className="h-4 w-4" />
                        View Details
                      </DropdownMenuItem>
                      {violation.status === "open" && (
                        <DropdownMenuItem
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAcknowledge(violation.id);
                          }}
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
                </div>
              </div>
            </div>

            {/* Hover indicator */}
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-gradient-to-r from-primary/0 via-primary/50 to-primary/0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </Card>
        );
      })}
    </div>
  );
}
