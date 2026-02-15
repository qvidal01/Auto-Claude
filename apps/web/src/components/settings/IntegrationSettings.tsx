"use client";

import { useState } from "react";
import { Github, ExternalLink, Check, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui";

function GitLabIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" role="img" aria-labelledby="gitlab-icon-title">
      <title id="gitlab-icon-title">GitLab</title>
      <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z" />
    </svg>
  );
}

function LinearIcon({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="currentColor" role="img" aria-labelledby="linear-icon-title">
      <title id="linear-icon-title">Linear</title>
      <path d="M2.93 17.07A10 10 0 0 1 2 12C2 6.477 6.477 2 12 2s10 4.477 10 10-4.477 10-10 10a10 10 0 0 1-5.07-1.37l-4.56 1.07 1.07-4.56-.51-.07z" />
    </svg>
  );
}

interface IntegrationConfig {
  id: string;
  name: string;
  icon: React.ElementType;
  description: string;
  connected: boolean;
  fields: { key: string; label: string; placeholder: string; type?: string }[];
}

/**
 * Integration settings — GitHub, GitLab, Linear setup
 */
export function IntegrationSettings() {
  const { t } = useTranslation("settings");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const integrations: IntegrationConfig[] = [
    {
      id: "github",
      name: "GitHub",
      icon: Github,
      description: t("integrations.github.description"),
      connected: false,
      fields: [
        { key: "repo", label: t("fields.repositoryLabel"), placeholder: t("placeholders.ownerRepo") },
        { key: "branch", label: t("fields.mainBranch"), placeholder: t("placeholders.main") },
        { key: "token", label: t("integrations.github.token"), placeholder: "ghp_...", type: "password" },
      ],
    },
    {
      id: "gitlab",
      name: "GitLab",
      icon: GitLabIcon,
      description: t("integrations.gitlab.description"),
      connected: false,
      fields: [
        { key: "url", label: t("integrations.gitlab.url"), placeholder: "https://gitlab.com" },
        { key: "project", label: t("integrations.gitlab.project"), placeholder: "group/project" },
        { key: "token", label: t("integrations.gitlab.token"), placeholder: "glpat-...", type: "password" },
      ],
    },
    {
      id: "linear",
      name: "Linear",
      icon: LinearIcon,
      description: t("integrations.linear.description"),
      connected: false,
      fields: [
        { key: "apiKey", label: t("integrations.linear.apiKey"), placeholder: "lin_api_...", type: "password" },
        { key: "team", label: t("integrations.linear.team"), placeholder: t("integrations.linear.teamPlaceholder") },
      ],
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold mb-1">{t("sections.integrations.title")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("sections.integrations.description")}
        </p>
      </div>

      <div className="space-y-3">
        {integrations.map((integration) => {
          const Icon = integration.icon;
          const isExpanded = expandedId === integration.id;
          return (
            <div key={integration.id} className="rounded-lg border border-border overflow-hidden">
              <button
                className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors"
                onClick={() => setExpandedId(isExpanded ? null : integration.id)}
              >
                <div className="flex items-center gap-3">
                  <Icon className="h-5 w-5" />
                  <div className="text-left">
                    <p className="text-sm font-medium">{integration.name}</p>
                    <p className="text-xs text-muted-foreground">{integration.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {integration.connected && (
                    <span className="flex items-center gap-1 rounded-full bg-green-500/10 text-green-600 px-2 py-0.5 text-xs">
                      <Check className="h-3 w-3" />
                      {t("status.connected")}
                    </span>
                  )}
                  <ExternalLink className="h-4 w-4 text-muted-foreground" />
                </div>
              </button>
              {isExpanded && (
                <div className="border-t border-border p-4 space-y-3 bg-muted/30">
                  {integration.fields.map((field) => (
                    <div key={field.key}>
                      <label className="text-xs text-muted-foreground">{field.label}</label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        placeholder={field.placeholder}
                        type={field.type ?? "text"}
                      />
                    </div>
                  ))}
                  <div className="flex justify-end">
                    <button className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                      {t("actions.save")}
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
