"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";

interface ProfileEditDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  profile?: {
    id: string;
    name: string;
    apiKey: string;
    baseUrl?: string;
  } | null;
  onSave: (data: { name: string; apiKey: string; baseUrl?: string }) => void;
}

/**
 * Dialog for creating or editing an API profile
 */
export function ProfileEditDialog({
  open,
  onOpenChange,
  profile,
  onSave,
}: ProfileEditDialogProps) {
  const { t } = useTranslation("settings");
  const [name, setName] = useState(profile?.name ?? "");
  const [apiKey, setApiKey] = useState(profile?.apiKey ?? "");
  const [baseUrl, setBaseUrl] = useState(profile?.baseUrl ?? "");

  if (!open) return null;

  const handleSave = () => {
    if (!name.trim() || !apiKey.trim()) return;
    onSave({
      name: name.trim(),
      apiKey: apiKey.trim(),
      baseUrl: baseUrl.trim() || undefined,
    });
    onOpenChange(false);
  };

  const isEditing = !!profile;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={() => onOpenChange(false)}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-md rounded-lg border border-border bg-background p-6 shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">
            {isEditing ? t("profileEdit.titleEdit") : t("profileEdit.titleCreate")}
          </h3>
          <button
            onClick={() => onOpenChange(false)}
            className="p-1 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <p className="text-sm text-muted-foreground mb-4">
          {t("profileEdit.description")}
        </p>

        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium">{t("profileEdit.name")}</label>
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder={t("profileEdit.namePlaceholder")}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium">{t("profileEdit.apiKey")}</label>
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
              placeholder="sk-ant-..."
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
            />
          </div>

          <div>
            <label className="text-sm font-medium">{t("profileEdit.baseUrl")}</label>
            <input
              className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder="https://api.anthropic.com"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
            />
            <p className="text-xs text-muted-foreground mt-1">
              {t("profileEdit.baseUrlHint")}
            </p>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={() => onOpenChange(false)}
            className="rounded-md border border-border px-4 py-2 text-sm hover:bg-accent transition-colors"
          >
            {t("actions.cancel")}
          </button>
          <button
            onClick={handleSave}
            disabled={!name.trim() || !apiKey.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            {isEditing ? t("actions.save") : t("actions.create")}
          </button>
        </div>
      </div>
    </div>
  );
}
