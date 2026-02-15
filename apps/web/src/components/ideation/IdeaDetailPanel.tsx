"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  X,
  Play,
  Trash2,
  ExternalLink,
  Code,
  Palette,
  FileText,
  Shield,
  Zap,
  Bug,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Idea, IdeationType } from "@/stores/ideation-store";

const TYPE_LABELS: Record<IdeationType, string> = {
  code_improvements: "Code Improvements",
  ui_ux_improvements: "UI/UX Improvements",
  documentation_gaps: "Documentation Gaps",
  security_hardening: "Security Hardening",
  performance_optimizations: "Performance Optimizations",
  code_quality: "Code Quality",
};

const TYPE_ICONS: Record<IdeationType, React.ComponentType<{ className?: string }>> = {
  code_improvements: Code,
  ui_ux_improvements: Palette,
  documentation_gaps: FileText,
  security_hardening: Shield,
  performance_optimizations: Zap,
  code_quality: Bug,
};

interface IdeaDetailPanelProps {
  idea: Idea;
  onClose: () => void;
  onConvert: (idea: Idea) => void;
  onDismiss: (idea: Idea) => void;
  onDelete: (ideaId: string) => void;
  onGoToTask?: (taskId: string) => void;
}

export function IdeaDetailPanel({
  idea,
  onClose,
  onConvert,
  onDismiss,
  onDelete,
  onGoToTask,
}: IdeaDetailPanelProps) {
  const { t } = useTranslation("views");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const Icon = TYPE_ICONS[idea.type];

  const isDismissed = idea.status === "dismissed";
  const isArchived = idea.status === "archived";
  const isConverted = idea.status === "converted";
  const isInactive = isDismissed || isArchived;

  const handleDelete = () => {
    onDelete(idea.id);
    onClose();
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-96 border-l border-border bg-card shadow-xl flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border p-4">
        <h2 className="text-sm font-semibold">
          {t("ideation.detail.title")}
        </h2>
        <div className="flex items-center gap-1">
          <button
            className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors"
            onClick={() => setShowDeleteConfirm(true)}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
          <button
            className="flex h-7 w-7 items-center justify-center rounded-md hover:bg-accent transition-colors"
            onClick={onClose}
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Type badge */}
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary">
            <Icon className="h-3.5 w-3.5" />
            {TYPE_LABELS[idea.type]}
          </span>
          <span
            className={cn(
              "rounded-full px-2 py-0.5 text-[11px] font-medium capitalize",
              idea.status === "new" && "bg-blue-500/10 text-blue-600",
              idea.status === "reviewed" && "bg-green-500/10 text-green-600",
              idea.status === "converted" && "bg-purple-500/10 text-purple-600",
              idea.status === "dismissed" && "bg-secondary text-muted-foreground",
              idea.status === "archived" && "bg-secondary text-muted-foreground",
            )}
          >
            {idea.status}
          </span>
        </div>

        {/* Title and description */}
        <div>
          <h3 className="text-lg font-semibold">{idea.title}</h3>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            {idea.description}
          </p>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-3">
          {idea.impact && (
            <div className="rounded-md border border-border p-3">
              <p className="text-xs text-muted-foreground">
                {t("ideation.detail.impact")}
              </p>
              <p className="text-sm font-medium capitalize">{idea.impact}</p>
            </div>
          )}
          {idea.effort && (
            <div className="rounded-md border border-border p-3">
              <p className="text-xs text-muted-foreground">
                {t("ideation.detail.effort")}
              </p>
              <p className="text-sm font-medium capitalize">{idea.effort}</p>
            </div>
          )}
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">
              {t("ideation.detail.priority")}
            </p>
            <p className="text-sm font-medium">{idea.priority}</p>
          </div>
        </div>

        {/* Linked task */}
        {idea.taskId && onGoToTask && (
          <div className="rounded-md border border-border p-3">
            <p className="text-xs text-muted-foreground">
              {t("ideation.detail.linkedTask")}
            </p>
            <button
              className="mt-1 flex items-center gap-1.5 text-sm text-primary hover:underline"
              onClick={() => onGoToTask(idea.taskId!)}
            >
              <ExternalLink className="h-3 w-3" />
              {idea.taskId}
            </button>
          </div>
        )}
      </div>

      {/* Actions */}
      {!isInactive && !isConverted && (
        <div className="shrink-0 border-t border-border p-4 space-y-2">
          <button
            className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={() => onConvert(idea)}
          >
            <Play className="h-4 w-4" />
            {t("ideation.convertToTask")}
          </button>
          {idea.status !== "dismissed" && (
            <button
              className="w-full flex items-center justify-center gap-2 rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-accent transition-colors"
              onClick={() => onDismiss(idea)}
            >
              <X className="h-4 w-4" />
              {t("ideation.dismiss")}
            </button>
          )}
        </div>
      )}

      {(isArchived || isConverted) && idea.taskId && onGoToTask && (
        <div className="shrink-0 border-t border-border p-4">
          <button
            className="w-full flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors"
            onClick={() => onGoToTask(idea.taskId!)}
          >
            <ExternalLink className="h-4 w-4" />
            {t("ideation.goToTask")}
          </button>
        </div>
      )}

      {/* Delete confirmation overlay */}
      {showDeleteConfirm && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/95 p-6">
          <div className="text-center space-y-4">
            <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-500/10">
              <Trash2 className="h-6 w-6 text-red-500" />
            </div>
            <div>
              <h3 className="font-semibold">
                {t("ideation.detail.deleteConfirmTitle")}
              </h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {t("ideation.detail.deleteConfirmDescription")}
              </p>
            </div>
            <div className="flex justify-center gap-2">
              <button
                className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent transition-colors"
                onClick={() => setShowDeleteConfirm(false)}
              >
                {t("ideation.detail.cancel")}
              </button>
              <button
                className="rounded-md bg-red-500 px-4 py-2 text-sm text-white hover:bg-red-600 transition-colors"
                onClick={handleDelete}
              >
                {t("ideation.detail.delete")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
