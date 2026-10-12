/* Typed access to the generated OpenAPI schema.
 *
 *   import type { S, Page } from "@gazyar/core";
 *   api.get<S<"CurrentPeriodOut">>("/api/v1/app/readings/current")
 *
 * Regenerate schema.ts with `pnpm gen:api` whenever the backend changes; a
 * renamed or removed field then fails `tsc` in the apps instead of at runtime. */
import type { components, paths } from "./schema";

export type { components, paths };
export type Schemas = components["schemas"];
export type S<K extends keyof Schemas> = Schemas[K];

/** Every list endpoint returns this shape (backend core/pagination.py). */
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}
