"use client";

/**
 * ClaudeCodeStatusBadge - Claude Code CLI connection status
 *
 * Shows whether Claude Code CLI is connected and available.
 * In the web app context, this reflects backend agent connectivity.
 */

import { Circle } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@auto-claude/ui/primitives/tooltip";

type ConnectionStatus = "connected" | "disconnected" | "connecting";

interface ClaudeCodeStatusBadgeProps {
  status?: ConnectionStatus;
  version?: string;
  className?: string;
}

const STATUS_CONFIG: Record<ConnectionStatus, { color: string; dotColor: string }> = {
  connected: {
    color: "bg-green-500/10 text-green-500 border-green-500/20",
    dotColor: "text-green-500",
  },
  disconnected: {
    color: "bg-red-500/10 text-red-500 border-red-500/20",
    dotColor: "text-red-500",
  },
  connecting: {
    color: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
    dotColor: "text-yellow-500",
  },
};

export function ClaudeCodeStatusBadge({
  status = "disconnected",
  version,
  className,
}: ClaudeCodeStatusBadgeProps) {
  const { t } = useTranslation("common");

  const config = STATUS_CONFIG[status];
  const statusLabel =
    status === "connected"
      ? t("labels.connected", "Connected")
      : status === "connecting"
        ? t("labels.connecting", "Connecting...")
        : t("labels.disconnected", "Disconnected");

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={cn(
              "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5",
              config.color,
              className,
            )}
          >
            <Circle
              className={cn(
                "h-2 w-2 fill-current",
                config.dotColor,
                status === "connecting" && "animate-pulse",
              )}
            />
            <span className="text-xs font-semibold">
              {t("labels.claudeCode", "Claude Code")}
            </span>
          </div>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <div className="space-y-1">
            <div className="font-medium">{statusLabel}</div>
            {version && (
              <div className="text-muted-foreground">v{version}</div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
