/* Session state as a tiny external store (no React).
 *
 * It lives outside React on purpose: the ApiClient is created before any
 * component renders and must be able to end the session from its
 * onSessionExpired callback — `createApiClient({ onSessionExpired: () =>
 * store.clearSession() })`. A React-state-only session could not be reached
 * from there. SessionProvider subscribes to it with useSyncExternalStore. */

import type { Permission } from "@gazyar/core";

export type SessionStatus = "loading" | "authenticated" | "anonymous";

export interface SessionSubject {
  type: "user" | "staff";
  id: number;
  /** Staff role ids (super_admin, operator, …). */
  roles?: string[];
  /** Staff permission strings as computed by the server (backend rbac.py). */
  permissions?: string[];
}

export interface SessionState {
  status: SessionStatus;
  subject: SessionSubject | null;
}

export interface SessionStore {
  getState(): SessionState;
  subscribe(listener: () => void): () => void;
  setSession(subject: SessionSubject): void;
  clearSession(): void;
  /** Back to "loading" (while a restore runs). Keeps the current subject. */
  setLoading(): void;
}

export const ANONYMOUS: SessionState = Object.freeze({ status: "anonymous", subject: null });
export const LOADING: SessionState = Object.freeze({ status: "loading", subject: null });

export function createSessionStore(initial: SessionState = LOADING): SessionStore {
  let state = initial;
  const listeners = new Set<() => void>();
  // A new object on every change and the same object otherwise: that is the
  // contract useSyncExternalStore relies on to avoid render loops.
  const set = (next: SessionState) => {
    if (next.status === state.status && next.subject === state.subject) return;
    state = next;
    for (const l of [...listeners]) l();
  };
  return {
    getState: () => state,
    subscribe(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    setSession: (subject) => set({ status: "authenticated", subject }),
    clearSession: () => set(ANONYMOUS),
    setLoading: () => set({ status: "loading", subject: state.subject }),
  };
}

/**
 * Whether the subject may do `permission`. Only staff have permissions;
 * super_admin has all of them (ARCHITECTURE §4.3). This only hides UI — the
 * server enforces every permission again, so a stale list fails closed there.
 */
export function can(subject: SessionSubject | null, permission: Permission): boolean {
  if (!subject || subject.type !== "staff") return false;
  if (subject.roles?.includes("super_admin")) return true;
  return subject.permissions?.includes(permission) ?? false;
}

export function canAny(subject: SessionSubject | null, permissions: readonly Permission[]): boolean {
  return permissions.some((p) => can(subject, p));
}
