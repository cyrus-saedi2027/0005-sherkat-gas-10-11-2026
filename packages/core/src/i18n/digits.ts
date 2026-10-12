/* Persian ↔ ASCII digits.
 *
 * Output rule: everything a person reads gets Persian digits, "٬" (U+066C)
 * thousands, "٫" (U+066B) decimal and a real minus "−" (U+2212).
 * Input rule: everything we compare, send or store is ASCII — users type on
 * Persian *and* Arabic keyboards and the two digit sets look alike but are
 * different code points (۴ U+06F4 vs ٤ U+0664). */

const FA_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const FA_ZERO = 0x06f0; // ۰
const AR_ZERO = 0x0660; // ٠

/** A plain decimal string for any finite number. String(1e21) is "1e+21" and
 *  String(1e-7) is "1e-7"; mapping digits on those would print "۱e+۲۱". */
function plainDecimal(n: number): string {
  const s = String(n);
  if (!/e/i.test(s)) return s;
  return n.toLocaleString("en-US", { useGrouping: false, maximumFractionDigits: 20 });
}

function mapDigits(s: string): string {
  return s.replace(/[0-9]/g, (d) => FA_DIGITS[d.charCodeAt(0) - 48] ?? d);
}

function groupThousands(int: string): string {
  let out = "";
  for (let i = int.length - 1, c = 0; i >= 0; i--, c++) {
    if (c > 0 && c % 3 === 0) out = "٬" + out;
    out = int[i] + out;
  }
  return out;
}

const NUMERIC = /^(-?)(\d+)(?:\.(\d+))?$/;

/**
 * Number (or numeric string) → Persian digits, "٬" grouping, "٫" decimal, "−" minus.
 * A non-numeric string (a date "1405/07/19", a tracking code "GZ-…") only has
 * its digits swapped: grouping it would corrupt it ("12-34" → "12٬-34").
 */
export function toFa(n: number | string, group = true): string {
  if (typeof n === "number" && !Number.isFinite(n)) return "—";
  const s = typeof n === "number" ? plainDecimal(n) : toEn(n);
  const m = NUMERIC.exec(s);
  if (!m) return mapDigits(s);
  const [, sign = "", int = "", frac] = m;
  // "-0" / "-0.00" (toFixed of a tiny negative) must not render as "−۰".
  const isZero = /^0+$/.test(int) && (!frac || /^0+$/.test(frac));
  // A leading zero means an identifier (mobile "0912…", national code), not a
  // quantity: grouping would print "۰۹٬۱۲۱٬۲۳۴٬۵۶۷".
  const isIdentifier = int.length > 1 && int.startsWith("0");
  const body = (group && !isIdentifier ? groupThousands(int) : int) + (frac ? "٫" + frac : "");
  return (sign && !isZero ? "−" : "") + mapDigits(body);
}

/** Persian (۰-۹) and Arabic-Indic (٠-٩) digits → ASCII. Everything else untouched. */
export function toEn(s: string): string {
  return s.replace(/[۰-۹٠-٩]/g, (d) => {
    const c = d.charCodeAt(0);
    return String(c >= FA_ZERO ? c - FA_ZERO : c - AR_ZERO);
  });
}

/**
 * Parse a number the way a Persian user types it: any digit set, "٬"/","
 * grouping, "٫" or "." decimal, "−" or "-" minus. null when it is not a number
 * (never NaN — NaN silently fails every comparison downstream).
 */
export function parseFaNumber(s: string): number | null {
  const t = toEn(s)
    .replace(/[\s٬,]/g, "")
    .replace(/٫/g, ".")
    .replace(/−/g, "-");
  if (!/^-?(\d+(\.\d*)?|\.\d+)$/.test(t)) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}
