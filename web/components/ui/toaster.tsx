"use client";

import { Toaster as Sonner } from "sonner";

export function Toaster() {
  return (
    <Sonner
      position="top-right"
      toastOptions={{
        classNames: {
          toast: "bg-background border-border",
          title: "text-foreground",
          description: "text-muted-foreground",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-muted text-muted-foreground",
          error: "border-destructive/50 bg-destructive/10 text-destructive",
          success: "border-green-500/50 bg-green-500/10 text-green-700 dark:text-green-400",
          warning: "border-yellow-500/50 bg-yellow-500/10 text-yellow-700 dark:text-yellow-400",
          info: "border-blue-500/50 bg-blue-500/10 text-blue-700 dark:text-blue-400",
        },
      }}
    />
  );
}
