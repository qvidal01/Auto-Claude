"use client";

import {
  ExternalLink,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  User,
  Calendar,
  MessageSquare,
  Sparkles,
} from "lucide-react";
import { cn } from "@auto-claude/ui";
import type { GitHubIssue, GitHubInvestigationResult } from "@auto-claude/types";
import { useTranslation } from "react-i18next";

interface IssueDetailProps {
  issue: GitHubIssue;
  onInvestigate: () => void;
  onCreateTask?: () => void;
  investigationResult: GitHubInvestigationResult | null;
}

export function IssueDetail({
  issue,
  onInvestigate,
  onCreateTask,
  investigationResult,
}: IssueDetailProps) {
  const { t } = useTranslation("integrations");

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-6 py-3">
        <h2 className="min-w-0 flex-1 truncate text-sm font-semibold">
          #{issue.number} {issue.title}
        </h2>
        <div className="flex shrink-0 items-center gap-2">
          <a
            href={issue.htmlUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex h-7 w-7 items-center justify-center rounded-md transition-colors hover:bg-accent"
          >
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-5">
          {/* Meta info */}
          <div className="flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
            <span
              className={cn(
                "flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium",
                issue.state === "open"
                  ? "border-green-500/30 text-green-600"
                  : "border-purple-500/30 text-purple-600",
              )}
            >
              {issue.state === "open" ? (
                <AlertCircle className="h-3 w-3" />
              ) : (
                <CheckCircle2 className="h-3 w-3" />
              )}
              {issue.state}
            </span>
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" />
              {issue.author.login}
            </span>
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(issue.createdAt).toLocaleDateString()}
            </span>
            <span className="flex items-center gap-1">
              <MessageSquare className="h-3 w-3" />
              {issue.commentsCount} comments
            </span>
          </div>

          {/* Labels */}
          {issue.labels.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {issue.labels.map((label) => (
                <span
                  key={label.name}
                  className="rounded-full border px-2.5 py-0.5 text-xs"
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

          {/* Assignees */}
          {issue.assignees.length > 0 && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Assignees:</span>
              {issue.assignees.map((assignee) => (
                <span
                  key={assignee.login}
                  className="rounded-full bg-secondary px-2.5 py-0.5 text-xs"
                >
                  {assignee.login}
                </span>
              ))}
            </div>
          )}

          {/* Body */}
          <div className="whitespace-pre-wrap text-sm text-muted-foreground">
            {issue.body || "No description provided."}
          </div>

          {/* Investigation Result */}
          {investigationResult && investigationResult.success && (
            <div className="rounded-lg border border-border bg-secondary/30 p-4 space-y-3">
              <h3 className="flex items-center gap-2 text-sm font-semibold">
                <Sparkles className="h-4 w-4 text-yellow-500" />
                AI Investigation
              </h3>
              <div className="space-y-2 text-sm">
                <div>
                  <span className="font-medium">Summary:</span>
                  <p className="mt-1 text-muted-foreground">
                    {investigationResult.analysis.summary}
                  </p>
                </div>
                <div>
                  <span className="font-medium">Proposed Solution:</span>
                  <p className="mt-1 text-muted-foreground">
                    {investigationResult.analysis.proposedSolution}
                  </p>
                </div>
                {investigationResult.analysis.affectedFiles.length > 0 && (
                  <div>
                    <span className="font-medium">Affected Files:</span>
                    <ul className="mt-1 list-inside list-disc text-muted-foreground">
                      {investigationResult.analysis.affectedFiles.map(
                        (file) => (
                          <li key={file} className="text-xs font-mono">
                            {file}
                          </li>
                        ),
                      )}
                    </ul>
                  </div>
                )}
                <div className="flex items-center gap-2">
                  <span className="font-medium">Complexity:</span>
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs",
                      investigationResult.analysis.estimatedComplexity === "simple"
                        ? "bg-green-500/10 text-green-600"
                        : investigationResult.analysis.estimatedComplexity === "standard"
                          ? "bg-yellow-500/10 text-yellow-600"
                          : "bg-red-500/10 text-red-600",
                    )}
                  >
                    {investigationResult.analysis.estimatedComplexity}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center gap-3 border-t border-border pt-4">
            <button
              onClick={onInvestigate}
              className="flex items-center gap-2 rounded-md border border-border bg-secondary px-4 py-2 text-sm transition-colors hover:bg-secondary/80"
            >
              <Sparkles className="h-3.5 w-3.5" />
              Investigate
            </button>
            <button
              onClick={onCreateTask}
              className="flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm text-primary-foreground transition-colors hover:bg-primary/90"
            >
              <ArrowRight className="h-3.5 w-3.5" />
              {t("github.issues.createTask")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
