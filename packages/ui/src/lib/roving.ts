/* Arrow-key navigation for radio-like groups (Segmented, Tabs).
   ArrowLeft/Right follow reading direction: in RTL, ArrowLeft moves
   *forward* — the key points where the next item visually is. */

export type RovingKey = "next" | "prev" | "first" | "last";

export function rovingKey(e: { key: string }, rtl: boolean, vertical = false): RovingKey | null {
  switch (e.key) {
    case "ArrowRight":
      return vertical ? null : rtl ? "prev" : "next";
    case "ArrowLeft":
      return vertical ? null : rtl ? "next" : "prev";
    case "ArrowDown":
      return "next";
    case "ArrowUp":
      return "prev";
    case "Home":
      return "first";
    case "End":
      return "last";
    default:
      return null;
  }
}

/** Index to move to, skipping disabled items and wrapping around. */
export function moveIndex(current: number, dir: RovingKey, disabled: readonly boolean[]): number {
  const n = disabled.length;
  if (n === 0) return -1;
  const enabled = (i: number) => !disabled[i];
  if (dir === "first" || dir === "last") {
    const order = Array.from({ length: n }, (_, i) => (dir === "first" ? i : n - 1 - i));
    return order.find(enabled) ?? current;
  }
  const step = dir === "next" ? 1 : -1;
  for (let k = 1; k <= n; k++) {
    const i = (((current + step * k) % n) + n) % n;
    if (enabled(i)) return i;
  }
  return current;
}
