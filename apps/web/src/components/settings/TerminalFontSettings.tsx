"use client";

import { useState } from "react";
import { RotateCcw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";
import {
  useTerminalFontSettingsStore,
  TERMINAL_PRESETS,
} from "@/stores/terminal-font-settings-store";

const CURSOR_STYLES = ["block", "underline", "bar"] as const;

const PRESET_LABELS: Record<string, string> = {
  vscode: "VS Code",
  intellij: "JetBrains",
  macos: "macOS",
  ubuntu: "Ubuntu",
};

/**
 * Terminal font settings — font family/size picker, cursor style, theme presets with live preview
 */
export function TerminalFontSettings() {
  const store = useTerminalFontSettingsStore();
  const { t } = useTranslation("settings");

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold mb-1">{t("sections.terminalFont.title")}</h2>
          <p className="text-sm text-muted-foreground">
            {t("sections.terminalFont.description")}
          </p>
        </div>
        <button
          onClick={() => store.resetToDefaults()}
          className="flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <RotateCcw className="h-3 w-3" />
          {t("actions.reset")}
        </button>
      </div>

      {/* Presets */}
      <div className="space-y-2">
        <p className="text-sm font-medium">{t("terminalFont.presets")}</p>
        <div className="grid grid-cols-4 gap-2">
          {Object.entries(PRESET_LABELS).map(([key, label]) => (
            <button
              key={key}
              onClick={() => store.applyPreset(key)}
              className="rounded-lg border border-border px-3 py-2 text-xs font-medium hover:border-primary/50 hover:bg-accent/50 transition-colors"
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Font settings */}
      <div className="space-y-4">
        <div className="flex items-center justify-between rounded-lg border border-border p-4">
          <div>
            <p className="text-sm font-medium">{t("terminalFont.fontFamily")}</p>
            <p className="text-xs text-muted-foreground">{store.fontFamily.join(", ")}</p>
          </div>
          <input
            className="w-48 rounded-md border border-border bg-background px-3 py-1.5 text-sm"
            value={store.fontFamily.join(", ")}
            onChange={(e) =>
              store.setFontFamily(e.target.value.split(",").map((s) => s.trim()).filter(Boolean))
            }
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="rounded-lg border border-border p-4">
            <p className="text-sm font-medium mb-2">{t("terminalFont.fontSize")}</p>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={8}
                max={32}
                value={store.fontSize}
                onChange={(e) => store.setFontSize(Number(e.target.value))}
                className="flex-1 h-2 bg-muted rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-sm font-mono w-8 text-right">{store.fontSize}</span>
            </div>
          </div>

          <div className="rounded-lg border border-border p-4">
            <p className="text-sm font-medium mb-2">{t("terminalFont.lineHeight")}</p>
            <div className="flex items-center gap-2">
              <input
                type="range"
                min={80}
                max={200}
                step={10}
                value={Math.round(store.lineHeight * 100)}
                onChange={(e) => store.setLineHeight(Number(e.target.value) / 100)}
                className="flex-1 h-2 bg-muted rounded-lg appearance-none cursor-pointer"
              />
              <span className="text-sm font-mono w-8 text-right">{store.lineHeight}</span>
            </div>
          </div>
        </div>

        {/* Cursor style */}
        <div className="rounded-lg border border-border p-4">
          <p className="text-sm font-medium mb-3">{t("terminalFont.cursorStyle")}</p>
          <div className="flex gap-3">
            {CURSOR_STYLES.map((style) => (
              <button
                key={style}
                onClick={() => store.setCursorStyle(style)}
                className={cn(
                  "flex items-center gap-2 rounded-lg border px-4 py-2 text-sm capitalize transition-colors",
                  store.cursorStyle === style
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-border/80"
                )}
              >
                <span
                  className={cn(
                    "inline-block w-2 h-4",
                    style === "block" && "bg-foreground",
                    style === "underline" && "border-b-2 border-foreground",
                    style === "bar" && "border-l-2 border-foreground"
                  )}
                />
                {style}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Live Preview */}
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="bg-muted/50 px-4 py-2 border-b border-border">
          <p className="text-xs font-medium text-muted-foreground">{t("terminalFont.preview")}</p>
        </div>
        <div
          className="bg-[#1e1e1e] text-[#d4d4d4] p-4"
          style={{
            fontFamily: store.fontFamily.join(", "),
            fontSize: `${store.fontSize}px`,
            lineHeight: store.lineHeight,
            letterSpacing: `${store.letterSpacing}px`,
          }}
        >
          <div>$ auto-claude build --spec 001</div>
          <div className="text-green-400">✓ Planning complete (3 subtasks)</div>
          <div className="text-blue-400">→ Building subtask 1/3...</div>
          <div>
            <span
              className={cn(
                "inline-block",
                store.cursorStyle === "block" && "bg-white text-black w-[0.6em]",
                store.cursorStyle === "underline" && "border-b-2 border-white",
                store.cursorStyle === "bar" && "border-l-2 border-white"
              )}
            >
              &nbsp;
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
