"use client";

import { useEffect, useRef } from "react";
import { useTranslation } from "react-i18next";
import { Terminal } from "lucide-react";
import { cn, ScrollArea } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskLogsProps {
  task: Task;
}

export function TaskLogs({ task }: TaskLogsProps) {
  const { t } = useTranslation(["kanban"]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new logs arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [task.logs.length]);

  if (!task.logs || task.logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <Terminal className="h-8 w-8 mb-2 opacity-50" />
        <p className="text-sm">
          {t("kanban:detail.noLogs", "No execution logs yet")}
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-border bg-black/90 overflow-hidden">
      <div
        ref={scrollRef}
        className="max-h-[400px] overflow-y-auto p-4 font-mono text-xs leading-relaxed"
      >
        {task.logs.map((log, index) => (
          <div
            key={index}
            className={cn(
              "py-0.5",
              log.includes("ERROR") || log.includes("error")
                ? "text-red-400"
                : log.includes("SUCCESS") || log.includes("✓")
                  ? "text-green-400"
                  : log.includes("WARNING") || log.includes("⚠")
                    ? "text-yellow-400"
                    : "text-gray-300",
            )}
          >
            {log}
          </div>
        ))}
      </div>
    </div>
  );
}
