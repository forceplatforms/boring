"use client";

import { useState } from "react";
import { RefreshCw, AlertTriangle, Filter } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ViolationsTable } from "@/components/violations/violations-table";
import { ViolationDetailDialog } from "@/components/violations/violation-detail-dialog";
import {
  useViolations,
  useViolationStats,
  useAcknowledgeViolation,
} from "@/lib/hooks/use-violations";
import type { Violation } from "@/lib/types/api";

export default function ViolationsPage() {
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(
    null
  );
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [severityFilter, setSeverityFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);

  // Fetch violations with filters
  const {
    data: violations,
    isLoading,
    error,
    refetch,
  } = useViolations({
    severity: severityFilter || undefined,
    status: statusFilter || undefined,
  });

  // Fetch stats
  const { data: stats } = useViolationStats();

  // Mutations
  const acknowledgeMutation = useAcknowledgeViolation();

  const handleViewDetails = (violation: Violation) => {
    setSelectedViolation(violation);
    setDetailDialogOpen(true);
  };

  const handleAcknowledge = async (id: string) => {
    try {
      await acknowledgeMutation.mutateAsync(id);
    } catch (error) {
      console.error("Acknowledge failed:", error);
    }
  };

  // Calculate stats
  const totalViolations = violations?.items?.length || 0;
  const criticalCount =
    violations?.items?.filter((v) => v.severity === "critical").length || 0;
  const openCount =
    violations?.items?.filter((v) => v.status === "open").length || 0;

  const severityOptions = ["critical", "high", "medium", "low"];
  const statusOptions = [
    "open",
    "assigned",
    "in_progress",
    "remediated",
    "false_positive",
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Violations</h1>
          <p className="text-muted-foreground mt-1">
            Review and manage compliance violations found in documents
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={() => refetch()}
            disabled={isLoading}
          >
            <RefreshCw
              className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
            />
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Violations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-8 w-8 text-destructive" />
              <div>
                <div className="text-2xl font-bold">{totalViolations}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {totalViolations === 0 ? "No violations" : "Found"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Critical Issues
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{criticalCount}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Require immediate attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Open
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{openCount}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Awaiting action
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <div className="flex-1 flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">Severity:</span>
              <Button
                variant={severityFilter === null ? "default" : "outline"}
                size="sm"
                onClick={() => setSeverityFilter(null)}
              >
                All
              </Button>
              {severityOptions.map((severity) => (
                <Button
                  key={severity}
                  variant={severityFilter === severity ? "default" : "outline"}
                  size="sm"
                  onClick={() => setSeverityFilter(severity)}
                >
                  {severity}
                </Button>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-4 mt-3">
            <div className="w-4" />
            <div className="flex-1 flex items-center gap-2 flex-wrap">
              <span className="text-sm font-medium">Status:</span>
              <Button
                variant={statusFilter === null ? "default" : "outline"}
                size="sm"
                onClick={() => setStatusFilter(null)}
              >
                All
              </Button>
              {statusOptions.map((status) => (
                <Button
                  key={status}
                  variant={statusFilter === status ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter(status)}
                  className="capitalize"
                >
                  {status.replace("_", " ")}
                </Button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">
                Failed to load violations
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

      {/* Violations Table */}
      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Loading violations...
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <ViolationsTable
              violations={violations?.items || []}
              onView={handleViewDetails}
              onAcknowledge={handleAcknowledge}
              isUpdating={acknowledgeMutation.isPending}
            />
          </CardContent>
        </Card>
      )}

      {/* Detail Dialog */}
      <ViolationDetailDialog
        violation={selectedViolation}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
      />
    </div>
  );
}
