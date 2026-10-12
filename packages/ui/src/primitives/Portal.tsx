import * as React from "react";
import { createPortal } from "react-dom";

export const OVERLAY_ROOT_ID = "gz-overlays";

/**
 * The single container every sheet, dialog and toast portals into.
 * Created on first use so apps do not have to remember it in
 * index.html. One root (not one per overlay) keeps stacking order
 * equal to mount order, which is what the overlay stack relies on.
 */
export function getOverlayRoot(): HTMLElement | null {
  if (typeof document === "undefined") return null;
  let root = document.getElementById(OVERLAY_ROOT_ID);
  if (!root) {
    root = document.createElement("div");
    root.id = OVERLAY_ROOT_ID;
    document.body.appendChild(root);
  }
  return root;
}

export type PortalProps = {
  children?: React.ReactNode;
  /** Render into this element instead of the shared overlay root. */
  container?: HTMLElement | null;
};

export function Portal({ children, container }: PortalProps) {
  // Resolved once; SSR/tests without a document render nothing.
  const [root] = React.useState<HTMLElement | null>(() => container ?? getOverlayRoot());
  const target = container ?? root;
  return target ? createPortal(children, target) : null;
}
