import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

export interface TerminalFontSettings {
  fontFamily: string[];
  fontSize: number;
  fontWeight: number;
  lineHeight: number;
  letterSpacing: number;
  cursorStyle: "block" | "underline" | "bar";
  cursorBlink: boolean;
  cursorAccentColor: string;
  scrollback: number;
}

const WEB_DEFAULTS: TerminalFontSettings = {
  fontFamily: ["SF Mono", "Menlo", "Consolas", "monospace"],
  fontSize: 14,
  fontWeight: 400,
  lineHeight: 1.2,
  letterSpacing: 0,
  cursorStyle: "block",
  cursorBlink: true,
  cursorAccentColor: "#000000",
  scrollback: 10000,
};

/** Preset configurations for popular terminals */
export const TERMINAL_PRESETS: Record<string, TerminalFontSettings> = {
  vscode: {
    fontFamily: ["Consolas", "Courier New", "monospace"],
    fontSize: 14,
    fontWeight: 400,
    lineHeight: 1.2,
    letterSpacing: 0,
    cursorStyle: "block",
    cursorBlink: true,
    cursorAccentColor: "#000000",
    scrollback: 10000,
  },
  intellij: {
    fontFamily: ["JetBrains Mono", "Consolas", "monospace"],
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.2,
    letterSpacing: 0,
    cursorStyle: "block",
    cursorBlink: true,
    cursorAccentColor: "#000000",
    scrollback: 10000,
  },
  macos: {
    fontFamily: ["SF Mono", "Menlo", "Monaco", "monospace"],
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.2,
    letterSpacing: 0,
    cursorStyle: "block",
    cursorBlink: true,
    cursorAccentColor: "#000000",
    scrollback: 10000,
  },
  ubuntu: {
    fontFamily: ["Ubuntu Mono", "monospace"],
    fontSize: 13,
    fontWeight: 400,
    lineHeight: 1.2,
    letterSpacing: 0,
    cursorStyle: "block",
    cursorBlink: true,
    cursorAccentColor: "#ffffff",
    scrollback: 10000,
  },
};

// Validation helpers
function isValidFontSize(size: number): boolean {
  return typeof size === "number" && size >= 8 && size <= 32;
}
function isValidFontWeight(weight: number): boolean {
  return typeof weight === "number" && weight >= 100 && weight <= 900;
}
function isValidLineHeight(height: number): boolean {
  return typeof height === "number" && height >= 0.8 && height <= 2.0;
}
function isValidLetterSpacing(spacing: number): boolean {
  return typeof spacing === "number" && spacing >= -2 && spacing <= 5;
}
function isValidScrollback(scrollback: number): boolean {
  return typeof scrollback === "number" && scrollback >= 0 && scrollback <= 100000;
}
function isValidCursorStyle(
  style: string,
): style is "block" | "underline" | "bar" {
  return ["block", "underline", "bar"].includes(style);
}
function isValidHexColor(color: string): boolean {
  return typeof color === "string" && /^#[0-9a-fA-F]{6}$/.test(color);
}
function isValidFontFamily(fonts: unknown): fonts is string[] {
  return (
    Array.isArray(fonts) &&
    fonts.length > 0 &&
    fonts.every((f) => typeof f === "string" && f.length > 0)
  );
}

interface TerminalFontSettingsStore extends TerminalFontSettings {
  setFontFamily: (fonts: string[]) => void;
  setFontSize: (size: number) => void;
  setFontWeight: (weight: number) => void;
  setLineHeight: (height: number) => void;
  setLetterSpacing: (spacing: number) => void;
  setCursorStyle: (style: "block" | "underline" | "bar") => void;
  setCursorBlink: (blink: boolean) => void;
  setCursorAccentColor: (color: string) => void;
  setScrollback: (scrollback: number) => void;
  applyPreset: (presetName: string) => boolean;
  resetToDefaults: () => void;
  applySettings: (settings: Partial<TerminalFontSettings>) => boolean;
  exportSettings: () => string;
  importSettings: (json: string) => boolean;
}

export const useTerminalFontSettingsStore =
  create<TerminalFontSettingsStore>()(
    persist(
      (set, get) => ({
        ...WEB_DEFAULTS,

        setFontFamily: (fontFamily) => {
          if (isValidFontFamily(fontFamily)) set({ fontFamily });
        },
        setFontSize: (fontSize) => {
          if (isValidFontSize(fontSize)) set({ fontSize });
        },
        setFontWeight: (fontWeight) => {
          if (isValidFontWeight(fontWeight)) set({ fontWeight });
        },
        setLineHeight: (lineHeight) => {
          if (isValidLineHeight(lineHeight)) set({ lineHeight });
        },
        setLetterSpacing: (letterSpacing) => {
          if (isValidLetterSpacing(letterSpacing)) set({ letterSpacing });
        },
        setCursorStyle: (cursorStyle) => {
          if (isValidCursorStyle(cursorStyle)) set({ cursorStyle });
        },
        setCursorBlink: (cursorBlink) => set({ cursorBlink }),
        setCursorAccentColor: (cursorAccentColor) => {
          if (isValidHexColor(cursorAccentColor)) set({ cursorAccentColor });
        },
        setScrollback: (scrollback) => {
          if (isValidScrollback(scrollback)) set({ scrollback });
        },

        applyPreset: (presetName) => {
          const preset = TERMINAL_PRESETS[presetName];
          if (preset) {
            set(preset);
            return true;
          }
          return false;
        },

        resetToDefaults: () => set(WEB_DEFAULTS),

        applySettings: (settings) => {
          if (
            settings.fontFamily !== undefined &&
            !isValidFontFamily(settings.fontFamily)
          )
            return false;
          if (
            settings.fontSize !== undefined &&
            !isValidFontSize(settings.fontSize)
          )
            return false;
          if (
            settings.fontWeight !== undefined &&
            !isValidFontWeight(settings.fontWeight)
          )
            return false;
          if (
            settings.lineHeight !== undefined &&
            !isValidLineHeight(settings.lineHeight)
          )
            return false;
          if (
            settings.letterSpacing !== undefined &&
            !isValidLetterSpacing(settings.letterSpacing)
          )
            return false;
          if (
            settings.scrollback !== undefined &&
            !isValidScrollback(settings.scrollback)
          )
            return false;
          if (
            settings.cursorStyle !== undefined &&
            !isValidCursorStyle(settings.cursorStyle)
          )
            return false;
          if (
            settings.cursorAccentColor !== undefined &&
            !isValidHexColor(settings.cursorAccentColor)
          )
            return false;
          set((state) => ({ ...state, ...settings }));
          return true;
        },

        exportSettings: () => {
          const s = get();
          return JSON.stringify(
            {
              fontFamily: s.fontFamily,
              fontSize: s.fontSize,
              fontWeight: s.fontWeight,
              lineHeight: s.lineHeight,
              letterSpacing: s.letterSpacing,
              cursorStyle: s.cursorStyle,
              cursorBlink: s.cursorBlink,
              cursorAccentColor: s.cursorAccentColor,
              scrollback: s.scrollback,
            },
            null,
            2,
          );
        },

        importSettings: (json) => {
          try {
            const parsed = JSON.parse(json);
            if (typeof parsed !== "object" || parsed === null) return false;
            return get().applySettings(parsed);
          } catch {
            return false;
          }
        },
      }),
      {
        name: "terminal-font-settings",
        storage: createJSONStorage(() => localStorage),
        skipHydration: true,
      },
    ),
  );
