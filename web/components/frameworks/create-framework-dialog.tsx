"use client";

import { useState } from "react";
import { Plus, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface CreateFrameworkDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (data: {
    name: string;
    framework_index_name: string;
    description?: string;
    version?: string;
    todos: string[];
  }) => void;
  isCreating?: boolean;
}

export function CreateFrameworkDialog({
  open,
  onOpenChange,
  onCreate,
  isCreating = false,
}: CreateFrameworkDialogProps) {
  const [name, setName] = useState("");
  const [frameworkIndexName, setFrameworkIndexName] = useState("");
  const [description, setDescription] = useState("");
  const [version, setVersion] = useState("");
  const [todos, setTodos] = useState<string[]>([""]);
  const [error, setError] = useState<string | null>(null);

  const addTodo = () => {
    setTodos([...todos, ""]);
  };

  const removeTodo = (index: number) => {
    if (todos.length > 1) {
      setTodos(todos.filter((_, i) => i !== index));
    }
  };

  const updateTodo = (index: number, value: string) => {
    const newTodos = [...todos];
    newTodos[index] = value;
    setTodos(newTodos);
  };

  const handleCreate = () => {
    setError(null);

    if (!name.trim()) {
      setError("Framework name is required");
      return;
    }

    if (!frameworkIndexName.trim()) {
      setError("Framework index name is required");
      return;
    }

    // Validate index name format (alphanumeric, underscores, lowercase)
    const indexNameRegex = /^[a-z0-9_]+$/;
    if (!indexNameRegex.test(frameworkIndexName.trim())) {
      setError("Index name must contain only lowercase letters, numbers, and underscores");
      return;
    }

    const filteredTodos = todos.filter((todo) => todo.trim() !== "");
    if (filteredTodos.length === 0) {
      setError("At least one compliance requirement is required");
      return;
    }

    onCreate({
      name: name.trim(),
      framework_index_name: frameworkIndexName.trim(),
      description: description.trim() || undefined,
      version: version.trim() || undefined,
      todos: filteredTodos,
    });
  };

  const handleClose = () => {
    if (!isCreating) {
      setName("");
      setFrameworkIndexName("");
      setDescription("");
      setVersion("");
      setTodos([""]);
      setError(null);
      onOpenChange(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Compliance Framework</DialogTitle>
          <DialogDescription>
            Define a new compliance framework with specific requirements
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Framework Name */}
          <div className="space-y-2">
            <Label htmlFor="name">
              Framework Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="name"
              placeholder="e.g., SOC 2 Type II, GDPR, HIPAA"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isCreating}
            />
            <p className="text-xs text-muted-foreground">
              A descriptive name for this compliance framework
            </p>
          </div>

          {/* Framework Index Name */}
          <div className="space-y-2">
            <Label htmlFor="indexName">
              Index Name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="indexName"
              placeholder="e.g., framework_soc2, framework_gdpr"
              value={frameworkIndexName}
              onChange={(e) => setFrameworkIndexName(e.target.value.toLowerCase())}
              disabled={isCreating}
            />
            <p className="text-xs text-muted-foreground">
              Milvus collection name for this framework's documents (lowercase, alphanumeric, underscores only)
            </p>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="description">Description (Optional)</Label>
            <Input
              id="description"
              placeholder="e.g., System and Organization Controls 2 Trust Service Criteria"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={isCreating}
            />
            <p className="text-xs text-muted-foreground">
              Detailed description of this framework
            </p>
          </div>

          {/* Version */}
          <div className="space-y-2">
            <Label htmlFor="version">Version (Optional)</Label>
            <Input
              id="version"
              placeholder="e.g., 2023.1, v1.0"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              disabled={isCreating}
            />
            <p className="text-xs text-muted-foreground">
              Framework version or revision number
            </p>
          </div>

          {/* Compliance Requirements */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>
                Compliance Requirements <span className="text-destructive">*</span>
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addTodo}
                disabled={isCreating}
                className="gap-2"
              >
                <Plus className="h-3 w-3" />
                Add Requirement
              </Button>
            </div>

            <div className="space-y-2">
              {todos.map((todo, index) => (
                <div key={index} className="flex items-center gap-2">
                  <Input
                    placeholder={`Requirement ${index + 1}`}
                    value={todo}
                    onChange={(e) => updateTodo(index, e.target.value)}
                    disabled={isCreating}
                  />
                  {todos.length > 1 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeTodo(index)}
                      disabled={isCreating}
                      className="shrink-0"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              List the key compliance requirements that documents must meet
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button
              variant="outline"
              onClick={handleClose}
              disabled={isCreating}
            >
              Cancel
            </Button>
            <Button onClick={handleCreate} disabled={isCreating}>
              {isCreating ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent mr-2" />
                  Creating...
                </>
              ) : (
                "Create Framework"
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
