"use client";

/**
 * AgentProfileSelector - Agent profile dropdown
 *
 * Allows selecting which agent profile (model configuration) to use for tasks.
 * Web port of the Electron agent profile selection.
 */

import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@auto-claude/ui/primitives/select";
import { useSettingsStore } from "@/stores/settings-store";

interface AgentProfile {
  id: string;
  name: string;
  model?: string;
  description?: string;
}

interface AgentProfileSelectorProps {
  /** Available profiles */
  profiles?: AgentProfile[];
  /** Currently selected profile ID */
  value?: string;
  /** Called when selection changes */
  onValueChange?: (profileId: string) => void;
  /** Disabled state */
  disabled?: boolean;
  className?: string;
}

/** Default profiles when none are provided */
const DEFAULT_PROFILES: AgentProfile[] = [
  { id: "default", name: "Default", model: "claude-sonnet-4-20250514", description: "Balanced performance" },
  { id: "fast", name: "Fast", model: "claude-haiku-4-20250414", description: "Quick responses" },
  { id: "quality", name: "Quality", model: "claude-opus-4-20250514", description: "Best quality" },
];

export function AgentProfileSelector({
  profiles = DEFAULT_PROFILES,
  value,
  onValueChange,
  disabled = false,
  className,
}: AgentProfileSelectorProps) {
  const { t } = useTranslation("common");
  const settings = useSettingsStore((s) => s.settings);

  const selectedValue = value ?? settings.selectedAgentProfile ?? profiles[0]?.id;

  return (
    <Select
      value={selectedValue}
      onValueChange={onValueChange}
      disabled={disabled}
    >
      <SelectTrigger
        className={cn("h-8 w-[180px] text-xs", className)}
        aria-label={t("labels.selectProfile", "Select agent profile")}
      >
        <SelectValue placeholder={t("labels.selectProfile", "Select profile")} />
      </SelectTrigger>
      <SelectContent>
        {profiles.map((profile) => (
          <SelectItem key={profile.id} value={profile.id}>
            <div className="flex flex-col">
              <span>{profile.name}</span>
              {profile.model && (
                <span className="text-[10px] text-muted-foreground">{profile.model}</span>
              )}
            </div>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}
