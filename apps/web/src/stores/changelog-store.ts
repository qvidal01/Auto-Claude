import { create } from "zustand";

// Types matching Electron field names
export type ChangelogFormat = "keep-a-changelog" | "conventional" | "custom";
export type ChangelogAudience = "user-facing" | "developer" | "all";
export type ChangelogEmojiLevel = "none" | "minimal" | "full";
export type ChangelogSourceMode = "tasks" | "git-history" | "branch-diff";

export interface ChangelogTask {
  id: string;
  title: string;
  specNumber: string;
  status: string;
}

export interface TaskSpecContent {
  specNumber: string;
  title: string;
  content: string;
}

export interface ExistingChangelog {
  content: string;
  lastVersion?: string;
  path: string;
}

export interface GitBranchInfo {
  name: string;
  isCurrent: boolean;
  isRemote: boolean;
}

export interface GitTagInfo {
  name: string;
  date?: string;
}

export interface GitCommit {
  hash: string;
  message: string;
  author: string;
  date: string;
}

export interface ChangelogGenerationProgress {
  phase: "idle" | "loading" | "generating" | "complete" | "error";
  progress: number;
  message: string;
}

interface ChangelogState {
  // Data
  doneTasks: ChangelogTask[];
  selectedTaskIds: string[];
  loadedSpecs: TaskSpecContent[];
  existingChangelog: ExistingChangelog | null;

  // Source mode
  sourceMode: ChangelogSourceMode;

  // Git data
  branches: GitBranchInfo[];
  tags: GitTagInfo[];
  currentBranch: string;
  defaultBranch: string;
  previewCommits: GitCommit[];
  isLoadingGitData: boolean;
  isLoadingCommits: boolean;

  // Git history options
  gitHistoryType: "recent" | "since-date" | "tag-range" | "since-version";
  gitHistoryCount: number;
  gitHistorySinceDate: string;
  gitHistoryFromTag: string;
  gitHistoryToTag: string;
  gitHistorySinceVersion: string;
  includeMergeCommits: boolean;

  // Branch diff options
  baseBranch: string;
  compareBranch: string;

  // Generation config
  version: string;
  date: string;
  format: ChangelogFormat;
  audience: ChangelogAudience;
  emojiLevel: ChangelogEmojiLevel;
  customInstructions: string;

  // Generation state
  generationProgress: ChangelogGenerationProgress | null;
  generatedChangelog: string;
  isGenerating: boolean;
  error: string | null;

  // Actions
  setDoneTasks: (tasks: ChangelogTask[]) => void;
  setSelectedTaskIds: (ids: string[]) => void;
  toggleTaskSelection: (taskId: string) => void;
  selectAllTasks: () => void;
  deselectAllTasks: () => void;
  setLoadedSpecs: (specs: TaskSpecContent[]) => void;
  setExistingChangelog: (changelog: ExistingChangelog | null) => void;
  setSourceMode: (mode: ChangelogSourceMode) => void;
  setBranches: (branches: GitBranchInfo[]) => void;
  setTags: (tags: GitTagInfo[]) => void;
  setCurrentBranch: (branch: string) => void;
  setDefaultBranch: (branch: string) => void;
  setPreviewCommits: (commits: GitCommit[]) => void;
  setIsLoadingGitData: (loading: boolean) => void;
  setIsLoadingCommits: (loading: boolean) => void;
  setGitHistoryType: (
    type: "recent" | "since-date" | "tag-range" | "since-version",
  ) => void;
  setGitHistoryCount: (count: number) => void;
  setGitHistorySinceDate: (date: string) => void;
  setGitHistoryFromTag: (tag: string) => void;
  setGitHistoryToTag: (tag: string) => void;
  setGitHistorySinceVersion: (version: string) => void;
  setIncludeMergeCommits: (include: boolean) => void;
  setBaseBranch: (branch: string) => void;
  setCompareBranch: (branch: string) => void;
  setVersion: (version: string) => void;
  setDate: (date: string) => void;
  setFormat: (format: ChangelogFormat) => void;
  setAudience: (audience: ChangelogAudience) => void;
  setEmojiLevel: (level: ChangelogEmojiLevel) => void;
  setCustomInstructions: (instructions: string) => void;
  setGenerationProgress: (progress: ChangelogGenerationProgress | null) => void;
  setGeneratedChangelog: (changelog: string) => void;
  setIsGenerating: (isGenerating: boolean) => void;
  setError: (error: string | null) => void;
  reset: () => void;
  updateGeneratedChangelog: (changelog: string) => void;
}

