import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { apiClient } from "@/lib/data";

/**
 * Web app settings — a subset of Electron AppSettings relevant to the web UI.
 * Additional Electron-specific fields (pythonPath, gitPath, etc.) are omitted
 * as they don't apply in a browser context.
 */
export interface WebAppSettings {
  // Appearance
  theme: "light" | "dark" | "system";
  colorTheme?: string;
  uiScale?: number;
  sidebarCollapsed?: boolean;

  // Language
  language?: string;

  // Agent configuration
  defaultModel?: string;
  selectedAgentProfile?: string;

  // Onboarding
  onboardingCompleted?: boolean;

  // Logging
  logOrder?: "chronological" | "reverse-chronological";
}

const DEFAULT_SETTINGS: WebAppSettings = {
  theme: "system",
  sidebarCollapsed: false,
  onboardingCompleted: false,
  logOrder: "chronological",
};

interface SettingsState {
  settings: WebAppSettings;
  isLoading: boolean;
  error: string | null;
  _hasHydrated: boolean;

  // Actions
  setSettings: (settings: WebAppSettings) => void;
  updateSettings: (updates: Partial<WebAppSettings>) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setHasHydrated: (hydrated: boolean) => void;
}

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      settings: DEFAULT_SETTINGS,
      isLoading: true,
      error: null,
      _hasHydrated: false,

      setSettings: (settings) => set({ settings }),

      updateSettings: (updates) =>
        set((state) => ({
          settings: { ...state.settings, ...updates },
        })),

      setLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      setHasHydrated: (hydrated) => set({ _hasHydrated: hydrated }),
    }),
    {
      name: "auto-claude-settings",
      storage: createJSONStorage(() => localStorage),
      skipHydration: true,
      partialState: (state: SettingsState) => ({
        settings: state.settings,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    } as Parameters<typeof persist<SettingsState>>[1],
  ),
);

/** Hydrate settings store from localStorage (call once on app init) */
export function hydrateSettings() {
  useSettingsStore.persist.rehydrate();
}

/** Load settings from API and merge with local cache */
export async function loadSettings() {
  useSettingsStore.setState({ isLoading: true, error: null });
  try {
    const result = await apiClient.getSettings();
    const remoteSettings = result.settings as Partial<WebAppSettings>;
    useSettingsStore.setState((state) => ({
      settings: { ...DEFAULT_SETTINGS, ...state.settings, ...remoteSettings },
      isLoading: false,
    }));
  } catch {
    // Use local/default settings if API not available
    useSettingsStore.setState({ isLoading: false });
  }
}

/** Save settings updates to both local store and API */
export async function saveSettings(updates: Partial<WebAppSettings>) {
  useSettingsStore.getState().updateSettings(updates);
  try {
    await apiClient.saveSettings(updates);
  } catch {
    // Settings saved locally even if API fails
  }
}
