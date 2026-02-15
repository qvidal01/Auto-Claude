"use client";

import { useTranslation } from "react-i18next";
import {
  Lightbulb,
  Sparkles,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { cn } from "@auto-claude/ui";

interface IdeationHeaderProps {
  ideaCount: number;
  isGenerating: boolean;
  onGenerate: () => void;
  onRefresh: () => void;
  onDismissAll: () => void;
  hasIdeas: boolean;
}

export function IdeationHeader({
  ideaCount,
  isGenerating,
  onGenerate,
  onRefresh,
  onDismissAll,
  hasIdeas,
}: IdeationHeaderProps) {
  const { t } = useTranslation("views");

  return (
    <div className="flex items-center justify-between border-b border-border px-6 py-4">
      <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
          <Lightbulb className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h1 className="text-lg font-semibold">{t("ideation.title")}</h1>
          <p className="text-xs text-muted-foreground">
            {ideaCount > 0
              ? t("ideation.ideaCount", { count: ideaCount })
              : t("ideation.noIdeas")}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {hasIdeas && (
          <>
            <button
              className="flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-xs text-muted-foreground hover:bg-accent transition-colors"
              onClick={onRefresh}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              {t("ideation.refresh")}
            </button>
            <button
              className="flex h-8 items-center gap-1.5 rounded-md border border-border px-3 text-xs text-muted-foreground hover:bg-red-500/10 hover:text-red-500 transition-colors"
              onClick={onDismissAll}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t("ideation.dismissAll")}
            </button>
          </>
        )}
        <button
          className={cn(
            "flex h-8 items-center gap-1.5 rounded-md bg-primary px-4 text-xs font-medium text-primary-foreground hover:bg-primary/90 transition-colors",
            isGenerating && "opacity-50 pointer-events-none",
          )}
          onClick={onGenerate}
          disabled={isGenerating}
        >
          <Sparkles className="h-3.5 w-3.5" />
          {isGenerating ? t("ideation.generating") : t("ideation.generate")}
        </button>
      </div>
    </div>
  );
}
