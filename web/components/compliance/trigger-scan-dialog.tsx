"use client";

import { useState, useEffect } from "react";
import { Play, AlertCircle } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useFrameworks } from "@/lib/hooks/use-frameworks";
import { useUniqueIndexes } from "@/lib/hooks/use-documents";

interface TriggerScanDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onTrigger: (data: { frameworkId: string; documentIndexName: string }) => void;
  isTriggering?: boolean;
}

export function TriggerScanDialog({
  open,
  onOpenChange,
  onTrigger,
  isTriggering = false,
}: TriggerScanDialogProps) {
  const [selectedFramework, setSelectedFramework] = useState<string>("");
  const [indexName, setIndexName] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Fetch frameworks and indexes
  const { data: frameworks } = useFrameworks();
  const { data: indexes, isLoading: indexesLoading } = useUniqueIndexes();

  useEffect(() => {
    if (open) {
      // Auto-select first framework if only one exists
      if (frameworks?.items?.length === 1) {
        setSelectedFramework(frameworks.items[0].id);
      }
    }
  }, [open, frameworks]);

  const handleTrigger = () => {
    setError(null);

    if (!selectedFramework) {
      setError("Please select a compliance framework");
      return;
    }

    if (!indexName.trim()) {
      setError("Please select a Milvus index/collection name");
      return;
    }

    onTrigger({
      frameworkId: selectedFramework,
      documentIndexName: indexName.trim(),
    });
  };

  const handleClose = () => {
    if (!isTriggering) {
      setSelectedFramework("");
      setIndexName("");
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Trigger Compliance Scan</DialogTitle>
          <DialogDescription>
            Check documents against a compliance framework
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Framework Selection */}
          <div className="space-y-2">
            <Label>Compliance Framework</Label>
            <div className="space-y-2">
              {frameworks?.items?.map((framework) => (
                <button
                  key={framework.id}
                  type="button"
                  onClick={() => setSelectedFramework(framework.id)}
                  disabled={isTriggering}
                  className={`w-full rounded-lg border p-3 text-left transition-colors ${
                    selectedFramework === framework.id
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  } ${isTriggering ? "opacity-50 cursor-not-allowed" : ""}`}
                >
                  <div className="font-medium text-sm">{framework.name}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {framework.compliance_todos.length} requirements
                  </div>
                </button>
              ))}
              {frameworks?.items?.length === 0 && (
                <div className="text-sm text-muted-foreground text-center py-4">
                  No frameworks available. Create one first.
                </div>
              )}
            </div>
          </div>

          {/* Milvus Index Name Selection */}
          <div className="space-y-2">
            <Label htmlFor="indexName">Milvus Index/Collection Name</Label>
            <Select
              value={indexName}
              onValueChange={setIndexName}
              disabled={isTriggering || indexesLoading}
            >
              <SelectTrigger id="indexName">
                <SelectValue placeholder={indexesLoading ? "Loading indexes..." : "Select an index"} />
              </SelectTrigger>
              <SelectContent>
                {indexes && indexes.length > 0 ? (
                  indexes.map((index) => (
                    <SelectItem key={index} value={index}>
                      {index}
                    </SelectItem>
                  ))
                ) : (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">
                    No indexes available. Upload documents first.
                  </div>
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Select the Milvus collection containing your documents to scan
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isTriggering}
            >
              Cancel
            </Button>
            <Button onClick={handleTrigger} disabled={isTriggering}>
              {isTriggering ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
                  Starting Scan...
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 mr-2" />
                  Start Scan
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
