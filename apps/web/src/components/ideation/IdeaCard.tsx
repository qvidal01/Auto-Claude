"use client";

import { useTranslation } from "react-i18next";
import {
  Code,
  Palette,
  FileText,
  Shield,
  Zap,
  Bug,
  Play,
  X,
  ExternalLink,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { Idea, IdeationType } from "@/stores/ideation-store";

const TYPE_ICONS: Record<IdeationType, React.ComponentType<{ className?: string }>> = {
  code_improvements: Code,
  ui_ux_improvements: Palette,
  documentation_gaps: FileText,
  security_hardening: Shield,
  performance_optimizations: Zap,
  code_quality: Bug,
};

const TYPE_LABELS: Record<IdeationType, string> = {
  code_improvements: "Code",
  ui_ux_improvements: "UI/UX",
  documentation_gaps: "Docs",
  security_hardening: "Security",
  performance_optimizations: "Performance",
  code_quality: "Quality",
};

const TYPE_COLORS: Record<IdeationType, string> = {
  code_improvements: "bg-blue-500/10 text-blue-600",
  ui_ux_improvements: "bg-purple-500/10 text-purple-600",
  documentation_gaps: "bg-amber-500/10 text-amber-600",
  security_hardening: "bg-red-500/10 text-red-600",
  performance_optimizations: "bg-green-500/10 text-green-600",
  code_quality: "bg-orange-500/10 text-orange-600",
};

interface IdeaCardProps {
  idea: Idea;
  isSelected: boolean;
  onClick: () => void;
  onConvert: (idea: Idea) => void;
  onDismiss: (idea: Idea) => void;
  onGoToTask?: (taskId: string) => void;
}

export function IdeaCard({
  idea,
  isSelected,
  onClick,
  onConvert,
  onDismiss,
  onGoToTask,
}: IdeaCardProps) {
  const { t } = useTranslation("views");
  const isDismissed = idea.status === "dismissed";
  const isArchived = idea.status === "archived";
  const isConverted = idea.status === "converted";
  const isInactive = isDismissed || isArchived;
  const Icon = TYPE_ICONS[idea.type];

  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card p-4 cursor-pointer transition-colors hover:bg-accent/50",
        isInactive && "opacity-50",
        isSelected && "ring-2 ring-primary bg-primary/5",
      )}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          {/* Type badge */}
          <div className="mb-2 flex items-center gap-2">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-medium",
                TYPE_COLORS[idea.type],
              )}
            >
              <Icon className="h-3 w-3" />
              {TYPE_LABELS[idea.type]}
            </span>
            {idea.impact && (
              <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-muted-foreground">
                {idea.impact}
              </span>
            )}
            {idea.effort && (
              <span className="rounded-full bg-secondary px-2 py-0.5 text-[11px] text-muted-foreground">
                {idea.effort}
              </span>
            )}
          </div>

          {/* Title */}
          <h3
            className={cn(
              "text-sm font-medium leading-snug",
              isInactive && "line-through",
            )}
          >
            {idea.title}
          </h3>

          {/* Description */}
          <p className="mt-1 text-xs text-muted-foreground line-clamp-2">
            {idea.description}
          </p>
        </div>

        {/* Actions */}
        <div className="flex shrink-0 items-center gap-0.5">
          {!isInactive && !isConverted && (
            <>
              <button
                className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-primary/10 hover:text-primary transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onConvert(idea);
                }}
                title={t("ideation.convertToTask")}
              >
                <Play className="h-3.5 w-3.5" />
              </button>
              <button
                className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors"
                onClick={(e) => {
                  e.stopPropagation();
                  onDismiss(idea);
                }}
                title={t("ideation.dismiss")}
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </>
          )}
          {(isArchived || isConverted) && idea.taskId && onGoToTask && (
            <button
              className="flex h-7 w-7 items-center justify-center rounded-md text-primary hover:bg-primary/10 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                onGoToTask(idea.taskId!);
              }}
              title={t("ideation.goToTask")}
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
