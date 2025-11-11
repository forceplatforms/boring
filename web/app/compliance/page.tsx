"use client";

import { useState } from "react";
import { Play, RefreshCw, CheckCircle2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TriggerScanDialog } from "@/components/compliance/trigger-scan-dialog";
import { ScanJobCard } from "@/components/compliance/scan-job-card";
import {
  useComplianceJobs,
  useComplianceCheck,
} from "@/lib/hooks/use-compliance";
import { useRouter } from "next/navigation";

export default function CompliancePage() {
  const [triggerDialogOpen, setTriggerDialogOpen] = useState(false);
  const router = useRouter();

  // Fetch compliance jobs
  const { data: jobs, isLoading, error, refetch } = useComplianceJobs();

  // Mutations
  const checkMutation = useComplianceCheck();

  const handleTriggerScan = async (data: {
    frameworkId: string;
    documentIndexName: string;
  }) => {
    try {
      await checkMutation.mutateAsync({
        framework_id: data.frameworkId,
        document_index_name: data.documentIndexName,
      });
      setTriggerDialogOpen(false);
    } catch (error) {
      console.error("Scan trigger failed:", error);
    }
  };

  // Calculate stats
  const totalScans = jobs?.items?.length || 0;
  const completedScans =
    jobs?.items?.filter((job) => job.status === "completed").length || 0;
  const runningScans =
    jobs?.items?.filter((job) => job.status === "running").length || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Compliance Scans
          </h1>
          <p className="text-muted-foreground mt-1">
            Trigger and monitor compliance checks for your documents
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
          <Button className="gap-2" onClick={() => setTriggerDialogOpen(true)}>
            <Play className="h-4 w-4" />
            Trigger Scan
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Scans
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalScans}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {totalScans === 0 ? "No scans yet" : "All time"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Running
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{runningScans}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Active scans
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Completed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-8 w-8 text-green-500" />
              <div>
                <div className="text-2xl font-bold">{completedScans}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  Successfully finished
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">
                Failed to load scans
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

      {/* Scan Jobs List */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Recent Scans</h2>
        {isLoading ? (
          <Card>
            <CardContent className="flex items-center justify-center py-16">
              <div className="flex flex-col items-center gap-3">
                <RefreshCw className="h-8 w-8 animate-spin text-primary" />
                <p className="text-sm text-muted-foreground">
                  Loading scans...
                </p>
              </div>
            </CardContent>
          </Card>
        ) : jobs?.items && jobs.items.length > 0 ? (
          <div className="space-y-3">
            {jobs.items.map((job) => (
              <ScanJobCard
                key={job.id}
                job={job}
                onClick={() => {
                  if (job.status === "completed") {
                    router.push(`/violations?scan_id=${job.id}`);
                  }
                }}
              />
            ))}
          </div>
        ) : (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-16">
              <div className="flex h-20 w-20 items-center justify-center rounded-full bg-primary/10 mb-4">
                <Play className="h-10 w-10 text-primary" />
              </div>
              <h3 className="text-lg font-semibold mb-2">No scans yet</h3>
              <p className="text-sm text-muted-foreground max-w-sm text-center mb-6">
                Trigger your first compliance scan to check documents against a
                framework
              </p>
              <Button className="gap-2" onClick={() => setTriggerDialogOpen(true)}>
                <Play className="h-4 w-4" />
                Trigger Your First Scan
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Trigger Dialog */}
      <TriggerScanDialog
        open={triggerDialogOpen}
        onOpenChange={setTriggerDialogOpen}
        onTrigger={handleTriggerScan}
        isTriggering={checkMutation.isPending}
      />
    </div>
  );
}
