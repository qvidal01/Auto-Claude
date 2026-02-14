"use client";

/**
 * AuthStatusIndicator - Authentication status display
 *
 * Shows the current authentication method and provider as a badge.
 * Web port of the Electron AuthStatusIndicator - adapted for web auth context.
 */

import { useMemo } from "react";
import { Key, Lock } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@auto-claude/ui/primitives/tooltip";

type AuthType = "oauth" | "api-key" | "cloud";

interface AuthStatusIndicatorProps {
  /** Authentication type */
  authType?: AuthType;
  /** Provider name (e.g., "Anthropic", "z.ai") */
  providerName?: string;
  /** Whether the user is authenticated */
  isAuthenticated?: boolean;
  className?: string;
}

/** Badge color classes by auth type */
const AUTH_BADGE_COLORS: Record<AuthType, string> = {
  oauth: "bg-orange-500/10 text-orange-500 border-orange-500/20 hover:bg-orange-500/15",
  "api-key": "bg-blue-500/10 text-blue-500 border-blue-500/20 hover:bg-blue-500/15",
  cloud: "bg-green-500/10 text-green-500 border-green-500/20 hover:bg-green-500/15",
};

export function AuthStatusIndicator({
  authType = "cloud",
  providerName,
  isAuthenticated = true,
  className,
}: AuthStatusIndicatorProps) {
  const { t } = useTranslation("common");

  const { Icon, label, badgeColor } = useMemo(() => {
    const isOAuth = authType === "oauth";
    return {
      Icon: isOAuth || authType === "cloud" ? Lock : Key,
      label: authType === "cloud"
        ? t("labels.cloudAuth", "Cloud")
        : isOAuth
          ? t("labels.oauthAuth", "OAuth")
          : t("labels.apiKeyAuth", "API Key"),
      badgeColor: AUTH_BADGE_COLORS[authType],
    };
  }, [authType, t]);

  if (!isAuthenticated) {
    return null;
  }

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            type="button"
            className={cn(
              "flex items-center gap-1.5 rounded-md border px-2.5 py-1.5 transition-all",
              badgeColor,
              className,
            )}
            aria-label={t("labels.authMethodAria", "Authentication: {{method}}", { method: label })}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="text-xs font-semibold">{label}</span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs">
          <div className="space-y-1">
            <div className="font-medium">{label}</div>
            {providerName && (
              <div className="text-muted-foreground">{providerName}</div>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
