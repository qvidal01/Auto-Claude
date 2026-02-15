"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import {
  Github,
  Search,
  RefreshCw,
  Settings,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import type { GitHubIssue } from "@auto-claude/types";

import { useIssuesStore, loadGitHubIssues, loadMoreGitHubIssues } from "@/stores/github/issues-store";
import { useSyncStatusStore, checkGitHubConnection } from "@/stores/github/sync-status-store";
import {
  useInvestigationStore,
  investigateGitHubIssue,
} from "@/stores/github/investigation-store";

import { IssueList } from "./IssueList";
import { IssueDetail } from "./IssueDetail";
import { InvestigationDialog } from "./InvestigationDialog";
import { GitHubSetupModal } from "./GitHubSetupModal";
import type { IssueFilterState } from "@/stores/github/issues-store";

interface GitHubIssuesViewProps {
  projectId: string;
}

export function GitHubIssuesView({ projectId }: GitHubIssuesViewProps) {
  const { t } = useTranslation("integrations");

  // Stores
  const issues = useIssuesStore((s) => s.issues);
  const isLoading = useIssuesStore((s) => s.isLoading);
  const isLoadingMore = useIssuesStore((s) => s.isLoadingMore);
  const error = useIssuesStore((s) => s.error);
  const selectedIssueNumber = useIssuesStore((s) => s.selectedIssueNumber);
  const selectIssue = useIssuesStore((s) => s.selectIssue);
  const filterState = useIssuesStore((s) => s.filterState);
  const setFilterState = useIssuesStore((s) => s.setFilterState);
  const hasMore = useIssuesStore((s) => s.hasMore);
  const getFilteredIssues = useIssuesStore((s) => s.getFilteredIssues);
  const getOpenIssuesCount = useIssuesStore((s) => s.getOpenIssuesCount);

  const isConnected = useSyncStatusStore((s) => s.isConnected());
  const repoFullName = useSyncStatusStore((s) => s.getRepoFullName());
  const syncError = useSyncStatusStore((s) => s.connectionError);

  const investigationStatus = useInvestigationStore((s) => s.investigationStatus);
  const lastInvestigationResult = useInvestigationStore((s) => s.lastInvestigationResult);
  const clearInvestigation = useInvestigationStore((s) => s.clearInvestigation);

  // Local state
  const [searchQuery, setSearchQuery] = useState("");
  const [showInvestigateDialog, setShowInvestigateDialog] = useState(false);
  const [selectedIssueForInvestigation, setSelectedIssueForInvestigation] =
    useState<GitHubIssue | null>(null);
  const [showGitHubSetup, setShowGitHubSetup] = useState(false);

  // Load issues on mount
  useEffect(() => {
    checkGitHubConnection(projectId);
    loadGitHubIssues(projectId, filterState);
  }, [projectId, filterState]);

  // Filtered + searched issues
  const filteredIssues = useMemo(() => {
    const filtered = getFilteredIssues();
    if (!searchQuery.trim()) return filtered;
    const q = searchQuery.toLowerCase();
    return filtered.filter(
      (issue) =>
        issue.title.toLowerCase().includes(q) ||
        issue.number.toString().includes(q) ||
        issue.labels.some((l) => l.name.toLowerCase().includes(q)),
    );
  }, [getFilteredIssues, searchQuery]);

  const selectedIssue = useMemo(
    () => issues.find((i) => i.number === selectedIssueNumber) ?? null,
    [issues, selectedIssueNumber],
  );

  const handleRefresh = useCallback(() => {
    loadGitHubIssues(projectId, filterState);
  }, [projectId, filterState]);

  const handleLoadMore = useCallback(() => {
    loadMoreGitHubIssues(projectId, filterState);
  }, [projectId, filterState]);

  const handleFilterChange = useCallback(
    (newFilter: IssueFilterState) => {
      setFilterState(newFilter);
    },
    [setFilterState],
  );

  const handleInvestigate = useCallback((issue: GitHubIssue) => {
    setSelectedIssueForInvestigation(issue);
    setShowInvestigateDialog(true);
  }, []);

  const handleStartInvestigation = useCallback(
    (selectedCommentIds: number[]) => {
      if (selectedIssueForInvestigation) {
        investigateGitHubIssue(
          projectId,
          selectedIssueForInvestigation.number,
          selectedCommentIds,
        );
      }
    },
    [selectedIssueForInvestigation, projectId],
  );

  const handleCloseDialog = useCallback(() => {
    setShowInvestigateDialog(false);
    clearInvestigation();
  }, [clearInvestigation]);

  // Not connected state
  if (!isConnected) {
    return (
      <>
        <div className="flex h-full flex-col items-center justify-center p-8">
          <div className="max-w-md text-center">
            <div className="mb-6 flex justify-center">
              <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-secondary">
                <Github className="h-8 w-8 text-muted-foreground" />
              </div>
            </div>
            <h2 className="mb-3 text-xl font-semibold">
              {t("github.issues.notConnected")}
            </h2>
            <p className="mb-6 text-sm text-muted-foreground">
              {t("github.issues.notConnectedDescription")}
            </p>
            {syncError && (
              <p className="mb-4 text-sm text-destructive">{syncError}</p>
            )}
            <button
              onClick={() => setShowGitHubSetup(true)}
              className="mx-auto flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <Settings className="h-4 w-4" />
              {t("github.issues.configure")}
            </button>
          </div>
        </div>
        <GitHubSetupModal
          open={showGitHubSetup}
          onOpenChange={setShowGitHubSetup}
          projectId={projectId}
          onComplete={() => {
            setShowGitHubSetup(false);
            handleRefresh();
          }}
        />
      </>
    );
  }

  return (
    <>
      <div className="flex h-full flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div className="flex items-center gap-3">
            <h1 className="flex items-center gap-2 text-sm font-semibold">
              <Github className="h-4 w-4" />
              {t("github.issues.title")}
            </h1>
            {repoFullName && (
              <span className="text-xs text-muted-foreground">
                {repoFullName}
              </span>
            )}
            <span className="rounded-full bg-secondary px-2 py-0.5 text-[10px] text-muted-foreground">
              {getOpenIssuesCount()} open
            </span>
          </div>
          <div className="flex items-center gap-2">
            {/* Filter */}
            <div className="flex items-center rounded-md border border-border text-xs">
              {(["open", "closed", "all"] as IssueFilterState[]).map((f) => (
                <button
                  key={f}
                  onClick={() => handleFilterChange(f)}
                  className={cn(
                    "px-2.5 py-1 capitalize transition-colors",
                    filterState === f
                      ? "bg-accent font-medium"
                      : "hover:bg-accent/50",
                  )}
                >
                  {f}
                </button>
              ))}
            </div>
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-accent disabled:opacity-50"
            >
              <RefreshCw
                className={cn("h-3.5 w-3.5", isLoading && "animate-spin")}
              />
            </button>
          </div>
        </div>

        {/* Search */}
        <div className="border-b border-border px-4 py-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              className="w-full rounded-md border border-border bg-background py-1.5 pl-8 pr-3 text-sm focus:outline-none focus:ring-1 focus:ring-primary/20"
              placeholder={t("github.issues.search")}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Content */}
        <div className="flex flex-1 overflow-hidden">
          {/* Issue List */}
          <div
            className={cn(
              "flex flex-col border-r border-border",
              selectedIssue ? "w-96" : "flex-1",
            )}
          >
            <IssueList
              issues={filteredIssues}
              selectedIssueNumber={selectedIssueNumber}
              isLoading={isLoading}
              isLoadingMore={isLoadingMore}
              hasMore={hasMore}
              error={error}
              onSelectIssue={(n) => selectIssue(n)}
              onInvestigate={handleInvestigate}
              onLoadMore={handleLoadMore}
              onRetry={handleRefresh}
            />
          </div>

          {/* Issue Detail */}
          <div className="flex flex-1 flex-col">
            {selectedIssue ? (
              <IssueDetail
                issue={selectedIssue}
                onInvestigate={() => handleInvestigate(selectedIssue)}
                investigationResult={
                  lastInvestigationResult?.issueNumber === selectedIssue.number
                    ? lastInvestigationResult
                    : null
                }
              />
            ) : (
              <div className="flex flex-1 items-center justify-center">
                <p className="text-sm text-muted-foreground">
                  Select an issue to view details
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Investigation Dialog */}
      <InvestigationDialog
        open={showInvestigateDialog}
        onOpenChange={setShowInvestigateDialog}
        issue={selectedIssueForInvestigation}
        status={investigationStatus}
        result={lastInvestigationResult}
        onStartInvestigation={handleStartInvestigation}
        onClose={handleCloseDialog}
      />

      {/* GitHub Setup Modal */}
      <GitHubSetupModal
        open={showGitHubSetup}
        onOpenChange={setShowGitHubSetup}
        projectId={projectId}
        onComplete={() => {
          setShowGitHubSetup(false);
          handleRefresh();
        }}
      />
    </>
  );
}
