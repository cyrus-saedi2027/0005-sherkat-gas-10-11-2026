/* React bindings for the session store (sessionStore.ts). */

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import type { Permission } from "@gazyar/core";
import { can, createSessionStore, type SessionState, type SessionStore, type SessionSubject } from "./sessionStore";

export interface SessionContextValue extends SessionState {
  setSession(subject: SessionSubject): void;
  clearSession(): void;
  /** Re-run the provider's `restore` (e.g. a "retry" button after an offline boot). */
  restore(): Promise<void>;
  /** Why the last restore failed (offline at boot), or null. */
  restoreError: unknown;
}

const SessionContext = createContext<{ store: SessionStore; restore: () => Promise<void>; restoreError: unknown } | null>(null);

export interface SessionProviderProps {
  /** Shared with the ApiClient's onSessionExpired. Created internally when omitted. */
  store?: SessionStore;
  /**
   * Boot-time restore, e.g. `api.restoreSession()` then a /me call. Resolve the
   * subject, or null when nobody is logged in. A rejection (offline) leaves the
   * session anonymous and is exposed as `restoreError`.
   */
  restore?: () => Promise<SessionSubject | null>;
  children?: ReactNode;
}

export function SessionProvider({ store: given, restore: restoreFn, children }: SessionProviderProps) {
  const [store] = useState(() => given ?? createSessionStore(restoreFn ? undefined : { status: "anonymous", subject: null }));
  const [restoreError, setRestoreError] = useState<unknown>(null);
  // Latest callback without re-running the boot effect when the parent
  // passes a new inline function on every render.
  const restoreRef = useRef(restoreFn);
  useEffect(() => {
    restoreRef.current = restoreFn;
  });

  // StrictMode runs the boot effect twice; sharing the in-flight run keeps
  // that to one refresh + one /me call.
  const inflight = useRef<Promise<void> | null>(null);
  const restore = useCallback((): Promise<void> => {
    const fn = restoreRef.current;
    if (!fn) return Promise.resolve();
    inflight.current ??= (async () => {
      store.setLoading();
      try {
        const subject = await fn();
        setRestoreError(null);
        if (subject) store.setSession(subject);
        else store.clearSession();
      } catch (e) {
        setRestoreError(e);
        store.clearSession();
      } finally {
        inflight.current = null;
      }
    })();
    return inflight.current;
  }, [store]);

  useEffect(() => {
    // Only when still undecided: a store handed in already authenticated
    // (e.g. right after login) must not be thrown back to "loading".
    if (restoreRef.current && store.getState().status === "loading") void restore();
  }, [restore, store]);

  const value = useMemo(() => ({ store, restore, restoreError }), [store, restore, restoreError]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

function useSessionContext() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession() must be used inside <SessionProvider>.");
  return ctx;
}

export function useSession(): SessionContextValue {
  const { store, restore, restoreError } = useSessionContext();
  const state = useSyncExternalStore(store.subscribe, store.getState, store.getState);
  return {
    status: state.status,
    subject: state.subject,
    setSession: store.setSession,
    clearSession: store.clearSession,
    restore,
    restoreError,
  };
}

/** Staff permission check for hiding UI (the server still enforces it). */
export function useCan(permission: Permission): boolean {
  const { subject } = useSession();
  return can(subject, permission);
}
