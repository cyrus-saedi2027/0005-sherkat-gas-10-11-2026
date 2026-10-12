/* ─────────────────────────────────────────────────────────────
 *  KeyValue — label/value rows for detail pages and receipts.
 *
 *  A <dl>, so a screen reader announces each value with its label
 *  ("شماره اشتراک: ۱۲۳…") instead of reading two unrelated columns.
 *
 *  Layouts:
 *    leader   label at the inline-start, value at the inline-end, a
 *             hairline between them — the receipt look. The line is
 *             what lets the eye cross a wide row without landing on
 *             the neighbouring value.
 *    split    same placement, rows separated by dividers (settings,
 *             compact admin panels).
 *    stacked  label above value, in 1–3 responsive columns: admin
 *             detail pages, where values are long (addresses, notes)
 *             and a side-by-side row would squeeze them.
 * ───────────────────────────────────────────────────────────── */

import * as React from "react";
import { cx } from "../lib/cx";
import styles from "./KeyValue.module.css";

export type KeyValueItem = {
  /** Stable key; defaults to the index. */
  key?: React.Key;
  label: React.ReactNode;
  /** Shown as «—» when null/undefined/"" so an empty field is visibly empty, not missing. */
  value: React.ReactNode;
  /** Latin/identifier value (IBAN, username, tracking code): forced LTR and isolated. */
  ltr?: boolean;
  /** Bold, larger value — totals, the amount the user pays. */
  emphasis?: boolean;
  /** Small text under the value. */
  hint?: React.ReactNode;
  /** Span the full width in a multi-column stacked layout (addresses, notes). */
  wide?: boolean;
};

export type KeyValueLayout = "leader" | "split" | "stacked";

export type KeyValueProps = Omit<React.HTMLAttributes<HTMLDListElement>, "children"> & {
  items: readonly KeyValueItem[];
  layout?: KeyValueLayout;
  /** stacked only: columns from the md breakpoint up (always 1 on phones). Default 2. */
  columns?: 1 | 2 | 3;
  /** Text for empty values. Default «—». */
  empty?: React.ReactNode;
  ref?: React.Ref<HTMLDListElement>;
};

function isEmpty(v: React.ReactNode): boolean {
  return v === null || v === undefined || v === "" || v === false;
}

export function KeyValue({ items, layout = "leader", columns = 2, empty = "—", className, ref, ...rest }: KeyValueProps) {
  return (
    <dl
      {...rest}
      ref={ref}
      data-layout={layout}
      data-columns={layout === "stacked" ? columns : undefined}
      className={cx(styles.kv, className)}
    >
      {items.map((it, i) => {
        const blank = isEmpty(it.value);
        return (
          // A div per pair is valid inside <dl> (only dt/dd may sit in it,
          // so the leader line is the label's ::after, not an element).
          <div
            key={it.key ?? i}
            className={styles.item}
            data-emphasis={it.emphasis || undefined}
            data-wide={it.wide || undefined}
          >
            <dt className={styles.label}>{it.label}</dt>
            <dd className={styles.value} data-empty={blank || undefined}>
              {blank ? empty : it.ltr ? <bdi dir="ltr">{it.value}</bdi> : it.value}
              {it.hint ? <span className={styles.hint}>{it.hint}</span> : null}
            </dd>
          </div>
        );
      })}
    </dl>
  );
}
