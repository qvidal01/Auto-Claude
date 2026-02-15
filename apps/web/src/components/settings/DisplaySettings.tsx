"use client";

import { useState } from "react";
import { Monitor, Moon, Sun, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";
import { useSettingsStore, saveSettings } from "@/stores/settings-store";
import type { ColorTheme } from "@auto-claude/types";

const UI_SCALE_MIN = 75;
const UI_SCALE_MAX = 200;
const UI_SCALE_DEFAULT = 100;
const UI_SCALE_STEP = 5;

const COLOR_THEMES: { id: ColorTheme; label: string; preview: { light: string; dark: string } }[] = [
  { id: "default", label: "Default", preview: { light: "#6366f1", dark: "#818cf8" } },
  { id: "dusk", label: "Dusk", preview: { light: "#8b5cf6", dark: "#a78bfa" } },
  { id: "lime", label: "Lime", preview: { light: "#84cc16", dark: "#a3e635" } },
  { id: "ocean", label: "Ocean", preview: { light: "#0ea5e9", dark: "#38bdf8" } },
  { id: "retro", label: "Retro", preview: { light: "#f59e0b", dark: "#fbbf24" } },
  { id: "neo", label: "Neo", preview: { light: "#ec4899", dark: "#f472b6" } },
  { id: "forest", label: "Forest", preview: { light: "#22c55e", dark: "#4ade80" } },
];

/**
 * Display settings — theme selector with 7 color themes, light/dark mode, UI scale
 */
export function DisplaySettings() {
  const settings = useSettingsStore((s) => s.settings);
  const { t } = useTranslation("settings");
  const [pendingScale, setPendingScale] = useState<number | null>(null);
  const displayScale = pendingScale ?? (settings.uiScale ?? UI_SCALE_DEFAULT);

  const handleScaleChange = (value: number) => {
    const clamped = Math.max(UI_SCALE_MIN, Math.min(UI_SCALE_MAX, value));
    setPendingScale(clamped);
  };

  const applyScale = () => {
    if (pendingScale !== null) {
      saveSettings({ uiScale: pendingScale });
      setPendingScale(null);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">{t("sections.appearance.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("sections.appearance.description")}
        </p>
      </div>

      <div className="space-y-4">
        {/* Light / Dark / System */}
        <div className="rounded-lg border border-border p-4">
          <p className="text-sm font-medium mb-3">{t("fields.theme")}</p>
          <div className="grid grid-cols-3 gap-3">
            {(["light", "dark", "system"] as const).map((theme) => {
              const Icon = theme === "light" ? Sun : theme === "dark" ? Moon : Monitor;
              return (
                <button
                  key={theme}
                  className={cn(
                    "flex flex-col items-center gap-2 rounded-lg border p-4 transition-colors",
                    settings.theme === theme
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-border/80"
                  )}
                  onClick={() => saveSettings({ theme })}
                >
                  <Icon className="h-5 w-5" />
                  <span className="text-xs font-medium capitalize">
                    {t(`themes.${theme}`)}
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Color Theme */}
        <div className="rounded-lg border border-border p-4">
          <p className="text-sm font-medium mb-3">{t("fields.colorTheme")}</p>
          <div className="grid grid-cols-4 gap-3">
            {COLOR_THEMES.map((theme) => (
              <button
                key={theme.id}
                className={cn(
                  "flex flex-col items-center gap-2 rounded-lg border p-3 transition-colors",
                  settings.colorTheme === theme.id
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-border/80"
                )}
                onClick={() => saveSettings({ colorTheme: theme.id })}
              >
                <div
                  className="h-6 w-6 rounded-full"
                  style={{ backgroundColor: theme.preview.light }}
                />
                <span className="text-xs font-medium">{theme.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* UI Scale */}
        <div className="rounded-lg border border-border p-4">
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-medium">{t("fields.uiScale")}</p>
            <div className="flex items-center gap-2">
              <span className="text-sm font-mono text-muted-foreground">
                {displayScale}%
              </span>
              {displayScale !== UI_SCALE_DEFAULT && (
                <button
                  onClick={() => {
                    saveSettings({ uiScale: UI_SCALE_DEFAULT });
                    setPendingScale(null);
                  }}
                  className="p-1 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => handleScaleChange(displayScale - UI_SCALE_STEP)}
              disabled={displayScale <= UI_SCALE_MIN}
              className="p-1 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
            <input
              type="range"
              min={UI_SCALE_MIN}
              max={UI_SCALE_MAX}
              step={UI_SCALE_STEP}
              value={displayScale}
              onChange={(e) => handleScaleChange(Number.parseInt(e.target.value, 10))}
              className="flex-1 h-2 bg-muted rounded-lg appearance-none cursor-pointer"
            />
            <button
              onClick={() => handleScaleChange(displayScale + UI_SCALE_STEP)}
              disabled={displayScale >= UI_SCALE_MAX}
              className="p-1 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
          </div>
          {pendingScale !== null && pendingScale !== (settings.uiScale ?? UI_SCALE_DEFAULT) && (
            <div className="mt-3 flex justify-end">
              <button
                onClick={applyScale}
                className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors"
              >
                {t("actions.apply")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
