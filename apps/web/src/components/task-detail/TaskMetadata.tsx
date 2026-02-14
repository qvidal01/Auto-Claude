"use client";

import { useTranslation } from "react-i18next";
import { Tag, Gauge, Zap, Flag, FileText } from "lucide-react";
import { Badge } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskMetadataProps {
  task: Task;
}

export function TaskMetadata({ task }: TaskMetadataProps) {
  const { t } = useTranslation(["kanban"]);
  const metadata = task.metadata;

  if (!metadata) return null;

  const items = [
    {
      label: t("kanban:detail.priority", "Priority"),
      value: metadata.priority,
      icon: Flag,
      translate: (v: string) => t(`kanban:card.priority.${v}`, v),
    },
    {
      label: t("kanban:detail.complexity", "Complexity"),
      value: metadata.complexity,
      icon: Gauge,
      translate: (v: string) => t(`kanban:card.complexity.${v}`, v),
    },
    {
      label: t("kanban:detail.impact", "Impact"),
      value: metadata.impact,
      icon: Zap,
      translate: (v: string) => t(`kanban:card.impact.${v}`, v),
    },
    {
      label: t("kanban:detail.category", "Category"),
      value: metadata.category,
      icon: Tag,
      translate: (v: string) => t(`kanban:card.category.${v}`, v),
    },
  ].filter((item) => item.value);

  const referencedFiles = metadata.referencedFiles ?? [];
  const affectedFiles = metadata.affectedFiles ?? [];

  return (
    <div className="space-y-4">
      {items.length > 0 && (
        <div className="grid grid-cols-2 gap-3">
          {items.map((item) => (
            <div key={item.label} className="rounded-md border border-border p-3">
              <div className="flex items-center gap-1.5 mb-1">
                <item.icon className="h-3.5 w-3.5 text-muted-foreground" />
                <p className="text-xs text-muted-foreground">{item.label}</p>
              </div>
              <p className="text-sm font-medium capitalize">{item.translate(item.value!)}</p>
            </div>
          ))}
          {metadata.model && (
            <div className="rounded-md border border-border p-3">
              <p className="text-xs text-muted-foreground">{t("kanban:detail.model", "Model")}</p>
              <p className="text-sm font-medium capitalize">{metadata.model}</p>
            </div>
          )}
        </div>
      )}

      {referencedFiles.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">
            {t("kanban:detail.referencedFiles", "Referenced Files")}
          </h4>
          <div className="flex flex-wrap gap-1">
            {referencedFiles.map((file) => (
              <Badge key={file.id} variant="outline" className="text-xs font-mono">
                <FileText className="h-3 w-3 mr-1" />
                {file.name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {affectedFiles.length > 0 && (
        <div>
          <h4 className="text-xs font-medium text-muted-foreground mb-2">
            {t("kanban:detail.affectedFiles", "Affected Files")}
          </h4>
          <div className="flex flex-wrap gap-1">
            {affectedFiles.map((file) => (
              <Badge key={file} variant="outline" className="text-xs font-mono">
                <FileText className="h-3 w-3 mr-1" />
                {file.split("/").pop()}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
