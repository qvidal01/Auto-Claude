/**
 * Shared utilities for branch selection across the application.
 * Used by TaskCreationWizard, CreateWorktreeDialog, and GitHubIntegration.
 */
import { GitBranch, Cloud } from 'lucide-react';
import type { ComboboxOption } from '../components/ui/combobox';
import type { BranchInfo } from '../../shared/types';
import { cn } from './utils';

/**
 * Configuration for building branch options
 */
export interface BranchOptionsConfig {
  /** Translation function */
  t: (key: string, options?: Record<string, string>) => string;
  /** Namespace prefix for translations (e.g., 'tasks:wizard.gitOptions' or 'terminal:worktree') */
  translationPrefix: string;
  /** Optional: Include a "use project default" option at the top */
  includeProjectDefault?: {
    /** The special value to use for the project default option */
    value: string;
    /** The name of the project's default branch (e.g., 'develop') */
    branchName: string;
    /** Translation key for the label (will receive { branch } interpolation) */
    labelKey: string;
  };
  /** Optional: Include an "auto-detect" option (used in GitHub settings) */
  includeAutoDetect?: {
    /** The value to use for auto-detect (usually empty string) */
    value: string;
    /** The label to display */
    label: string;
  };
}

/**
 * Builds ComboboxOption[] from BranchInfo[] with proper grouping, icons, and badges.
 * This shared function ensures consistent branch display across all branch selectors.
 */
export function buildBranchOptions(
  branches: BranchInfo[],
  config: BranchOptionsConfig
): ComboboxOption[] {
  const { t, translationPrefix, includeProjectDefault, includeAutoDetect } = config;

  // Separate local and remote branches
  const localBranches = branches.filter((b) => b.type === 'local');
  const remoteBranches = branches.filter((b) => b.type === 'remote');

  // Build local branch options
  const localOptions: ComboboxOption[] = localBranches.map((branch) => ({
    value: branch.name,
    label: branch.displayName,
    group: t(`${translationPrefix}.branchGroups.local`),
    icon: <GitBranch className="h-3.5 w-3.5" />,
    badge: (
      <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
        {t(`${translationPrefix}.branchType.local`)}
      </span>
    ),
  }));

  // Build remote branch options
  const remoteOptions: ComboboxOption[] = remoteBranches.map((branch) => ({
    value: branch.name,
    label: branch.displayName,
    group: t(`${translationPrefix}.branchGroups.remote`),
    icon: <Cloud className="h-3.5 w-3.5" />,
    badge: (
      <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/10 text-blue-600 dark:text-blue-400">
        {t(`${translationPrefix}.branchType.remote`)}
      </span>
    ),
  }));

  // Build final options array
  const options: ComboboxOption[] = [];

  // Add auto-detect option if configured (for GitHub settings)
  if (includeAutoDetect) {
    options.push({
      value: includeAutoDetect.value,
      label: includeAutoDetect.label,
    });
  }

  // Add project default option if configured (for task creation and worktree dialogs)
  if (includeProjectDefault) {
    const { value, branchName, labelKey } = includeProjectDefault;

    // Determine if project default branch is local or remote
    const defaultBranchInfo = branches.find((b) => b.name === branchName);
    const isDefaultLocal = defaultBranchInfo?.type === 'local';

    options.push({
      value,
      label: t(labelKey, { branch: branchName }),
      icon: isDefaultLocal ? <GitBranch className="h-3.5 w-3.5" /> : <Cloud className="h-3.5 w-3.5" />,
      badge: defaultBranchInfo ? (
        <span className={cn(
          "text-xs px-1.5 py-0.5 rounded",
          isDefaultLocal
            ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
            : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
        )}>
          {isDefaultLocal
            ? t(`${translationPrefix}.branchType.local`)
            : t(`${translationPrefix}.branchType.remote`)}
        </span>
      ) : undefined,
    });
  }

  // Add local branches, then remote branches
  options.push(...localOptions, ...remoteOptions);

  return options;
}

/**
 * Creates badge JSX for a branch type indicator
 */
export function createBranchTypeBadge(
  type: 'local' | 'remote',
  t: (key: string) => string,
  translationPrefix: string
): React.ReactNode {
  const isLocal = type === 'local';
  return (
    <span className={cn(
      "text-xs px-1.5 py-0.5 rounded",
      isLocal
        ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
        : "bg-blue-500/10 text-blue-600 dark:text-blue-400"
    )}>
      {t(`${translationPrefix}.branchType.${type}`)}
    </span>
  );
}

/**
 * Returns the appropriate icon for a branch type
 */
export function getBranchIcon(type: 'local' | 'remote'): React.ReactNode {
  return type === 'local'
    ? <GitBranch className="h-3.5 w-3.5" />
    : <Cloud className="h-3.5 w-3.5" />;
}
