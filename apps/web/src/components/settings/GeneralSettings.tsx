"use client";

import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";
import { useSettingsStore, saveSettings } from "@/stores/settings-store";

const MODELS = [
  { value: "sonnet", label: "Claude Sonnet" },
  { value: "opus", label: "Claude Opus" },
  { value: "haiku", label: "Claude Haiku" },
] as const;

/**
 * General settings section — language, default model, auto-continue
 */
export function GeneralSettings() {
  const settings = useSettingsStore((s) => s.settings);
  const { t } = useTranslation("settings");

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">{t("sections.general.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("sections.general.description")}
        </p>
      </div>

      <div className="space-y-4">
        {/* Language */}
        <div className="flex items-center justify-between rounded-lg border border-border p-4">
          <div>
            <p className="text-sm font-medium">{t("fields.language")}</p>
            <p className="text-xs text-muted-foreground">
              {t("fields.languageDescription")}
            </p>
          </div>
          <select
            className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
            value={settings.language ?? "en"}
            onChange={(e) => saveSettings({ language: e.target.value })}
          >
            <option value="en">{t("languages.en")}</option>
            <option value="fr">{t("languages.fr")}</option>
          </select>
        </div>

        {/* Default Model */}
        <div className="flex items-center justify-between rounded-lg border border-border p-4">
          <div>
            <p className="text-sm font-medium">{t("fields.defaultModel")}</p>
            <p className="text-xs text-muted-foreground">
              {t("fields.defaultModelDescription")}
            </p>
          </div>
          <select
            className="rounded-md border border-border bg-background px-3 py-1.5 text-sm"
            value={settings.defaultModel ?? "sonnet"}
            onChange={(e) => saveSettings({ defaultModel: e.target.value })}
          >
            {MODELS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
