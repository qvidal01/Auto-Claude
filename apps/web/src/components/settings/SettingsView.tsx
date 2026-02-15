"use client";

import { useState } from "react";
import {
  Settings,
  Palette,
  Key,
  Bot,
  Database,
  Terminal,
  Plug,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import { GeneralSettings } from "./GeneralSettings";
import { DisplaySettings } from "./DisplaySettings";
import { AccountSettings } from "./AccountSettings";
import { AgentProfileSettings } from "./AgentProfileSettings";
import { IntegrationSettings } from "./IntegrationSettings";
import { TerminalFontSettings } from "./TerminalFontSettings";
import { AdvancedSettings } from "./AdvancedSettings";

export type SettingsSection =
  | "general"
  | "appearance"
  | "accounts"
  | "agentProfile"
  | "integrations"
  | "terminalFont"
  | "advanced";

const SECTION_IDS: { id: SettingsSection; icon: React.ElementType }[] = [
  { id: "general", icon: Settings },
  { id: "appearance", icon: Palette },
  { id: "accounts", icon: Key },
  { id: "agentProfile", icon: Bot },
  { id: "integrations", icon: Plug },
  { id: "terminalFont", icon: Terminal },
  { id: "advanced", icon: Database },
];

/**
 * Settings dialog shell with sidebar navigation between sections.
 * Each section delegates to its own dedicated component.
 */
export function SettingsView() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("general");
  const { t } = useTranslation("settings");

  const SECTIONS = SECTION_IDS.map((s) => ({
    ...s,
    label: t(`sections.${s.id}.title`),
  }));

  const renderSection = () => {
    switch (activeSection) {
      case "general":
        return <GeneralSettings />;
      case "appearance":
        return <DisplaySettings />;
      case "accounts":
        return <AccountSettings />;
      case "agentProfile":
        return <AgentProfileSettings />;
      case "integrations":
        return <IntegrationSettings />;
      case "terminalFont":
        return <TerminalFontSettings />;
      case "advanced":
        return <AdvancedSettings />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* Sidebar */}
      <div className="w-56 border-r border-border bg-card/50 p-4">
        <h1 className="text-sm font-semibold mb-4 px-3">{t("title")}</h1>
        <nav className="space-y-1">
          {SECTIONS.map((section) => {
            const Icon = section.icon;
            return (
              <button
                key={section.id}
                className={cn(
                  "flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  activeSection === section.id
                    ? "bg-accent text-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                )}
                onClick={() => setActiveSection(section.id)}
              >
                <Icon className="h-4 w-4" />
                {section.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl">
          {renderSection()}
        </div>
      </div>
    </div>
  );
}
