import { create } from "zustand";

/**
 * Auth failure info for the web app.
 */
export interface AuthFailureInfo {
  profileId: string;
  error: string;
  timestamp: string;
  recoverable: boolean;
}

interface AuthFailureState {
  // Auth failure modal state
  isModalOpen: boolean;
  authFailureInfo: AuthFailureInfo | null;

  // Track pending auth failures for sidebar indicator
  hasPendingAuthFailure: boolean;

  // Actions
  showAuthFailureModal: (info: AuthFailureInfo) => void;
  hideAuthFailureModal: () => void;
  clearAuthFailure: () => void;
}

export const useAuthFailureStore = create<AuthFailureState>((set) => ({
  isModalOpen: false,
  authFailureInfo: null,
  hasPendingAuthFailure: false,

  showAuthFailureModal: (info: AuthFailureInfo) => {
    set({
      isModalOpen: true,
      authFailureInfo: info,
      hasPendingAuthFailure: true,
    });
  },

  hideAuthFailureModal: () => {
    set({ isModalOpen: false });
  },

  clearAuthFailure: () => {
    set({
      isModalOpen: false,
      authFailureInfo: null,
      hasPendingAuthFailure: false,
    });
  },
}));
