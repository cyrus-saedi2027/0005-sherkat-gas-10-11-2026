/** Join class names, skipping falsy entries. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  let out = "";
  for (const p of parts) {
    if (p) out = out ? `${out} ${p}` : p;
  }
  return out;
}
