import * as React from "react";
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MOTION, Spring, isReducedMotion, resetTicker, setReducedMotion } from "@gazyar/motion";
import { installFakeRaf, installMatchMedia, type FakeRaf } from "../test/fakeRaf";
import { useReducedMotionSync, useSpringBind, useSpringRef, useSpringState } from "./hooks";

let raf: FakeRaf;

beforeEach(() => {
  raf = installFakeRaf();
});

afterEach(() => {
  setReducedMotion(false);
  resetTicker();
  vi.unstubAllGlobals();
});

/** A sheet-like component: renders nothing while closed (the case that broke the reference). */
function Sheet({ open, spring }: { open: boolean; spring: Spring }) {
  const bind = useSpringBind<HTMLDivElement>(spring, (el, x) => {
    el.style.transform = `translate3d(0,${(x * 100).toFixed(2)}px,0)`;
  });
  React.useEffect(() => {
    if (open) spring.springTo(0);
  }, [open, spring]);
  return open ? <div data-testid="panel" ref={bind} /> : null;
}

describe("useSpringBind", () => {
  it("writes to a node that mounts after the subscription was made (reference early-return bug)", () => {
    const spring = new Spring(1, MOTION.sheet);
    const { rerender } = render(<Sheet open={false} spring={spring} />);
    expect(screen.queryByTestId("panel")).toBeNull();

    rerender(<Sheet open spring={spring} />);
    const panel = screen.getByTestId("panel");
    // Attached at the resting value right away, before any frame.
    expect(panel.style.transform).toBe("translate3d(0,100.00px,0)");

    act(() => {
      raf.frame();
      raf.frame();
    });
    const mid = parseFloat(panel.style.transform.split(",")[1]!);
    expect(mid).toBeGreaterThan(0);
    expect(mid).toBeLessThan(100);

    act(() => {
      raf.run();
    });
    expect(panel.style.transform).toBe("translate3d(0,0.00px,0)");
  });

  it("writes the current value immediately when a node attaches to a spring at rest", () => {
    const spring = new Spring(0.37, MOTION.thumb);
    function Late({ show }: { show: boolean }) {
      const bind = useSpringBind<HTMLDivElement>(spring, (el, x) => {
        el.dataset.x = x.toFixed(2);
      });
      return show ? <div data-testid="n" ref={bind} /> : null;
    }
    const { rerender } = render(<Late show={false} />);
    rerender(<Late show />);
    expect(screen.getByTestId("n").dataset.x).toBe("0.37");
    expect(raf.pending()).toBe(0);
  });

  it("renders zero times while animating", () => {
    let renders = 0;
    let api: Spring | null = null;
    function Hot() {
      renders++;
      const s = useSpringRef(0, MOTION.thumb);
      api = s;
      const bind = useSpringBind<HTMLDivElement>(s, (el, x) => {
        el.style.opacity = String(x);
      });
      return <div ref={bind} />;
    }
    render(<Hot />);
    const before = renders;
    act(() => {
      api!.springTo(1);
      raf.run();
    });
    expect(renders).toBe(before);
  });

  it("useSpringRef leaves the ticker on unmount", () => {
    let api: Spring | null = null;
    function Owner() {
      api = useSpringRef(0, MOTION.thumb);
      return null;
    }
    const { unmount } = render(<Owner />);
    api!.springTo(1);
    expect(raf.pending()).toBe(1);
    unmount();
    expect(api!.isMoving).toBe(false);
  });
});

describe("useSpringState", () => {
  it("re-renders with the value and lands exactly on the target", () => {
    const spring = new Spring(0, MOTION.thumb);
    const seen: number[] = [];
    function Cold() {
      const x = useSpringState(spring);
      seen.push(x);
      return <span data-testid="x">{x}</span>;
    }
    render(<Cold />);
    act(() => spring.springTo(1));
    // One act per frame: act batches state updates until it returns.
    while (raf.pending()) act(() => raf.frame());
    expect(screen.getByTestId("x").textContent).toBe("1");
    expect(seen.length).toBeGreaterThan(3);
  });
});

describe("useReducedMotionSync", () => {
  it("feeds the OS setting into the engine, live", () => {
    const mm = installMatchMedia({ "(prefers-reduced-motion: reduce)": true });
    function App() {
      useReducedMotionSync();
      return null;
    }
    const { unmount } = render(<App />);
    expect(isReducedMotion()).toBe(true);
    act(() => mm.set("(prefers-reduced-motion: reduce)", false));
    expect(isReducedMotion()).toBe(false);
    unmount();
    expect(mm.listeners("(prefers-reduced-motion: reduce)")).toBe(0);
  });
});
