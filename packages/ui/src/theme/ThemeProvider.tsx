/* ─────────────────────────────────────────────────────────────
 *  Theme as CSS custom properties — switching costs zero renders.
 *
 *  A theme is a typed object; applying it writes `--c-<key>` onto
 *  <html>. Components never read the palette object, they use
 *  `v("ink")` (a typo is a compile error) or `var(--c-ink)` in CSS
 *  Modules. Nothing re-renders on a switch: no context value changes,
 *  the browser repaints from the new variable values. Only components
 *  that call `useTheme()` (a settings screen) re-render.
 *
 *  colorScheme (native controls, scrollbars) and <meta theme-color>
 *  (Android status bar) are written in the same call, so they never
 *  lag one step behind the palette.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { DEFAULT_THEME, THEMES, type Palette, type ThemeId } from "./palettes";

export type ThemeMode = ThemeId | "system";

/** `v("accent")` → `"var(--c-accent)"`, type-checked against Palette. */
export function v(key: keyof Palette): string {
  return `var(--c-${key})`;
}

const MODE_KEY = "gz-theme-mode";
const GEN_KEY = "gz-theme-gen";

/**
 * Default generation. Bump it when the app's *default* theme changes.
 *
 * The chosen mode lives in localStorage, so without this every phone
 * that already opened the app stays pinned to the old default and "the
 * new default" only reaches clean installs. Bumping moves every device
 * to the new default once; after that the user's own choice is
 * respected again.
 */
export const THEME_GENERATION = "1";

const DARK_QUERY = "(prefers-color-scheme: dark)";

/* ── storage (never throws: private mode / disabled storage) ── */

function readStored(): ThemeMode | null {
  try {
    if (localStorage.getItem(GEN_KEY) !== THEME_GENERATION) {
      localStorage.setItem(GEN_KEY, THEME_GENERATION);
      localStorage.removeItem(MODE_KEY);
      return null;
    }
    const m = localStorage.getItem(MODE_KEY);
    return m === "day" || m === "night" || m === "system" ? m : null;
  } catch {
    return null;
  }
}

function writeStored(mode: ThemeMode): void {
  try {
    localStorage.setItem(MODE_KEY, mode);
    localStorage.setItem(GEN_KEY, THEME_GENERATION);
  } catch {
    /* storage unavailable: the choice lasts for this session only */
  }
}

function systemPrefersDark(): boolean {
  return typeof matchMedia === "function" && matchMedia(DARK_QUERY).matches;
}

/* ── applying ── */

/** Write a theme onto <html>. Safe to call before React mounts. */
export function applyTheme(id: ThemeId): void {
  if (typeof document === "undefined") return;
  const t = THEMES[id];
  const root = document.documentElement;
  for (const [k, val] of Object.entries(t.p)) root.style.setProperty(`--c-${k}`, val);
  root.setAttribute("data-theme", id);
  root.style.colorScheme = t.dark ? "dark" : "light";

  let meta = document.querySelector<HTMLMetaElement>('meta[name="theme-color"]');
  if (!meta) {
    meta = document.createElement("meta");
    meta.name = "theme-color";
    document.head.appendChild(meta);
  }
  meta.content = t.p.bar;
}

/* ── module store: one source of truth, shaped for useSyncExternalStore ── */

type Snapshot = { mode: ThemeMode; theme: ThemeId };

let snapshot: Snapshot | null = null;
const listeners = new Set<() => void>();
let unwatchSystem: (() => void) | null = null;

function resolve(mode: ThemeMode): ThemeId {
  if (mode !== "system") return mode;
  return systemPrefersDark() ? "night" : "day";
}

function commit(mode: ThemeMode): void {
  const theme = resolve(mode);
  const prev = snapshot;
  if (!prev || prev.theme !== theme) applyTheme(theme);
  if (!prev || prev.mode !== mode || prev.theme !== theme) {
    snapshot = { mode, theme };
    for (const l of Array.from(listeners)) l();
  }
  syncSystemWatch(mode);
}

/* "system" follows the OS live: flipping dark mode in quick settings
   repaints the open app without a reload. Only installed while the
   mode is "system", so an explicit choice is never overridden. */
function syncSystemWatch(mode: ThemeMode): void {
  if (mode !== "system") {
    unwatchSystem?.();
    unwatchSystem = null;
    return;
  }
  if (unwatchSystem || typeof matchMedia !== "function") return;
  const mql = matchMedia(DARK_QUERY);
  const onChange = () => {
    if (snapshot?.mode === "system") commit("system");
  };
  mql.addEventListener("change", onChange);
  unwatchSystem = () => mql.removeEventListener("change", onChange);
}

/**
 * Run before the first render (in main.tsx, before createRoot) so the
 * first paint already has the right colours — no flash of day theme
 * on a night phone. Idempotent. Returns the mode in effect.
 *
 * The product default is the "day" brand theme, not the OS preference:
 * the theme is part of the program's identity, and a user who wants it
 * to follow the phone picks "system" in settings.
 */
export function bootTheme(fallback: ThemeMode = DEFAULT_THEME): ThemeMode {
  if (snapshot) return snapshot.mode;
  commit(readStored() ?? fallback);
  return snapshot!.mode;
}

/** Change the mode, persist it, repaint. */
export function setThemeMode(mode: ThemeMode): void {
  writeStored(mode);
  commit(mode);
}

/* A constant, not a fresh object: useSyncExternalStore treats a new
   identity on every call as a change and re-renders in a loop. */
const UNBOOTED: Snapshot = { mode: DEFAULT_THEME, theme: DEFAULT_THEME };

export function getThemeSnapshot(): Snapshot {
  return snapshot ?? UNBOOTED;
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => {
    listeners.delete(fn);
  };
}

/** Test/HMR isolation: forget the booted state and stop watching the OS. */
export function resetThemeForTests(): void {
  unwatchSystem?.();
  unwatchSystem = null;
  snapshot = null;
  listeners.clear();
}

/* ── React surface ── */

export type ThemeProviderProps = {
  /** Mode used when nothing is stored (and the generation was bumped). */
  defaultMode?: ThemeMode;
  /** Force a mode (e.g. the admin panel pinned to day). */
  mode?: ThemeMode;
  children?: React.ReactNode;
};

/**
 * Makes sure a theme is applied before paint and renders children as
 * is — it provides no context value, which is what keeps a theme
 * switch at zero renders for the tree below it.
 */
export function ThemeProvider({ defaultMode = DEFAULT_THEME, mode, children }: ThemeProviderProps) {
  // Layout effect: runs after commit but before paint, so an app that
  // forgot bootTheme() still never shows unthemed colours.
  React.useLayoutEffect(() => {
    bootTheme(defaultMode);
  }, [defaultMode]);

  React.useLayoutEffect(() => {
    if (mode) commit(mode);
  }, [mode]);

  return <>{children}</>;
}

export type UseTheme = {
  mode: ThemeMode;
  theme: ThemeId;
  dark: boolean;
  palette: Palette;
  setMode: (mode: ThemeMode) => void;
};

/** Current mode/theme for the few components that must know (settings, charts drawn in canvas). */
export function useTheme(): UseTheme {
  const snap = React.useSyncExternalStore(subscribe, getThemeSnapshot, getThemeSnapshot);
  return {
    mode: snap.mode,
    theme: snap.theme,
    dark: THEMES[snap.theme].dark,
    palette: THEMES[snap.theme].p,
    setMode: setThemeMode,
  };
}
