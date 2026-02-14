"use client";

/**
 * FileExplorerPanel - File tree browser panel
 *
 * Wraps the FileTree component with a header, refresh button, and loading states.
 * Uses the useFileExplorer hook for data fetching.
 */

import { useCallback, useState } from "react";
import { FolderTree, RefreshCw } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import { Button } from "@auto-claude/ui/primitives/button";
import { ScrollArea } from "@auto-claude/ui/primitives/scroll-area";
import { useFileExplorer } from "@/hooks/useFileExplorer";
import type { FileNode } from "@/hooks/useFileExplorer";
import { FileTree } from "./FileTree";

interface FileExplorerPanelProps {
  projectId: string | null;
  onFileSelect?: (node: FileNode) => void;
  className?: string;
}

export function FileExplorerPanel({
  projectId,
  onFileSelect,
  className,
}: FileExplorerPanelProps) {
  const { t } = useTranslation("common");
  const { tree, expandedPaths, isLoading, error, toggle, refresh } = useFileExplorer(projectId);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await refresh();
    } finally {
      setIsRefreshing(false);
    }
  }, [refresh]);

  const handleSelect = useCallback(
    (node: FileNode) => {
      setSelectedPath(node.path);
      onFileSelect?.(node);
    },
    [onFileSelect],
  );

  return (
    <div className={cn("flex h-full flex-col", className)}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-3 py-2">
        <div className="flex items-center gap-2 text-sm font-medium text-foreground">
          <FolderTree className="h-4 w-4 text-muted-foreground" />
          {t("labels.files", "Files")}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          disabled={isRefreshing || isLoading}
          className="h-6 w-6 p-0"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", (isRefreshing || isLoading) && "animate-spin")} />
        </Button>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {error ? (
            <div className="flex flex-col items-center gap-2 py-4 text-xs text-destructive">
              <span>{error}</span>
              <Button variant="ghost" size="sm" onClick={handleRefresh}>
                {t("buttons.retry")}
              </Button>
            </div>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              {t("labels.loading")}
            </div>
          ) : !projectId ? (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              {t("labels.noProjectSelected", "No project selected")}
            </div>
          ) : (
            <FileTree
              nodes={tree}
              expandedPaths={expandedPaths}
              onToggle={toggle}
              onSelect={handleSelect}
              selectedPath={selectedPath}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
