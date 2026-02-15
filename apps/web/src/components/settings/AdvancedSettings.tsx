"use client";

import { useState } from "react";
import { Bug, Database, Server, Shield } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";

/**
 * Advanced settings — developer options, debug mode, MCP servers
 */
export function AdvancedSettings() {
  const { t } = useTranslation("settings");
  const [debugMode, setDebugMode] = useState(false);
  const [mcpServers, setMcpServers] = useState<string[]>([]);
  const [newMcpUrl, setNewMcpUrl] = useState("");

  const handleAddMcp = () => {
    if (!newMcpUrl.trim()) return;
    setMcpServers((prev) => [...prev, newMcpUrl.trim()]);
    setNewMcpUrl("");
  };

  const handleRemoveMcp = (index: number) => {
    setMcpServers((prev) => prev.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">{t("sections.advanced.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("sections.advanced.description")}
        </p>
      </div>

      <div className="space-y-4">
        {/* Memory System */}
        <div className="rounded-lg border border-border p-4">
          <div className="flex items-center gap-2 mb-3">
            <Database className="h-4 w-4 text-primary" />
            <p className="text-sm font-medium">{t("fields.memorySystem")}</p>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            {t("fields.memorySystemDescription")}
          </p>
          <div className="flex items-center gap-2">
            <span className="rounded-full bg-green-500/10 text-green-600 px-2 py-0.5 text-xs">
              {t("status.active")}
            </span>
            <span className="text-xs text-muted-foreground">
              {t("status.usingLadybugDb")}
            </span>
          </div>
        </div>

        {/* Debug Mode */}
        <div className="flex items-center justify-between rounded-lg border border-border p-4">
          <div className="flex items-center gap-3">
            <Bug className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{t("advanced.debugMode")}</p>
              <p className="text-xs text-muted-foreground">
                {t("advanced.debugModeDescription")}
              </p>
            </div>
          </div>
          <button
            onClick={() => setDebugMode(!debugMode)}
            className={cn(
              "relative inline-flex h-6 w-11 items-center rounded-full transition-colors",
              debugMode ? "bg-primary" : "bg-muted"
            )}
          >
            <span
              className={cn(
                "inline-block h-4 w-4 rounded-full bg-white transition-transform",
                debugMode ? "translate-x-6" : "translate-x-1"
              )}
            />
          </button>
        </div>

        {/* MCP Servers */}
        <div className="rounded-lg border border-border p-4">
          <div className="flex items-center gap-2 mb-3">
            <Server className="h-4 w-4 text-muted-foreground" />
            <p className="text-sm font-medium">{t("advanced.mcpServers")}</p>
          </div>
          <p className="text-xs text-muted-foreground mb-3">
            {t("advanced.mcpServersDescription")}
          </p>

          {mcpServers.length > 0 && (
            <div className="space-y-2 mb-3">
              {mcpServers.map((url, i) => (
                <div key={url} className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
                  <span className="font-mono text-xs truncate">{url}</span>
                  <button
                    onClick={() => handleRemoveMcp(i)}
                    className="text-xs text-muted-foreground hover:text-destructive transition-colors ml-2"
                  >
                    {t("actions.remove")}
                  </button>
                </div>
              ))}
            </div>
          )}

          <div className="flex gap-2">
            <input
              className="flex-1 rounded-md border border-border bg-background px-3 py-1.5 text-sm"
              placeholder={t("advanced.mcpUrlPlaceholder")}
              value={newMcpUrl}
              onChange={(e) => setNewMcpUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleAddMcp()}
            />
            <button
              onClick={handleAddMcp}
              disabled={!newMcpUrl.trim()}
              className="rounded-md bg-primary px-3 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
            >
              {t("actions.add")}
            </button>
          </div>
        </div>

        {/* Error Reporting */}
        <div className="flex items-center justify-between rounded-lg border border-border p-4">
          <div className="flex items-center gap-3">
            <Shield className="h-4 w-4 text-muted-foreground" />
            <div>
              <p className="text-sm font-medium">{t("advanced.errorReporting")}</p>
              <p className="text-xs text-muted-foreground">
                {t("advanced.errorReportingDescription")}
              </p>
            </div>
          </div>
          <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary transition-colors">
            <span className="inline-block h-4 w-4 rounded-full bg-white transition-transform translate-x-6" />
          </button>
        </div>
      </div>
    </div>
  );
}
