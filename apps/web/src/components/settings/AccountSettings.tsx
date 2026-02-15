"use client";

import { useState } from "react";
import { Key, Plus, Trash2, Star, Eye, EyeOff } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";

interface ApiProfile {
  id: string;
  name: string;
  apiKey: string;
  baseUrl?: string;
  isActive: boolean;
}

/**
 * Account settings — Claude profiles list, add/remove accounts, active profile selection
 */
export function AccountSettings() {
  const { t } = useTranslation("settings");
  const [profiles, setProfiles] = useState<ApiProfile[]>([]);
  const [showKey, setShowKey] = useState<string | null>(null);
  const [isAdding, setIsAdding] = useState(false);
  const [newName, setNewName] = useState("");
  const [newKey, setNewKey] = useState("");
  const [newUrl, setNewUrl] = useState("");

  const maskKey = (key: string) => {
    if (key.length <= 8) return "••••••••";
    return `${key.slice(0, 4)}${"•".repeat(key.length - 8)}${key.slice(-4)}`;
  };

  const handleAdd = () => {
    if (!newName.trim() || !newKey.trim()) return;
    const profile: ApiProfile = {
      id: crypto.randomUUID(),
      name: newName.trim(),
      apiKey: newKey.trim(),
      baseUrl: newUrl.trim() || undefined,
      isActive: profiles.length === 0,
    };
    setProfiles([...profiles, profile]);
    setNewName("");
    setNewKey("");
    setNewUrl("");
    setIsAdding(false);
  };

  const handleRemove = (id: string) => {
    setProfiles((prev) => prev.filter((p) => p.id !== id));
  };

  const handleSetActive = (id: string) => {
    setProfiles((prev) =>
      prev.map((p) => ({ ...p, isActive: p.id === id }))
    );
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">{t("sections.accounts.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("sections.accounts.description")}
        </p>
      </div>

      <div className="space-y-4">
        {/* Profile list */}
        {profiles.map((profile) => (
          <div
            key={profile.id}
            className={cn(
              "rounded-lg border p-4 transition-colors",
              profile.isActive ? "border-primary bg-primary/5" : "border-border"
            )}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Key className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">{profile.name}</span>
                {profile.isActive && (
                  <span className="rounded-full bg-primary/10 text-primary px-2 py-0.5 text-xs">
                    {t("status.active")}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-1">
                {!profile.isActive && (
                  <button
                    onClick={() => handleSetActive(profile.id)}
                    className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                    title={t("actions.setActive")}
                  >
                    <Star className="h-4 w-4" />
                  </button>
                )}
                <button
                  onClick={() => setShowKey(showKey === profile.id ? null : profile.id)}
                  className="p-1.5 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
                >
                  {showKey === profile.id ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </button>
                <button
                  onClick={() => handleRemove(profile.id)}
                  className="p-1.5 rounded-md hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground font-mono">
              {showKey === profile.id ? profile.apiKey : maskKey(profile.apiKey)}
            </div>
            {profile.baseUrl && (
              <div className="mt-1 text-xs text-muted-foreground">
                {profile.baseUrl}
              </div>
            )}
          </div>
        ))}

        {profiles.length === 0 && !isAdding && (
          <div className="rounded-lg border border-dashed border-border p-6 text-center">
            <Key className="h-8 w-8 mx-auto mb-2 text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              {t("accounts.noProfiles")}
            </p>
          </div>
        )}

        {/* Add form */}
        {isAdding ? (
          <div className="rounded-lg border border-border p-4 space-y-3">
            <input
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder={t("accounts.namePlaceholder")}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
            />
            <input
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm font-mono"
              placeholder={t("accounts.keyPlaceholder")}
              type="password"
              value={newKey}
              onChange={(e) => setNewKey(e.target.value)}
            />
            <input
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              placeholder={t("accounts.urlPlaceholder")}
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={() => setIsAdding(false)}
                className="rounded-md border border-border px-3 py-1.5 text-sm hover:bg-accent transition-colors"
              >
                {t("actions.cancel")}
              </button>
              <button
                onClick={handleAdd}
                disabled={!newName.trim() || !newKey.trim()}
                className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                {t("actions.add")}
              </button>
            </div>
          </div>
        ) : (
          <button
            onClick={() => setIsAdding(true)}
            className="flex items-center gap-2 rounded-md border border-dashed border-border px-4 py-2 text-sm text-muted-foreground hover:text-foreground hover:border-border/80 transition-colors"
          >
            <Plus className="h-4 w-4" />
            {t("accounts.addProfile")}
          </button>
        )}
      </div>
    </div>
  );
}
