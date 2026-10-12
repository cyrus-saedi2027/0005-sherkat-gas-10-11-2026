import * as React from "react";

export type VisuallyHiddenProps = React.HTMLAttributes<HTMLSpanElement> & {
  ref?: React.Ref<HTMLSpanElement>;
};

/**
 * Read by screen readers, invisible on screen. Uses the global
 * `.gz-sr-only` utility (not a CSS Module) so it also works for markup
 * rendered outside React, e.g. a live region created imperatively.
 */
export function VisuallyHidden({ className, ...rest }: VisuallyHiddenProps) {
  return <span {...rest} className={className ? `gz-sr-only ${className}` : "gz-sr-only"} />;
}
