"use client";

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { CheckCircle2, XCircle, Loader2, MessageSquare } from "lucide-react";
import { Button, Textarea } from "@auto-claude/ui";
import type { Task } from "@auto-claude/types";

interface TaskReviewProps {
  task: Task;
  onApprove?: (feedback: string) => void;
  onReject?: (feedback: string) => void;
  isSubmitting?: boolean;
}

export function TaskReview({
  task,
  onApprove,
  onReject,
  isSubmitting = false,
}: TaskReviewProps) {
  const { t } = useTranslation(["kanban"]);
  const [feedback, setFeedback] = useState("");

  if (task.status !== "human_review") return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-medium">
        <MessageSquare className="h-4 w-4" />
        {t("kanban:detail.reviewFeedback", "Review Feedback")}
      </div>

      {task.reviewReason && (
        <div className="rounded-md border border-border bg-muted/30 p-3">
          <p className="text-xs text-muted-foreground">
            {t("kanban:detail.reviewReason", "Reason:")}
            {" "}
            <span className="font-medium text-foreground">
              {t(`kanban:card.review.${task.reviewReason}`, task.reviewReason)}
            </span>
          </p>
        </div>
      )}

      <Textarea
        placeholder={t(
          "kanban:detail.feedbackPlaceholder",
          "Provide feedback for the AI agent...",
        )}
        value={feedback}
        onChange={(e) => setFeedback(e.target.value)}
        rows={4}
        className="resize-none"
      />

      <div className="flex gap-2">
        {onApprove && (
          <Button
            onClick={() => onApprove(feedback)}
            disabled={isSubmitting}
            size="sm"
            className="gap-1.5"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <CheckCircle2 className="h-4 w-4" />
            )}
            {t("kanban:detail.approve", "Approve")}
          </Button>
        )}
        {onReject && (
          <Button
            onClick={() => onReject(feedback)}
            disabled={isSubmitting || (!feedback.trim())}
            variant="outline"
            size="sm"
            className="gap-1.5"
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            {t("kanban:detail.reject", "Reject")}
          </Button>
        )}
      </div>
    </div>
  );
}
