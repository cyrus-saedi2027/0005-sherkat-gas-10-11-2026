/* @gazyar/ui — the React DOM design system.
 *
 * Apps import components from here and the stylesheet once:
 *     import "@gazyar/ui/styles.css";
 *     import { Button, ThemeProvider, useReducedMotionSync } from "@gazyar/ui";
 *
 * `export *` on purpose: TypeScript reports two modules exporting the
 * same name as an error, so a collision between areas cannot slip in
 * silently the way an explicit list that shadows one of them can. */

export * from "./tokens";
export * from "./theme";
export * from "./lib";
export * from "./motion";
export * from "./primitives";
export * from "./text";
export * from "./icons";
export * from "./kit";
