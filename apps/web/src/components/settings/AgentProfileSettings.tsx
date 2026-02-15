"use client";

import { useState } from "react";
import { Bot, Check } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";
import { useSettingsStore, saveSettings } from "@/stores/settings-store";
import type { ModelTypeShort, ThinkingLevel } from "@auto-claude/types";

const MODELS: { value: ModelTypeShort; label: string }[] = [
  { value: "haiku", label: "Haiku" },
  { value: "sonnet", label: "Sonnet" },
  { value: "opus", label: "Opus" },
];

const THINKING_LEVELS: { value: ThinkingLevel; label: string }[] = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
];

const PHASES = ["spec", "planning", "coding", "qa"] as const;

interface ProfilePreset {
  id: string;
  name: string;
  description: string;
  icon: string;
}

const PROFILE_PRESETS: ProfilePreset[] = [
  { id: "speed", name: "Speed", description: "Fast execution with Haiku/Sonnet", icon: "⚡" },
  { id: "balanced", name: "Balanced", description: "Best mix of speed and quality", icon: "⚖️" },
  { id: "quality", name: "Quality", description: "Maximum quality with Opus", icon: "🎯" },
  { id: "custom", name: "Custom", description: "Configure each phase individually", icon: "🔧" },
];

/**
 * Agent profile settings — model per phase, thinking levels
 */
export function AgentProfileSettings() {
  const settings = useSettingsStore((s) => s.settings);
  const { t } = useTranslation("settings");
  const [selectedPreset, setSelectedPreset] = useState(
    settings.selectedAgentProfile ?? "balanced"
  );

  const handlePresetSelect = (presetId: string) => {
    setSelectedPreset(presetId);
    saveSettings({ selectedAgentProfile: presetId });
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">{t("sections.agentProfile.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("sections.agentProfile.description")}
        </p>
      </div>

      {/* Profile Presets */}
      <div className="grid grid-cols-2 gap-3">
        {PROFILE_PRESETS.map((preset) => (
          <button
            key={preset.id}
            onClick={() => handlePresetSelect(preset.id)}
            className={cn(
              "flex items-start gap-3 rounded-lg border p-4 text-left transition-colors",
              selectedPreset === preset.id
                ? "border-primary bg-primary/5"
                : "border-border hover:border-border/80"
            )}
          >
            <span className="text-xl">{preset.icon}</span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{preset.name}</span>
                {selectedPreset === preset.id && (
                  <Check className="h-3.5 w-3.5 text-primary" />
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                {preset.description}
              </p>
            </div>
          </button>
        ))}
      </div>

      {/* Per-phase config (shown for custom) */}
      {selectedPreset === "custom" && (
        <div className="rounded-lg border border-border p-4 space-y-4">
          <p className="text-sm font-medium">{t("agentProfile.phaseConfig")}</p>
          {PHASES.map((phase) => (
            <div key={phase} className="flex items-center justify-between gap-4">
              <span className="text-sm capitalize text-muted-foreground w-20">
                {t(`agentProfile.phases.${phase}`)}
              </span>
              <div className="flex gap-2 flex-1">
                <select className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs">
                  {MODELS.map((m) => (
                    <option key={m.value} value={m.value}>
                      {m.label}
                    </option>
                  ))}
                </select>
                <select className="flex-1 rounded-md border border-border bg-background px-2 py-1.5 text-xs">
                  {THINKING_LEVELS.map((l) => (
                    <option key={l.value} value={l.value}>
                      {l.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
