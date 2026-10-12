import * as React from "react";

/**
 * Controlled-or-uncontrolled state. Controlled when `value !== undefined`;
 * otherwise the component owns it, seeded from `defaultValue`. The setter
 * always calls `onChange`, so a controlled parent sees every change.
 */
export function useControllable<T>(
  value: T | undefined,
  defaultValue: T,
  onChange?: (next: T) => void,
): [T, (next: T) => void] {
  const [inner, setInner] = React.useState(defaultValue);
  const controlled = value !== undefined;
  const current = controlled ? value : inner;
  const onChangeRef = React.useRef(onChange);
  onChangeRef.current = onChange;
  const set = React.useCallback(
    (next: T) => {
      if (!controlled) setInner(next);
      onChangeRef.current?.(next);
    },
    [controlled],
  );
  return [current, set];
}
