/**
 * Usage Indicator - Real-time Claude usage display in header
 *
 * Displays current session/weekly usage as a badge with color-coded status.
 * Shows detailed breakdown on hover.
 */

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Activity, TrendingUp, AlertCircle } from 'lucide-react';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from './ui/tooltip';
import { UsageProgressBar } from './ui/usage-progress-bar';
import { getUsageBadgeClasses, isUsageCritical, isUsageWarning } from '../lib/usage-colors';
import type { ClaudeUsageSnapshot } from '../../shared/types/agent';

export function UsageIndicator() {
  const { t } = useTranslation(['navigation']);
  const [usage, setUsage] = useState<ClaudeUsageSnapshot | null>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Listen for usage updates from main process
    const unsubscribe = window.electronAPI.onUsageUpdated((snapshot: ClaudeUsageSnapshot) => {
      setUsage(snapshot);
      setIsVisible(true);
    });

    // Request initial usage on mount
    window.electronAPI.requestUsageUpdate().then((result) => {
      if (result.success && result.data) {
        setUsage(result.data);
        setIsVisible(true);
      }
    });

    return () => {
      unsubscribe();
    };
  }, []);

  if (!isVisible || !usage) {
    return null;
  }

  // Determine color based on highest usage percentage
  const maxUsage = Math.max(usage.sessionPercent, usage.weeklyPercent);
  const colorClasses = getUsageBadgeClasses(maxUsage);

  const Icon =
    isUsageCritical(maxUsage) ? AlertCircle :
    isUsageWarning(maxUsage) ? TrendingUp :
    Activity;

  return (
    <TooltipProvider delayDuration={200}>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md border transition-all hover:opacity-80 ${colorClasses}`}
            aria-label={t('navigation:accountProfile.usageStatusAriaLabel')}
          >
            <Icon className="h-3.5 w-3.5" />
            <span className="text-xs font-semibold font-mono">
              {Math.round(maxUsage)}%
            </span>
          </button>
        </TooltipTrigger>
        <TooltipContent side="bottom" className="text-xs w-64">
          <div className="space-y-2">
            {/* Session usage */}
            <div>
              <div className="flex items-center justify-between gap-4 mb-1">
                <span className="text-muted-foreground font-medium">{t('navigation:accountProfile.sessionUsage')}</span>
                <span className="font-semibold tabular-nums">{Math.round(usage.sessionPercent)}%</span>
              </div>
              {usage.sessionResetTime && (
                <div className="text-[10px] text-muted-foreground">
                  {t('navigation:accountProfile.resetsAt', { time: usage.sessionResetTime })}
                </div>
              )}
              {/* Progress bar */}
              <UsageProgressBar percent={usage.sessionPercent} />
            </div>

            <div className="h-px bg-border" />

            {/* Weekly usage */}
            <div>
              <div className="flex items-center justify-between gap-4 mb-1">
                <span className="text-muted-foreground font-medium">{t('navigation:accountProfile.weeklyUsage')}</span>
                <span className="font-semibold tabular-nums">{Math.round(usage.weeklyPercent)}%</span>
              </div>
              {usage.weeklyResetTime && (
                <div className="text-[10px] text-muted-foreground">
                  {t('navigation:accountProfile.resetsAt', { time: usage.weeklyResetTime })}
                </div>
              )}
              {/* Progress bar */}
              <UsageProgressBar percent={usage.weeklyPercent} />
            </div>

            <div className="h-px bg-border" />

            {/* Active profile */}
            <div className="flex items-center justify-between gap-4 pt-1">
              <span className="text-muted-foreground text-[10px] uppercase tracking-wide">{t('navigation:accountProfile.activeAccount')}</span>
              <span className="font-semibold text-primary">{usage.profileName}</span>
            </div>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
