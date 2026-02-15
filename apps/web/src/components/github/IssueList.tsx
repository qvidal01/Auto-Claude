"use client";

import { useCallback, useRef, useEffect } from "react";
import {
  AlertCircle,
  CheckCircle2,
  MessageSquare,
  Loader2,
  Search as SearchIcon,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { GitHubIssue } from "@auto-claude/types";
import { useTranslation } from "react-i18next";

interface IssueListProps {
  issues: GitHubIssue[];
  selectedIssueNumber: number | null;
  isLoading: boolean;
  isLoadingMore: boolean;
  hasMore: boolean;
  error: string | null;
  onSelectIssue: (issueNumber: number) => void;
  onInvestigate: (issue: GitHubIssue) => void;
  onLoadMore?: () => void;
  onRetry: () => void;
}

export function IssueList({
  issues,
  selectedIssueNumber,
  isLoading,
  isLoadingMore,
  hasMore,
  error,
  onSelectIssue,
  onInvestigate,
  onLoadMore,
  onRetry,
}: IssueListProps) {
  const { t } = useTranslation("integrations");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Infinite scroll
  const handleScroll = useCallback(() => {
    if (!scrollRef.current || !hasMore || isLoadingMore || !onLoadMore) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    if (scrollHeight - scrollTop - clientHeight < 200) {
      onLoadMore();
    }
  }, [hasMore, isLoadingMore, onLoadMore]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, [handleScroll]);

  if (isLoading && issues.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-8">
        <p className="text-sm text-destructive">{error}</p>
        <button
          onClick={onRetry}
          className="rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          {t("common:retry", "Retry")}
        </button>
      </div>
    );
  }

  if (issues.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center p-8">
        <div className="text-center">
          <SearchIcon className="mx-auto mb-2 h-8 w-8 text-muted-foreground/50" />
          <p className="text-sm text-muted-foreground">No issues found</p>
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto">
      {issues.map((issue) => (
        <div
          key={issue.number}
          className={cn(
            "flex items-start gap-3 border-b border-border px-4 py-3 cursor-pointer transition-colors group",
            selectedIssueNumber === issue.number
              ? "bg-accent"
              : "hover:bg-accent/50",
          )}
          onClick={() => onSelectIssue(issue.number)}
        >
          {issue.state === "open" ? (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-green-500" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-purple-500" />
          )}
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium leading-tight">
              #{issue.number} {issue.title}
            </p>
            {issue.labels.length > 0 && (
              <div className="mt-1 flex flex-wrap items-center gap-1.5">
                {issue.labels.map((label) => (
                  <span
                    key={label.name}
                    className="rounded-full border px-2 py-0.5 text-[10px]"
                    style={{
                      borderColor: `#${label.color}40`,
                      color: `#${label.color}`,
                    }}
                  >
                    {label.name}
                  </span>
                ))}
              </div>
            )}
            <div className="mt-1 flex items-center gap-3 text-[10px] text-muted-foreground">
              <span>{issue.author.login}</span>
              <span>
                {new Date(issue.createdAt).toLocaleDateString()}
              </span>
              {issue.commentsCount > 0 && (
                <span className="flex items-center gap-0.5">
                  <MessageSquare className="h-2.5 w-2.5" />
                  {issue.commentsCount}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onInvestigate(issue);
            }}
            className="shrink-0 rounded-md px-2 py-1 text-[10px] text-muted-foreground opacity-0 transition-all hover:bg-accent group-hover:opacity-100"
            title="Investigate"
          >
            Investigate
          </button>
        </div>
      ))}
      {isLoadingMore && (
        <div className="flex items-center justify-center py-4">
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        </div>
      )}
    </div>
  );
}
