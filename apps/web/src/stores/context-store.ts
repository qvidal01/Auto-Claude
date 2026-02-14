import { create } from "zustand";

// Types matching Electron field names
export interface ProjectIndex {
  projectId: string;
  files: number;
  languages: string[];
  frameworks: string[];
  analyzedAt: Date;
}

export interface GraphitiMemoryStatus {
  enabled: boolean;
  connected: boolean;
  episodeCount: number;
}

export interface GraphitiMemoryState {
  isIndexing: boolean;
  lastIndexedAt?: Date;
  error?: string;
}

export interface MemoryEpisode {
  id: string;
  content: string;
  type: string;
  createdAt: Date;
}

export interface ContextSearchResult {
  id: string;
  content: string;
  score: number;
  type: string;
}

interface ContextState {
  // Project Index
  projectIndex: ProjectIndex | null;
  indexLoading: boolean;
  indexError: string | null;

  // Memory Status
  memoryStatus: GraphitiMemoryStatus | null;
  memoryState: GraphitiMemoryState | null;
  memoryLoading: boolean;
  memoryError: string | null;

  // Recent Memories
  recentMemories: MemoryEpisode[];
  memoriesLoading: boolean;

  // Search
  searchResults: ContextSearchResult[];
  searchLoading: boolean;
  searchQuery: string;

  // Actions
  setProjectIndex: (index: ProjectIndex | null) => void;
  setIndexLoading: (loading: boolean) => void;
  setIndexError: (error: string | null) => void;
  setMemoryStatus: (status: GraphitiMemoryStatus | null) => void;
  setMemoryState: (state: GraphitiMemoryState | null) => void;
  setMemoryLoading: (loading: boolean) => void;
  setMemoryError: (error: string | null) => void;
  setRecentMemories: (memories: MemoryEpisode[]) => void;
  setMemoriesLoading: (loading: boolean) => void;
  setSearchResults: (results: ContextSearchResult[]) => void;
  setSearchLoading: (loading: boolean) => void;
  setSearchQuery: (query: string) => void;
  clearAll: () => void;
}

export const useContextStore = create<ContextState>((set) => ({
  projectIndex: null,
  indexLoading: false,
  indexError: null,
  memoryStatus: null,
  memoryState: null,
  memoryLoading: false,
  memoryError: null,
  recentMemories: [],
  memoriesLoading: false,
  searchResults: [],
  searchLoading: false,
  searchQuery: "",

  setProjectIndex: (index) => set({ projectIndex: index }),
  setIndexLoading: (loading) => set({ indexLoading: loading }),
  setIndexError: (error) => set({ indexError: error }),
  setMemoryStatus: (status) => set({ memoryStatus: status }),
  setMemoryState: (state) => set({ memoryState: state }),
  setMemoryLoading: (loading) => set({ memoryLoading: loading }),
  setMemoryError: (error) => set({ memoryError: error }),
  setRecentMemories: (memories) => set({ recentMemories: memories }),
  setMemoriesLoading: (loading) => set({ memoriesLoading: loading }),
  setSearchResults: (results) => set({ searchResults: results }),
  setSearchLoading: (loading) => set({ searchLoading: loading }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  clearAll: () =>
    set({
      projectIndex: null,
      indexLoading: false,
      indexError: null,
      memoryStatus: null,
      memoryState: null,
      memoryLoading: false,
      memoryError: null,
      recentMemories: [],
      memoriesLoading: false,
      searchResults: [],
      searchLoading: false,
      searchQuery: "",
    }),
}));
