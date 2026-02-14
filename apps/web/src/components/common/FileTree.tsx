"use client";

/**
 * FileTree - Recursive file tree rendering component
 *
 * Renders a tree of files/directories with expand/collapse support.
 * Uses the FileNode type from useFileExplorer hook.
 */

import { memo } from "react";
import { ChevronRight, File, Folder, FolderOpen, Loader2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { cn } from "@auto-claude/ui/utils";
import type { FileNode } from "@/hooks/useFileExplorer";

interface FileTreeProps {
  nodes: FileNode[];
  expandedPaths: Set<string>;
  onToggle: (path: string) => Promise<void>;
  onSelect?: (node: FileNode) => void;
  selectedPath?: string | null;
  depth?: number;
  className?: string;
}

export const FileTree = memo(function FileTree({
  nodes,
  expandedPaths,
  onToggle,
  onSelect,
  selectedPath,
  depth = 0,
  className,
}: FileTreeProps) {
  const { t } = useTranslation("common");

  if (nodes.length === 0 && depth === 0) {
    return (
      <div className="flex items-center justify-center py-4 text-xs text-muted-foreground">
        {t("labels.noFiles", "No files")}
      </div>
    );
  }

  return (
    <div className={cn("text-sm", className)} role="tree">
      {nodes.map((node) => {
        const isExpanded = expandedPaths.has(node.path);
        const isSelected = selectedPath === node.path;

        return (
          <div key={node.path} role="treeitem" aria-expanded={node.isDirectory ? isExpanded : undefined}>
            <button
              type="button"
              className={cn(
                "flex w-full items-center gap-1 rounded-sm px-1 py-0.5 text-left hover:bg-accent/50 transition-colors",
                isSelected && "bg-accent text-accent-foreground",
              )}
              style={{ paddingLeft: `${depth * 16 + 4}px` }}
              onClick={() => {
                if (node.isDirectory) {
                  onToggle(node.path);
                } else {
                  onSelect?.(node);
                }
              }}
            >
              {node.isDirectory ? (
                <>
                  <ChevronRight
                    className={cn(
                      "h-3 w-3 shrink-0 text-muted-foreground transition-transform",
                      isExpanded && "rotate-90",
                    )}
                  />
                  {isExpanded ? (
                    <FolderOpen className="h-4 w-4 shrink-0 text-amber-500" />
                  ) : (
                    <Folder className="h-4 w-4 shrink-0 text-amber-500" />
                  )}
                </>
              ) : (
                <>
                  <span className="h-3 w-3 shrink-0" />
                  <File className="h-4 w-4 shrink-0 text-muted-foreground" />
                </>
              )}
              <span className="truncate text-xs">{node.name}</span>
            </button>

            {/* Render children recursively */}
            {node.isDirectory && isExpanded && node.children && (
              <FileTree
                nodes={node.children}
                expandedPaths={expandedPaths}
                onToggle={onToggle}
                onSelect={onSelect}
                selectedPath={selectedPath}
                depth={depth + 1}
              />
            )}
          </div>
        );
      })}
    </div>
  );
});
