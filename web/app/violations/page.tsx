"use client";

import { useState } from "react";
import { RefreshCw, AlertTriangle, Filter, Shield, CheckCircle2, Clock } from "lucide-react";
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
  const highCount =
    violations?.items?.filter((v) => v.severity === "high").length || 0;
  const openCount =
    violations?.items?.filter((v) => v.status === "open").length || 0;
  const remediatedCount =
    violations?.items?.filter((v) => v.status === "remediated").length || 0;

  const severityOptions = ["critical", "high", "medium", "low"];
  const statusOptions = [
    "open",
    "assigned",
    "in_progress",
    "remediated",
    "false_positive",
  ];

  return (
    <div className="space-y-6 pb-8">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold tracking-tight bg-gradient-to-r from-red-600 to-orange-600 bg-clip-text text-transparent">
            Compliance Violations
          </h1>
          <p className="text-muted-foreground mt-2 text-base">
            Monitor and manage compliance gaps across your documentation
          </p>
        </div>
        <Button
          variant="outline"
          size="default"
          onClick={() => refetch()}
          disabled={isLoading}
          className="gap-2"
        >
          <RefreshCw
            className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
          />
          Refresh
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card className="relative overflow-hidden border-none bg-gradient-to-br from-red-500/10 via-red-500/5 to-transparent">
          <div className="absolute top-0 right-0 w-32 h-32 bg-red-500/10 rounded-full blur-3xl -mr-16 -mt-16" />
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Total Violations
                </p>
                <div className="text-4xl font-bold tracking-tight">
                  {totalViolations}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {totalViolations === 0 ? "All clear" : "Compliance gaps found"}
                </p>
              </div>
              <div className="h-14 w-14 rounded-2xl bg-red-500/20 flex items-center justify-center">
                <AlertTriangle className="h-7 w-7 text-red-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-none bg-gradient-to-br from-orange-500/10 via-orange-500/5 to-transparent">
          <div className="absolute top-0 right-0 w-32 h-32 bg-orange-500/10 rounded-full blur-3xl -mr-16 -mt-16" />
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Critical & High
                </p>
                <div className="text-4xl font-bold tracking-tight">
                  {criticalCount + highCount}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Require immediate attention
                </p>
              </div>
              <div className="h-14 w-14 rounded-2xl bg-orange-500/20 flex items-center justify-center">
                <Shield className="h-7 w-7 text-orange-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-none bg-gradient-to-br from-yellow-500/10 via-yellow-500/5 to-transparent">
          <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/10 rounded-full blur-3xl -mr-16 -mt-16" />
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Open Issues
                </p>
                <div className="text-4xl font-bold tracking-tight">
                  {openCount}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Awaiting action
                </p>
              </div>
              <div className="h-14 w-14 rounded-2xl bg-yellow-500/20 flex items-center justify-center">
                <Clock className="h-7 w-7 text-yellow-600" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden border-none bg-gradient-to-br from-green-500/10 via-green-500/5 to-transparent">
          <div className="absolute top-0 right-0 w-32 h-32 bg-green-500/10 rounded-full blur-3xl -mr-16 -mt-16" />
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground mb-2">
                  Remediated
                </p>
                <div className="text-4xl font-bold tracking-tight">
                  {remediatedCount}
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  Successfully resolved
                </p>
              </div>
              <div className="h-14 w-14 rounded-2xl bg-green-500/20 flex items-center justify-center">
                <CheckCircle2 className="h-7 w-7 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card className="border-none shadow-sm">
        <CardContent className="p-6">
          <div className="space-y-5">
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 min-w-[100px]">
                <Filter className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-semibold">Severity</span>
              </div>
              <div className="flex-1 flex items-center gap-2 flex-wrap">
                <Button
                  variant={severityFilter === null ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setSeverityFilter(null)}
                  className="rounded-full"
                >
                  All
                </Button>
                {severityOptions.map((severity) => (
                  <Button
                    key={severity}
                    variant={severityFilter === severity ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setSeverityFilter(severity)}
                    className="rounded-full capitalize"
                  >
                    {severity}
                  </Button>
                ))}
              </div>
            </div>

            <div className="h-px bg-border" />

            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 min-w-[100px]">
                <div className="w-4" />
                <span className="text-sm font-semibold">Status</span>
              </div>
              <div className="flex-1 flex items-center gap-2 flex-wrap">
                <Button
                  variant={statusFilter === null ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setStatusFilter(null)}
                  className="rounded-full"
                >
                  All
                </Button>
                {statusOptions.map((status) => (
                  <Button
                    key={status}
                    variant={statusFilter === status ? "default" : "ghost"}
                    size="sm"
                    onClick={() => setStatusFilter(status)}
                    className="rounded-full capitalize"
                  >
                    {status.replace("_", " ")}
                  </Button>
                ))}
              </div>
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
        <Card className="border-none shadow-sm">
          <CardContent className="flex items-center justify-center py-24">
            <div className="flex flex-col items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              </div>
              <div className="text-center">
                <p className="text-base font-medium">Loading violations...</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Fetching compliance data
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div>
          <ViolationsTable
            violations={violations?.items || []}
            onView={handleViewDetails}
            onAcknowledge={handleAcknowledge}
            isUpdating={acknowledgeMutation.isPending}
          />
        </div>
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
