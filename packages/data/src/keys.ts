/* Query key factory — the one place keys are spelled.
 *
 * Conventions (so invalidation can be precise, ARCHITECTURE §6.2):
 *   [domain]                          everything in a domain
 *   [domain, "list"]                  every list, any filters
 *   [domain, "list", params]          one filtered/paginated list
 *   [domain, "detail"]                every detail
 *   [domain, "detail", id, ...sub]    one entity and its sub-resources
 * TanStack matches keys by prefix, so invalidating qk.readings.detail(5)
 * also refreshes qk.readings.events(5), and qk.readings.lists() refreshes
 * every page of every filter after an approve. */

export type ParamValue = string | number | boolean | null | undefined | readonly (string | number | boolean)[];
export type ListParams = Readonly<Record<string, ParamValue>>;
export type CleanParams = Readonly<Record<string, string | number | boolean | readonly (string | number | boolean)[]>>;
export type Id = string | number;

/**
 * Drop unset filters (undefined, null, "", []) so `{status: undefined}` and
 * `{}` are the same cache entry — otherwise clearing a filter refetches a list
 * that is already cached.
 */
export function cleanParams(params?: ListParams): CleanParams {
  const out: Record<string, string | number | boolean | readonly (string | number | boolean)[]> = {};
  if (!params) return out;
  for (const k of Object.keys(params).sort()) {
    const v = params[k];
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v) && v.length === 0) continue;
    out[k] = v as string | number | boolean | readonly (string | number | boolean)[];
  }
  return out;
}

/* Ids are strings in keys: route params arrive as "5" while API payloads carry
 * 5, and ["readings","detail",5] would never match ["readings","detail","5"]. */
const sid = (id: Id) => String(id);

function entity<const D extends string>(domain: D) {
  return {
    all: [domain] as const,
    lists: () => [domain, "list"] as const,
    list: (params?: ListParams) => [domain, "list", cleanParams(params)] as const,
    details: () => [domain, "detail"] as const,
    detail: (id: Id) => [domain, "detail", sid(id)] as const,
  };
}

export const qk = {
  /** The signed-in subject: profile, devices, terms state. */
  me: {
    all: ["me"] as const,
    profile: () => ["me", "profile"] as const,
    eligibility: () => ["me", "eligibility"] as const,
  },
  dashboard: {
    all: ["dashboard"] as const,
    summary: (params?: ListParams) => ["dashboard", "summary", cleanParams(params)] as const,
  },
  readings: {
    ...entity("readings"),
    /** The current revision for one period (user app: "this month's reading"). */
    period: (periodKey: string) => ["readings", "period", periodKey] as const,
    events: (id: Id) => ["readings", "detail", sid(id), "events"] as const,
  },
  cases: {
    ...entity("cases"),
    calls: (id: Id) => ["cases", "detail", sid(id), "calls"] as const,
    visits: (id: Id) => ["cases", "detail", sid(id), "visits"] as const,
    photos: (id: Id) => ["cases", "detail", sid(id), "photos"] as const,
    estimate: (id: Id) => ["cases", "detail", sid(id), "estimate"] as const,
    events: (id: Id) => ["cases", "detail", sid(id), "events"] as const,
    calendar: (params?: ListParams) => ["cases", "calendar", cleanParams(params)] as const,
  },
  points: {
    all: ["points"] as const,
    balance: (userId?: Id) => (userId === undefined ? (["points", "balance"] as const) : (["points", "balance", sid(userId)] as const)),
    ledger: (params?: ListParams) => ["points", "ledger", cleanParams(params)] as const,
    rules: () => ["points", "rules"] as const,
  },
  referrals: {
    ...entity("referrals"),
    mine: () => ["referrals", "mine"] as const,
  },
  notifications: {
    ...entity("notifications"),
    unreadCount: () => ["notifications", "unread-count"] as const,
  },
  content: entity("content"),
  rewards: {
    ...entity("rewards"),
    categories: () => ["rewards", "categories"] as const,
  },
  redemptions: entity("redemptions"),
  tickets: {
    ...entity("tickets"),
    messages: (id: Id) => ["tickets", "detail", sid(id), "messages"] as const,
  },
  subscribers: {
    ...entity("subscribers"),
    consumption: (id: Id) => ["subscribers", "detail", sid(id), "consumption"] as const,
  },
  users: entity("users"),
  staff: entity("staff"),
  regions: entity("regions"),
  imports: entity("imports"),
  settings: {
    all: ["settings"] as const,
    list: () => ["settings", "list"] as const,
    detail: (key: string) => ["settings", "detail", key] as const,
  },
  audit: entity("audit"),
  reports: entity("reports"),
  surveys: entity("surveys"),
  files: {
    all: ["files"] as const,
    url: (fileId: string) => ["files", "url", fileId] as const,
  },
} as const;

export type QueryDomain = keyof typeof qk;
