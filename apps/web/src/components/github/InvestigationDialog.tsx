"use client";

import { useCallback } from "react";
import { Sparkles, Loader2, CheckCircle2, AlertCircle, X } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Progress,
} from "@auto-claude/ui";
import type {
  GitHubIssue,
  GitHubInvestigationStatus,
  GitHubInvestigationResult,
} from "@auto-claude/types";

interface InvestigationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  issue: GitHubIssue | null;
  status: GitHubInvestigationStatus;
  result: GitHubInvestigationResult | null;
  onStartInvestigation: (selectedCommentIds: number[]) => void;
  onClose: () => void;
}

export function InvestigationDialog({
  open,
  onOpenChange,
  issue,
  status,
  result,
  onStartInvestigation,
  onClose,
}: InvestigationDialogProps) {
  const handleStart = useCallback(() => {
    onStartInvestigation([]);
  }, [onStartInvestigation]);

  const isInProgress =
    status.phase === "fetching" ||
    status.phase === "analyzing" ||
    status.phase === "creating_task";
  const isComplete = status.phase === "complete";
  const isError = status.phase === "error";
  const isIdle = status.phase === "idle";

  if (!issue) return null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-yellow-500" />
            AI Investigation
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Issue info */}
          <div className="rounded-md border border-border bg-secondary/30 p-3">
            <p className="text-sm font-medium">
              #{issue.number} {issue.title}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {issue.author.login} · {new Date(issue.createdAt).toLocaleDateString()}
            </p>
          </div>

          {/* Idle state - start button */}
          {isIdle && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                AI will analyze this issue, explore the codebase, and provide a
                detailed investigation with proposed solutions and affected files.
              </p>
              <button
                onClick={handleStart}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2.5 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
              >
                <Sparkles className="h-4 w-4" />
                Start Investigation
              </button>
            </div>
          )}

          {/* Progress state */}
          {isInProgress && (
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <span className="text-sm font-medium">{status.message}</span>
              </div>
              <Progress value={status.progress} className="h-2" />
              <p className="text-xs text-muted-foreground">
                Phase: {status.phase}
              </p>
            </div>
          )}

          {/* Complete state */}
          {isComplete && result && result.success && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-sm font-medium">Investigation Complete</span>
              </div>
              <div className="space-y-2 rounded-md border border-border p-3 text-sm">
                <div>
                  <span className="font-medium">Summary:</span>
                  <p className="mt-1 text-muted-foreground">
                    {result.analysis.summary}
                  </p>
                </div>
                <div>
                  <span className="font-medium">Proposed Solution:</span>
                  <p className="mt-1 text-muted-foreground">
                    {result.analysis.proposedSolution}
                  </p>
                </div>
                {result.analysis.affectedFiles.length > 0 && (
                  <div>
                    <span className="font-medium">Affected Files:</span>
                    <ul className="mt-1 list-inside list-disc text-xs font-mono text-muted-foreground">
                      {result.analysis.affectedFiles.map((file) => (
                        <li key={file}>{file}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  <span className="font-medium">Complexity: </span>
                  <span className="capitalize">
                    {result.analysis.estimatedComplexity}
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground transition-colors hover:bg-primary/90"
              >
                Done
              </button>
            </div>
          )}

          {/* Error state */}
          {isError && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm font-medium">Investigation Failed</span>
              </div>
              <p className="text-sm text-muted-foreground">
                {status.message || status.error}
              </p>
              <div className="flex gap-2">
                <button
                  onClick={handleStart}
                  className="flex-1 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground transition-colors hover:bg-primary/90"
                >
                  Retry
                </button>
                <button
                  onClick={onClose}
                  className="flex-1 rounded-md border border-border px-4 py-2 text-sm transition-colors hover:bg-accent"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
