"use client";

import { useState, useCallback } from "react";
import {
  Github,
  Key,
  Loader2,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  Input,
  Label,
  Button,
} from "@auto-claude/ui";
import { useTranslation } from "react-i18next";
import { apiClient } from "@/lib/data";

interface GitHubSetupModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onComplete: (settings: {
    githubToken: string;
    githubRepo: string;
  }) => void;
}

type SetupStep = "auth" | "repo" | "complete";

/**
 * GitHub Setup Modal for Web
 *
 * Adapted from the Electron version to use web-based OAuth redirect flow
 * instead of Electron IPC-based gh CLI flow.
 *
 * Flow:
 * 1. Authenticate with GitHub (redirect-based OAuth or PAT entry)
 * 2. Enter repository name
 * 3. Complete setup
 */
export function GitHubSetupModal({
  open,
  onOpenChange,
  projectId,
  onComplete,
}: GitHubSetupModalProps) {
  const { t } = useTranslation("integrations");
  const [step, setStep] = useState<SetupStep>("auth");
  const [authMethod, setAuthMethod] = useState<"oauth" | "pat" | null>(null);
  const [token, setToken] = useState("");
  const [repoName, setRepoName] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleOAuthStart = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const result = await apiClient.getGitHubOAuthUrl(projectId);
      if (result.url) {
        // Open OAuth URL in new window for redirect-based flow
        window.open(result.url, "_blank", "noopener,noreferrer");
        setAuthMethod("oauth");
      } else {
        setError("Failed to get OAuth URL from server");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start OAuth");
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  const handlePATSubmit = useCallback(() => {
    if (!token.trim()) {
      setError("Please enter a valid token");
      return;
    }
    setError(null);
    setStep("repo");
  }, [token]);

  const handleRepoSubmit = useCallback(() => {
    if (!repoName.trim()) {
      setError("Please enter a repository name (owner/repo)");
      return;
    }
    if (!repoName.includes("/")) {
      setError("Repository must be in format: owner/repo");
      return;
    }
    setError(null);
    setStep("complete");
    onComplete({ githubToken: token, githubRepo: repoName });
    onOpenChange(false);
  }, [repoName, token, onComplete, onOpenChange]);

  const handleReset = useCallback(() => {
    setStep("auth");
    setAuthMethod(null);
    setToken("");
    setRepoName("");
    setError(null);
  }, []);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Github className="h-5 w-5" />
            {t("github.issues.configure")}
          </DialogTitle>
          <DialogDescription>
            Connect your GitHub repository to sync issues and enable AI investigation.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Step indicator */}
          <div className="flex items-center gap-2">
            <StepIndicator
              label="Auth"
              active={step === "auth"}
              completed={step === "repo" || step === "complete"}
            />
            <div className="h-px flex-1 bg-border" />
            <StepIndicator
              label="Repo"
              active={step === "repo"}
              completed={step === "complete"}
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
              <AlertCircle className="h-4 w-4 shrink-0" />
              {error}
            </div>
          )}

          {/* Auth Step */}
          {step === "auth" && !authMethod && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Choose how to authenticate with GitHub:
              </p>
              <button
                onClick={handleOAuthStart}
                disabled={isLoading}
                className="flex w-full items-center gap-3 rounded-md border border-border p-3 text-left transition-colors hover:bg-accent"
              >
                {isLoading ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Github className="h-5 w-5" />
                )}
                <div>
                  <p className="text-sm font-medium">GitHub OAuth</p>
                  <p className="text-xs text-muted-foreground">
                    Sign in with your GitHub account
                  </p>
                </div>
                <ExternalLink className="ml-auto h-4 w-4 text-muted-foreground" />
              </button>
              <button
                onClick={() => setAuthMethod("pat")}
                className="flex w-full items-center gap-3 rounded-md border border-border p-3 text-left transition-colors hover:bg-accent"
              >
                <Key className="h-5 w-5" />
                <div>
                  <p className="text-sm font-medium">Personal Access Token</p>
                  <p className="text-xs text-muted-foreground">
                    Use a GitHub PAT with repo scope
                  </p>
                </div>
              </button>
            </div>
          )}

          {/* PAT Entry */}
          {step === "auth" && authMethod === "pat" && (
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="github-pat">Personal Access Token</Label>
                <Input
                  id="github-pat"
                  type="password"
                  placeholder="ghp_..."
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handlePATSubmit()}
                />
                <p className="text-xs text-muted-foreground">
                  Create a token at{" "}
                  <a
                    href="https://github.com/settings/tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary underline"
                  >
                    GitHub Settings
                  </a>{" "}
                  with <code className="text-[10px]">repo</code> scope.
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setAuthMethod(null)}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button onClick={handlePATSubmit} className="flex-1">
                  Continue
                </Button>
              </div>
            </div>
          )}

          {/* OAuth waiting */}
          {step === "auth" && authMethod === "oauth" && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Complete the OAuth flow in the browser window that opened.
                Once authenticated, enter your token below.
              </p>
              <div className="space-y-2">
                <Label htmlFor="oauth-token">Token from OAuth</Label>
                <Input
                  id="oauth-token"
                  type="password"
                  placeholder="Paste token here..."
                  value={token}
                  onChange={(e) => setToken(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handlePATSubmit()}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={handleReset}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button onClick={handlePATSubmit} className="flex-1">
                  Continue
                </Button>
              </div>
            </div>
          )}

          {/* Repo Step */}
          {step === "repo" && (
            <div className="space-y-3">
              <div className="space-y-2">
                <Label htmlFor="github-repo">Repository</Label>
                <Input
                  id="github-repo"
                  placeholder="owner/repository"
                  value={repoName}
                  onChange={(e) => setRepoName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleRepoSubmit()}
                />
                <p className="text-xs text-muted-foreground">
                  Enter the full repository name, e.g.{" "}
                  <code className="text-[10px]">octocat/hello-world</code>
                </p>
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => setStep("auth")}
                  className="flex-1"
                >
                  Back
                </Button>
                <Button onClick={handleRepoSubmit} className="flex-1">
                  Connect
                </Button>
              </div>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function StepIndicator({
  label,
  active,
  completed,
}: {
  label: string;
  active: boolean;
  completed: boolean;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-medium ${
          completed
            ? "bg-green-500/10 text-green-600"
            : active
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-muted-foreground"
        }`}
      >
        {completed ? <CheckCircle2 className="h-3.5 w-3.5" /> : label[0]}
      </div>
      <span
        className={`text-xs ${active ? "font-medium" : "text-muted-foreground"}`}
      >
        {label}
      </span>
    </div>
  );
}
