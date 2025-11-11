"use client";

import { useState } from "react";
import { Plus, RefreshCw, Shield } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CreateFrameworkDialog } from "@/components/frameworks/create-framework-dialog";
import { FrameworksTable } from "@/components/frameworks/frameworks-table";
import { UploadDialog } from "@/components/documents/upload-dialog";
import {
  useFrameworks,
  useCreateFramework,
  useDeleteFramework,
} from "@/lib/hooks/use-frameworks";
import { useIngestDocuments } from "@/lib/hooks/use-documents";
import type { ComplianceFramework } from "@/lib/types/api";

export default function FrameworksPage() {
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [selectedFramework, setSelectedFramework] = useState<ComplianceFramework | null>(null);

  // Fetch frameworks
  const { data: frameworks, isLoading, error, refetch } = useFrameworks();

  // Mutations
  const createMutation = useCreateFramework();
  const deleteMutation = useDeleteFramework();
  const ingestMutation = useIngestDocuments();

  const handleCreate = async (data: {
    name: string;
    framework_index_name: string;
    description?: string;
    version?: string;
    todos: string[];
  }) => {
    try {
      await createMutation.mutateAsync({
        name: data.name,
        framework_index_name: data.framework_index_name,
        description: data.description || "",
        version: data.version || "",
        compliance_todos: data.todos,
      });
      setCreateDialogOpen(false);
    } catch (error) {
      console.error("Create failed:", error);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  const handleUploadDocuments = (framework: ComplianceFramework) => {
    setSelectedFramework(framework);
    setUploadDialogOpen(true);
  };

  const handleUpload = async (files: File[], indexName: string) => {
    try {
      await ingestMutation.mutateAsync({ files, indexName });
      setUploadDialogOpen(false);
      setSelectedFramework(null);
    } catch (error) {
      console.error("Upload failed:", error);
    }
  };

  // Calculate stats
  const totalFrameworks = frameworks?.items?.length || 0;
  const totalRequirements = frameworks?.items?.reduce(
    (sum, fw) => sum + fw.compliance_todos.length,
    0
  ) || 0;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Compliance Frameworks
          </h1>
          <p className="text-muted-foreground mt-1">
            Define and manage compliance frameworks for document validation
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
          <Button className="gap-2" onClick={() => setCreateDialogOpen(true)}>
            <Plus className="h-4 w-4" />
            Create Framework
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Frameworks
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <Shield className="h-8 w-8 text-primary" />
              <div>
                <div className="text-2xl font-bold">{totalFrameworks}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {totalFrameworks === 0
                    ? "No frameworks yet"
                    : "Active frameworks"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Requirements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRequirements}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Across all frameworks
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Error State */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 py-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">
                Failed to load frameworks
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

      {/* Frameworks Table */}
      {isLoading ? (
        <Card>
          <CardContent className="flex items-center justify-center py-16">
            <div className="flex flex-col items-center gap-3">
              <RefreshCw className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">
                Loading frameworks...
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <FrameworksTable
              frameworks={frameworks?.items || []}
              onDelete={handleDelete}
              onUploadDocuments={handleUploadDocuments}
              isDeleting={deleteMutation.isPending}
            />
          </CardContent>
        </Card>
      )}

      {/* Create Dialog */}
      <CreateFrameworkDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
        onCreate={handleCreate}
        isCreating={createMutation.isPending}
      />

      {/* Upload Dialog */}
      <UploadDialog
        open={uploadDialogOpen}
        onOpenChange={setUploadDialogOpen}
        onUpload={handleUpload}
        isUploading={ingestMutation.isPending}
        defaultIndexName={selectedFramework?.framework_index_name}
      />
    </div>
  );
}
