"use client";

import { useState } from "react";
import {
  Settings,
  User,
  Palette,
  Globe,
  Shield,
  Bell,
  Github,
  Key,
  Database,
  Monitor,
  Moon,
  Sun,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useSettingsStore, saveSettings } from "@/stores/settings-store";

type SettingsSection =
  | "general"
  | "appearance"
  | "accounts"
  | "github"
  | "notifications"
  | "advanced";

const SECTIONS: {
  id: SettingsSection;
  label: string;
  icon: React.ElementType;
}[] = [
  { id: "general", label: "General", icon: Settings },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "accounts", label: "Accounts", icon: Key },
  { id: "github", label: "GitHub", icon: Github },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "advanced", label: "Advanced", icon: Database },
];

export function SettingsView() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("general");
  const settings = useSettingsStore((s) => s.settings);

  return (
    <div className="flex h-full overflow-hidden">
      {/* Sidebar */}
      <div className="w-56 border-r border-border bg-card/50 p-4">
        <h1 className="text-sm font-semibold mb-4 px-3">Settings</h1>
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
          {activeSection === "general" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">General</h2>
                <p className="text-sm text-muted-foreground">
                  Configure general application settings.
                </p>
              </div>

              <div className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <p className="text-sm font-medium">Language</p>
                    <p className="text-xs text-muted-foreground">
                      Select your preferred language
                    </p>
                  </div>
                  <select className="rounded-md border border-border bg-background px-3 py-1.5 text-sm">
                    <option value="en">English</option>
                    <option value="fr">French</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {activeSection === "appearance" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">Appearance</h2>
                <p className="text-sm text-muted-foreground">
                  Customize the look and feel of the application.
                </p>
              </div>

              <div className="space-y-4">
                {/* Theme */}
                <div className="rounded-lg border border-border p-4">
                  <p className="text-sm font-medium mb-3">Theme</p>
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
                            {theme}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "accounts" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">Accounts</h2>
                <p className="text-sm text-muted-foreground">
                  Manage API keys and authentication.
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Key className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">Claude API</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    Configure your Claude API authentication for AI features.
                  </p>
                  <button className="rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground hover:bg-primary/90 transition-colors">
                    Configure
                  </button>
                </div>
              </div>
            </div>
          )}

          {activeSection === "github" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">GitHub Integration</h2>
                <p className="text-sm text-muted-foreground">
                  Connect and configure your GitHub repository.
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Github className="h-4 w-4" />
                    <p className="text-sm font-medium">Repository</p>
                  </div>
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs text-muted-foreground">Repository (owner/repo)</label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        placeholder="owner/repo"
                      />
                    </div>
                    <div>
                      <label className="text-xs text-muted-foreground">Main Branch</label>
                      <input
                        className="mt-1 w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
                        placeholder="main"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeSection === "notifications" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">Notifications</h2>
                <p className="text-sm text-muted-foreground">
                  Configure notification preferences.
                </p>
              </div>

              <div className="space-y-4">
                {[
                  { label: "Task Completed", description: "Notify when a task finishes execution" },
                  { label: "Task Failed", description: "Notify when a task encounters an error" },
                  { label: "Review Needed", description: "Notify when a task needs human review" },
                ].map((item) => (
                  <div
                    key={item.label}
                    className="flex items-center justify-between rounded-lg border border-border p-4"
                  >
                    <div>
                      <p className="text-sm font-medium">{item.label}</p>
                      <p className="text-xs text-muted-foreground">{item.description}</p>
                    </div>
                    <button className="relative inline-flex h-6 w-11 items-center rounded-full bg-primary transition-colors">
                      <span className="inline-block h-4 w-4 transform rounded-full bg-white transition-transform translate-x-6" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeSection === "advanced" && (
            <div className="space-y-6">
              <div>
                <h2 className="text-lg font-semibold mb-1">Advanced</h2>
                <p className="text-sm text-muted-foreground">
                  Advanced configuration options.
                </p>
              </div>

              <div className="space-y-4">
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <Database className="h-4 w-4 text-primary" />
                    <p className="text-sm font-medium">Memory System</p>
                  </div>
                  <p className="text-xs text-muted-foreground mb-3">
                    Configure the AI memory system for your projects.
                  </p>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-green-500/10 text-green-600 px-2 py-0.5 text-xs">
                      Active
                    </span>
                    <span className="text-xs text-muted-foreground">
                      Using LadybugDB embedded database
                    </span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
