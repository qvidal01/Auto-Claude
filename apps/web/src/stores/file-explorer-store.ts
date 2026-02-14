import { create } from "zustand";

// Types matching Electron field names
export interface FileNode {
  name: string;
  path: string;
  isDirectory: boolean;
  size?: number;
  children?: FileNode[];
}

interface FileExplorerState {
  isOpen: boolean;
  expandedFolders: Set<string>;
  files: Map<string, FileNode[]>;
  isLoading: Map<string, boolean>;
  error: string | null;

  // Actions
  toggle: () => void;
  open: () => void;
  close: () => void;
  toggleFolder: (path: string) => void;
  expandFolder: (path: string) => void;
  collapseFolder: (path: string) => void;
  setFiles: (dirPath: string, nodes: FileNode[]) => void;
  setLoadingDir: (dirPath: string, loading: boolean) => void;
  setError: (error: string | null) => void;
  clearCache: () => void;

  // Selectors
  isExpanded: (path: string) => boolean;
  getFiles: (dirPath: string) => FileNode[] | undefined;
  isLoadingDir: (dirPath: string) => boolean;
  getVisibleFiles: (rootPath: string) => FileNode[];
  computeVisibleItems: (
    rootPath: string,
  ) => { nodes: FileNode[]; count: number };
}

export const useFileExplorerStore = create<FileExplorerState>((set, get) => ({
  isOpen: false,
  expandedFolders: new Set(),
  files: new Map(),
  isLoading: new Map(),
  error: null,

  toggle: () => set((state) => ({ isOpen: !state.isOpen })),
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),

  toggleFolder: (path) => {
    set((state) => {
      const newExpanded = new Set(state.expandedFolders);
      if (newExpanded.has(path)) {
        newExpanded.delete(path);
      } else {
        newExpanded.add(path);
      }
      return { expandedFolders: newExpanded };
    });
  },

  expandFolder: (path) => {
    set((state) => {
      const newExpanded = new Set(state.expandedFolders);
      newExpanded.add(path);
      return { expandedFolders: newExpanded };
    });
  },

  collapseFolder: (path) => {
    set((state) => {
      const newExpanded = new Set(state.expandedFolders);
      newExpanded.delete(path);
      return { expandedFolders: newExpanded };
    });
  },

  setFiles: (dirPath, nodes) => {
    set((state) => {
      const newFiles = new Map(state.files);
      newFiles.set(dirPath, nodes);
      return { files: newFiles };
    });
  },

  setLoadingDir: (dirPath, loading) => {
    set((state) => {
      const newLoading = new Map(state.isLoading);
      newLoading.set(dirPath, loading);
      return { isLoading: newLoading };
    });
  },

  setError: (error) => set({ error }),

  clearCache: () =>
    set({ files: new Map(), expandedFolders: new Set() }),

  isExpanded: (path) => get().expandedFolders.has(path),
  getFiles: (dirPath) => get().files.get(dirPath),
  isLoadingDir: (dirPath) => get().isLoading.get(dirPath) ?? false,

  getVisibleFiles: (rootPath) => {
    const state = get();
    const result: FileNode[] = [];

    const collect = (dirPath: string): void => {
      const nodes = state.files.get(dirPath);
      if (!nodes) return;
      for (const node of nodes) {
        result.push(node);
        if (node.isDirectory && state.expandedFolders.has(node.path)) {
          collect(node.path);
        }
      }
    };

    collect(rootPath);
    return result;
  },

  computeVisibleItems: (rootPath) => {
    const nodes = get().getVisibleFiles(rootPath);
    return { nodes, count: nodes.length };
  },
}));
