"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Play,
  Square,
  CheckCircle2,
  RotateCcw,
  Trash2,
  GitMerge,
  Loader2,
} from "lucide-react";
import {
  cn,
  Button,
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskActionsProps {
  task: Task;
  isStuck?: boolean;
  onStart?: () => void;
  onStop?: () => void;
  onRecover?: () => void;
  onMerge?: () => void;
  onDiscard?: () => void;
  onDelete?: () => void;
  isStarting?: boolean;
  isStopping?: boolean;
  isRecovering?: boolean;
  isMerging?: boolean;
  isDeleting?: boolean;
}

export function TaskActions({
  task,
  isStuck = false,
  onStart,
  onStop,
  onRecover,
  onMerge,
  onDiscard,
  onDelete,
  isStarting = false,
  isStopping = false,
  isRecovering = false,
  isMerging = false,
  isDeleting = false,
}: TaskActionsProps) {
  const { t } = useTranslation(["kanban", "common"]);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [showDiscardDialog, setShowDiscardDialog] = useState(false);

  const isRunning = task.status === "in_progress";
  const canStart =
    task.status === "backlog" ||
    task.status === "queue" ||
    task.status === "human_review" ||
    task.status === "error";
  const canStop = isRunning && !isStuck;
  const canMerge = task.status === "done" || task.status === "human_review";
  const isAnyLoading = isStarting || isStopping || isRecovering || isMerging || isDeleting;

  return (
    <>
      <div className="flex flex-wrap gap-2">
        {/* Start / Resume */}
        {canStart && onStart && (
          <Button
            onClick={onStart}
            disabled={isAnyLoading}
            size="sm"
            className="gap-1.5"
          >
            {isStarting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Play className="h-4 w-4" />
            )}
            {t("kanban:actions.start")}
          </Button>
        )}

        {/* Stop */}
        {canStop && onStop && (
          <Button
            onClick={onStop}
            disabled={isAnyLoading}
            variant="outline"
            size="sm"
            className="gap-1.5"
          >
            {isStopping ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Square className="h-4 w-4" />
            )}
            {t("kanban:actions.stop")}
          </Button>
        )}

        {/* Recover (stuck tasks) */}
        {isStuck && onRecover && (
          <Button
            onClick={onRecover}
            disabled={isAnyLoading}
            variant="outline"
            size="sm"
            className="gap-1.5"
          >
            {isRecovering ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RotateCcw className="h-4 w-4" />
            )}
            {t("kanban:actions.recover")}
          </Button>
        )}

        {/* Merge */}
        {canMerge && onMerge && (
          <Button
            onClick={onMerge}
            disabled={isAnyLoading}
            variant="outline"
            size="sm"
            className="gap-1.5"
          >
            {isMerging ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <GitMerge className="h-4 w-4" />
            )}
            {t("kanban:detail.merge", "Merge")}
          </Button>
        )}

        {/* Discard */}
        {onDiscard && (
          <Button
            onClick={() => setShowDiscardDialog(true)}
            disabled={isAnyLoading || isRunning}
            variant="outline"
            size="sm"
            className="gap-1.5 text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
            {t("kanban:detail.discard", "Discard")}
          </Button>
        )}

        {/* Delete */}
        {onDelete && (
          <Button
            onClick={() => setShowDeleteDialog(true)}
            disabled={isAnyLoading || isRunning}
            variant="ghost"
            size="sm"
            className="gap-1.5 text-destructive hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
            {t("common:buttons.delete")}
          </Button>
        )}
      </div>

      {/* Delete confirmation */}
      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("kanban:detail.deleteTitle", "Delete Task")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                "kanban:detail.deleteDescription",
                "This will permanently delete this task and its worktree. This action cannot be undone.",
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:buttons.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                onDelete?.();
                setShowDeleteDialog(false);
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isDeleting ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : null}
              {t("common:buttons.delete")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Discard confirmation */}
      <AlertDialog open={showDiscardDialog} onOpenChange={setShowDiscardDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t("kanban:detail.discardTitle", "Discard Changes")}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t(
                "kanban:detail.discardDescription",
                "This will discard all changes made by this task. This action cannot be undone.",
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t("common:buttons.cancel")}</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                onDiscard?.();
                setShowDiscardDialog(false);
              }}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t("kanban:detail.discard", "Discard")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
