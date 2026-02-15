"use client";

import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";
import type { IdeationType, IdeationStatus } from "@/stores/ideation-store";

const IDEATION_TYPE_OPTIONS: { value: IdeationType | "all"; labelKey: string }[] = [
  { value: "all", labelKey: "ideation.filters.all" },
  { value: "code_improvements", labelKey: "ideation.filters.codeImprovements" },
  { value: "ui_ux_improvements", labelKey: "ideation.filters.uiUx" },
  { value: "documentation_gaps", labelKey: "ideation.filters.documentation" },
  { value: "security_hardening", labelKey: "ideation.filters.security" },
  { value: "performance_optimizations", labelKey: "ideation.filters.performance" },
  { value: "code_quality", labelKey: "ideation.filters.codeQuality" },
];

const IDEATION_STATUS_OPTIONS: { value: IdeationStatus | "all"; labelKey: string }[] = [
  { value: "all", labelKey: "ideation.filters.allStatuses" },
  { value: "new", labelKey: "ideation.filters.new" },
  { value: "reviewed", labelKey: "ideation.filters.reviewed" },
  { value: "converted", labelKey: "ideation.filters.converted" },
  { value: "dismissed", labelKey: "ideation.filters.dismissed" },
];

interface IdeationFiltersProps {
  activeType: IdeationType | "all";
  activeStatus: IdeationStatus | "all";
  onTypeChange: (type: IdeationType | "all") => void;
  onStatusChange: (status: IdeationStatus | "all") => void;
  typeCounts: Record<string, number>;
}

export function IdeationFilters({
  activeType,
  activeStatus,
  onTypeChange,
  onStatusChange,
  typeCounts,
}: IdeationFiltersProps) {
  const { t } = useTranslation("views");

  return (
    <div className="space-y-3 px-6">
      {/* Type filters */}
      <div className="flex items-center gap-1.5 overflow-x-auto">
        {IDEATION_TYPE_OPTIONS.map((option) => {
          const count = option.value === "all"
            ? Object.values(typeCounts).reduce((a, b) => a + b, 0)
            : typeCounts[option.value] ?? 0;
          return (
            <button
              key={option.value}
              className={cn(
                "shrink-0 rounded-full px-3 py-1 text-xs font-medium transition-colors",
                activeType === option.value
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:bg-accent",
              )}
              onClick={() => onTypeChange(option.value)}
            >
              {t(option.labelKey)} {count > 0 && `(${count})`}
            </button>
          );
        })}
      </div>

      {/* Status filters */}
      <div className="flex items-center gap-1.5">
        {IDEATION_STATUS_OPTIONS.map((option) => (
          <button
            key={option.value}
            className={cn(
              "shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-medium transition-colors",
              activeStatus === option.value
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:bg-accent",
            )}
            onClick={() => onStatusChange(option.value)}
          >
            {t(option.labelKey)}
          </button>
        ))}
      </div>
    </div>
  );
}
