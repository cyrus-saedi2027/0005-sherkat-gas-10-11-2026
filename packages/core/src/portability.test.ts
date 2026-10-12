/// <reference types="node" />
/* React Native portability guard (ARCHITECTURE §2): core, motion and data
 * must not reference DOM globals or import react-dom; core and motion must not
 * import React at all. ESLint enforces the same, but lint can be skipped or
 * misconfigured — a failing test cannot. Comments and string contents are
 * stripped first so prose like "window/document" in a comment is fine. */

import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const PACKAGES = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

const EXEMPT = [/\.test\.tsx?$/, /\.test-util\.tsx?$/, /(^|\/)platform\.web\.ts$/];

function sources(dir: string): string[] {
  let out: string[] = [];
  let entries: string[];
  try {
    entries = readdirSync(dir);
  } catch {
    return out; // package not created yet
  }
  for (const name of entries) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) out = out.concat(sources(p));
    else if (/\.tsx?$/.test(name) && !EXEMPT.some((r) => r.test(p))) out.push(p);
  }
  return out;
}

/** Drop comments and the contents of string/template literals (keeping the
 *  quotes, so `from "react-dom"` is still visible as an import). */
function stripCommentsAndStrings(src: string, keepImportSpecifiers = true): string {
  let out = "";
  let i = 0;
  while (i < src.length) {
    const c = src[i]!;
    const n = src[i + 1];
    if (c === "/" && n === "/") {
      while (i < src.length && src[i] !== "\n") i++;
    } else if (c === "/" && n === "*") {
      i += 2;
      while (i < src.length && !(src[i] === "*" && src[i + 1] === "/")) i++;
      i += 2;
    } else if (c === '"' || c === "'" || c === "`") {
      let j = i + 1;
      let body = "";
      while (j < src.length && src[j] !== c) {
        if (src[j] === "\\") {
          body += src[j]! + (src[j + 1] ?? "");
          j += 2;
          continue;
        }
        body += src[j];
        j++;
      }
      const isSpecifier = keepImportSpecifiers && /(\bfrom|\bimport|\brequire\()\s*$/.test(out);
      out += c + (isSpecifier ? body : "") + c;
      i = j + 1;
    } else {
      out += c;
      i++;
    }
  }
  return out;
}

const DOM_GLOBALS: [string, RegExp][] = [
  ["window", /(?<![.\w$])window\b/],
  ["document", /(?<![.\w$])document\b/],
  ["localStorage", /(?<![.\w$])localStorage\b/],
  ["sessionStorage", /(?<![.\w$])sessionStorage\b/],
  ["navigator", /(?<![.\w$])navigator\b/],
  ["XMLHttpRequest", /(?<![.\w$])XMLHttpRequest\b/],
  ["react-dom", /["']react-dom(\/[^"']*)?["']/],
];
const REACT_IMPORT: [string, RegExp] = ["react", /["']react(\/[^"']*)?["']/];

const TARGETS: { pkg: string; rules: [string, RegExp][] }[] = [
  { pkg: "core", rules: [...DOM_GLOBALS, REACT_IMPORT] },
  { pkg: "motion", rules: [...DOM_GLOBALS, REACT_IMPORT] },
  { pkg: "data", rules: DOM_GLOBALS },
];

describe("stripCommentsAndStrings", () => {
  it("keeps code and import specifiers, drops prose and string contents", () => {
    const src = [
      '// window.alert in a comment',
      '/* document.title */ const a = "window.x";',
      'import x from "react-dom";',
      "const b = `localStorage`;",
      "const c = obj.window;",
    ].join("\n");
    const s = stripCommentsAndStrings(src);
    expect(s).not.toMatch(/alert|title|window\.x|localStorage/);
    expect(s).toContain('from "react-dom"');
    expect(DOM_GLOBALS[0]![1].test(s)).toBe(false); // obj.window is a property, not the global
  });
});

describe("platform-neutral packages", () => {
  it("core has the files this guard is meant to protect", () => {
    const files = sources(join(PACKAGES, "core", "src")).map((f) => relative(PACKAGES, f));
    expect(files).toContain(join("core", "src", "api", "client.ts"));
    expect(files).toContain(join("core", "src", "platform.ts"));
    expect(files).not.toContain(join("core", "src", "platform.web.ts"));
  });

  for (const { pkg, rules } of TARGETS) {
    it(`${pkg}/src has no DOM globals${rules.includes(REACT_IMPORT) ? " and no React" : " and no react-dom"}`, () => {
      const offences: string[] = [];
      for (const file of sources(join(PACKAGES, pkg, "src"))) {
        const code = stripCommentsAndStrings(readFileSync(file, "utf8"));
        for (const [name, re] of rules) if (re.test(code)) offences.push(`${relative(PACKAGES, file)}: ${name}`);
      }
      expect(offences).toEqual([]);
    });
  }
});