const getDefaultDate = (): string => {
  return new Date().toISOString().split("T")[0];
};

const initialState = {
  doneTasks: [] as ChangelogTask[],
  selectedTaskIds: [] as string[],
  loadedSpecs: [] as TaskSpecContent[],
  existingChangelog: null as ExistingChangelog | null,
  sourceMode: "tasks" as ChangelogSourceMode,
  branches: [] as GitBranchInfo[],
  tags: [] as GitTagInfo[],
  currentBranch: "",
  defaultBranch: "main",
  previewCommits: [] as GitCommit[],
  isLoadingGitData: false,
  isLoadingCommits: false,
  gitHistoryType: "recent" as const,
  gitHistoryCount: 25,
  gitHistorySinceDate: "",
  gitHistoryFromTag: "",
  gitHistoryToTag: "",
  gitHistorySinceVersion: "",
  includeMergeCommits: false,
  baseBranch: "",
  compareBranch: "",
  version: "1.0.0",
  date: getDefaultDate(),
  format: "keep-a-changelog" as ChangelogFormat,
  audience: "user-facing" as ChangelogAudience,
  emojiLevel: "none" as ChangelogEmojiLevel,
  customInstructions: "",
  generationProgress: null as ChangelogGenerationProgress | null,
  generatedChangelog: "",
  isGenerating: false,
  error: null as string | null,
};

export const useChangelogStore = create<ChangelogState>((set, get) => ({
  ...initialState,

  setDoneTasks: (tasks) => set({ doneTasks: tasks }),
  setSelectedTaskIds: (ids) => set({ selectedTaskIds: ids }),

  toggleTaskSelection: (taskId) =>
    set((state) => ({
      selectedTaskIds: state.selectedTaskIds.includes(taskId)
        ? state.selectedTaskIds.filter((id) => id !== taskId)
        : [...state.selectedTaskIds, taskId],
    })),

  selectAllTasks: () =>
    set((state) => ({
      selectedTaskIds: state.doneTasks.map((task) => task.id),
    })),

  deselectAllTasks: () => set({ selectedTaskIds: [] }),
  setLoadedSpecs: (specs) => set({ loadedSpecs: specs }),
  setExistingChangelog: (changelog) => set({ existingChangelog: changelog }),
  setSourceMode: (mode) => set({ sourceMode: mode }),
  setBranches: (branches) => set({ branches }),
  setTags: (tags) => set({ tags }),
  setCurrentBranch: (branch) => set({ currentBranch: branch }),
  setDefaultBranch: (branch) => set({ defaultBranch: branch }),
  setPreviewCommits: (commits) => set({ previewCommits: commits }),
  setIsLoadingGitData: (loading) => set({ isLoadingGitData: loading }),
  setIsLoadingCommits: (loading) => set({ isLoadingCommits: loading }),
  setGitHistoryType: (type) => set({ gitHistoryType: type }),
  setGitHistoryCount: (count) => set({ gitHistoryCount: count }),
  setGitHistorySinceDate: (date) => set({ gitHistorySinceDate: date }),
  setGitHistoryFromTag: (tag) => set({ gitHistoryFromTag: tag }),
  setGitHistoryToTag: (tag) => set({ gitHistoryToTag: tag }),
  setGitHistorySinceVersion: (version) =>
    set({ gitHistorySinceVersion: version }),
  setIncludeMergeCommits: (include) => set({ includeMergeCommits: include }),
  setBaseBranch: (branch) => set({ baseBranch: branch }),
  setCompareBranch: (branch) => set({ compareBranch: branch }),
  setVersion: (version) => set({ version }),
  setDate: (date) => set({ date }),
  setFormat: (format) => set({ format }),
  setAudience: (audience) => set({ audience }),
  setEmojiLevel: (level) => set({ emojiLevel: level }),
  setCustomInstructions: (instructions) =>
    set({ customInstructions: instructions }),
  setGenerationProgress: (progress) => set({ generationProgress: progress }),
  setGeneratedChangelog: (changelog) =>
    set({ generatedChangelog: changelog }),
  setIsGenerating: (isGenerating) => set({ isGenerating }),
  setError: (error) => set({ error }),

  reset: () => set({ ...initialState, date: getDefaultDate() }),

  updateGeneratedChangelog: (changelog) =>
    set({ generatedChangelog: changelog }),
}));
