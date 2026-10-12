/* ─────────────────────────────────────────────────────────────
 *  Palettes — «گازیار» day and night.
 *
 *  Brand reasoning: a utility people must trust with their bill and
 *  their meter photo. The primary is a deep gas-flame blue (the blue
 *  of a clean burner, not a "tech" blue), secondary is a calm teal
 *  that means "saving / approved", and a warm flame amber is reserved
 *  for points and prizes so a reward never looks like a warning.
 *
 *  Rules carried over from the reference, each because it broke once:
 *   1. Every text colour is ≥ 4.5:1 on every surface it is used on,
 *      including the faintest grey. theme.test.ts computes WCAG
 *      contrast for each pair in TEXT_PAIRS and fails below 4.5.
 *   2. Status colours are dark on light surfaces, not bright: bright
 *      red on white is how a "rejected" badge became invisible.
 *   3. Surfaces are opaque. A translucent card takes its colour from
 *      whatever scrolls behind it and appears to flicker.
 *   4. Two accent ramps: `accent` (small emphatic fills — buttons, the
 *      nav pill — with its own ink) and `accentWash` (large tinted
 *      surfaces with dark text). One ramp cannot do both in blue: a
 *      blue light enough for text-on-top is too weak for emphasis.
 *   5. Gradients only on three things: page background, primary
 *      button, deep hero panel. More than that and the app looks dirty.
 *
 *  Keys that are not opaque hex (gradients, rgba shadows/scrims) are
 *  listed in NON_HEX_KEYS; everything else is tested.
 * ───────────────────────────────────────────────────────────── */

export type Palette = {
  /* ── surfaces ── */
  /** page base under the gradient */
  canvas: string;
  /** chrome surfaces: headers, sheets, sidebars */
  surface: string;
  /** recessed surface: segmented track, icon squares, inputs on cards */
  surfaceAlt: string;
  card: string;
  /** zebra rows, nested blocks inside a card */
  cardAlt: string;

  /* ── text ── */
  ink: string;
  inkMuted: string;
  /** the faintest text allowed — still ≥ 4.5:1 on every surface */
  inkFaint: string;

  /** 1px border around cards and rows — separation that costs no paint */
  hair: string;
  divider: string;

  /* ── accent (brand blue) ── */
  accent: string;
  /** gradient stops of the primary button; ink must pass on both */
  accentTop: string;
  accentBottom: string;
  /** text/icons on `accent` */
  accentInk: string;
  /** accent-coloured text (links, active tab) on card/canvas */
  accentText: string;
  accentWash: string;
  /** text on `accentWash` */
  accentWashInk: string;
  accentGrad: string;

  /* ── reward (flame amber) — points, prizes, wallet ── */
  reward: string;
  rewardInk: string;
  rewardText: string;
  rewardWash: string;

  /* ── deep hero panel ── */
  deep: string;
  deepAlt: string;
  deepInk: string;
  deepInkMuted: string;
  deepGrad: string;

  /* ── status ── */
  ok: string;
  okWash: string;
  warn: string;
  warnWash: string;
  crit: string;
  critWash: string;
  info: string;
  infoWash: string;
  /** unread dots, count badges */
  attn: string;
  attnWash: string;
  /** ink on a solid status fill (a count badge on `attn`, a toast icon
   *  on `ok`) — the status colours double as fills, tested both ways */
  onSolid: string;

  /* ── page background ── */
  bgTop: string;
  bgMid: string;
  bgBottom: string;
  /** faint halo at the top of the page */
  glow: string;

  /** dimming layer behind sheets and dialogs */
  scrim: string;

  /* ── floating pill nav ── */
  nav: string;
  navInk: string;
  navActive: string;
  navActiveInk: string;

  /** text on dark fills (deep buttons, hero panels) */
  onDark: string;
  /** toast / tooltip fill — the inverse of the page in both themes */
  toast: string;
  toastInk: string;

  /** <meta name="theme-color"> */
  bar: string;

  /** keyboard focus ring — ≥ 3:1 against canvas and card (non-text contrast) */
  focus: string;
  /** progress ring / switch track */
  ring: string;
  ringTrack: string;
  /** switch track when off — darker than ringTrack so the knob reads at 3:1 */
  switchTrack: string;
  /** switch knob when off, and when on (on the accent track). Night's
   *  accent is a light blue, where a white knob would sit at ~2:1. */
  knob: string;
  knobOn: string;
  selection: string;

  shadow: string;
  shadowStrong: string;

  /* ── charts: series ≥ 3:1 against card ── */
  chart1: string;
  chart2: string;
  chart3: string;
  chart4: string;
  chart5: string;
  chart6: string;
  chartGrid: string;
};

export type ThemeId = "day" | "night";

export type Theme = { fa: string; dark: boolean; p: Palette };

/** Keys whose values are not opaque hex — skipped by the contrast test. */
export const NON_HEX_KEYS = [
  "accentGrad",
  "deepGrad",
  "glow",
  "scrim",
  "selection",
  "shadow",
  "shadowStrong",
] as const satisfies readonly (keyof Palette)[];

const day: Palette = {
  canvas: "#F3F6FB",
  surface: "#FFFFFF",
  surfaceAlt: "#E9EEF6",
  card: "#FFFFFF",
  cardAlt: "#F5F7FB",

  ink: "#0C1526",
  inkMuted: "#3D4960",
  inkFaint: "#596580",

  hair: "#E1E7F0",
  divider: "#D3DBE8",

  accent: "#1546C8",
  accentTop: "#1D52DA",
  accentBottom: "#123DB2",
  accentInk: "#FFFFFF",
  accentText: "#1442BC",
  accentWash: "#E5ECFC",
  accentWashInk: "#0E328F",
  accentGrad: "linear-gradient(180deg,#1D52DA 0%,#123DB2 100%)",

  reward: "#A34A00",
  rewardInk: "#FFFFFF",
  rewardText: "#8F4100",
  rewardWash: "#FFF0DB",

  deep: "#0B1F4D",
  deepAlt: "#14306B",
  deepInk: "#FFFFFF",
  deepInkMuted: "#BCC9E8",
  deepGrad: "linear-gradient(160deg,#14306B 0%,#0B1F4D 70%)",

  ok: "#0A6B5B",
  okWash: "#DFF3EE",
  warn: "#8A4F00",
  warnWash: "#FCEFD9",
  crit: "#B0201A",
  critWash: "#FCE9E7",
  info: "#0C58A8",
  infoWash: "#E2EFFC",
  attn: "#B83A0B",
  attnWash: "#FFEBE0",
  onSolid: "#FFFFFF",

  bgTop: "#F7F9FD",
  bgMid: "#F1F4FA",
  bgBottom: "#E8EDF6",
  glow: "rgba(21,70,200,.07)",

  scrim: "rgba(6,12,28,.44)",

  nav: "#0F1A33",
  navInk: "#A9B4CB",
  navActive: "#FFFFFF",
  navActiveInk: "#0F1A33",

  onDark: "#FFFFFF",
  toast: "#111B30",
  toastInk: "#FFFFFF",

  bar: "#F7F9FD",

  focus: "#1546C8",
  ring: "#1546C8",
  ringTrack: "#D6DEEC",
  switchTrack: "#77849D",
  knob: "#FFFFFF",
  knobOn: "#FFFFFF",
  selection: "rgba(21,70,200,.2)",

  shadow: "rgba(15,32,72,.26)",
  shadowStrong: "rgba(15,32,72,.38)",

  chart1: "#1546C8",
  chart2: "#0E8573",
  chart3: "#C26A00",
  chart4: "#C2335B",
  chart5: "#6B4FD6",
  chart6: "#5A6780",
  chartGrid: "#E3E8F1",
};

const night: Palette = {
  canvas: "#090E1A",
  surface: "#0F1626",
  surfaceAlt: "#18213A",
  card: "#121A2C",
  cardAlt: "#172036",

  ink: "#EEF2FA",
  inkMuted: "#B8C2D7",
  inkFaint: "#8F9BB4",

  hair: "#212B43",
  divider: "#2A3551",

  accent: "#8AA8FF",
  accentTop: "#9BB5FF",
  accentBottom: "#7A9BFA",
  accentInk: "#06122E",
  accentText: "#9DB5FF",
  accentWash: "#1A2A55",
  accentWashInk: "#D0DCFF",
  accentGrad: "linear-gradient(180deg,#9BB5FF 0%,#7A9BFA 100%)",

  reward: "#FFB547",
  rewardInk: "#2A1700",
  rewardText: "#FFC266",
  rewardWash: "#33240C",

  deep: "#152B63",
  deepAlt: "#1D3878",
  deepInk: "#FFFFFF",
  deepInkMuted: "#C2CFEE",
  deepGrad: "linear-gradient(160deg,#1D3878 0%,#152B63 70%)",

  ok: "#5AD6BB",
  okWash: "#0E2D2A",
  warn: "#F5B955",
  warnWash: "#30240E",
  crit: "#FF928A",
  critWash: "#3A1618",
  info: "#82B8FF",
  infoWash: "#12253F",
  attn: "#FFA474",
  attnWash: "#3A2013",
  onSolid: "#0A0F1A",

  bgTop: "#0D1424",
  bgMid: "#0A101D",
  bgBottom: "#070B15",
  glow: "rgba(138,168,255,.08)",

  scrim: "rgba(0,0,0,.6)",

  nav: "#E9EEF8",
  navInk: "#4A5671",
  navActive: "#0C1526",
  navActiveInk: "#FFFFFF",

  onDark: "#FFFFFF",
  toast: "#E9EEF8",
  toastInk: "#0C1526",

  bar: "#0D1424",

  focus: "#8AA8FF",
  ring: "#8AA8FF",
  ringTrack: "#26314C",
  switchTrack: "#4A5671",
  knob: "#FFFFFF",
  knobOn: "#06122E",
  selection: "rgba(138,168,255,.3)",

  shadow: "rgba(0,0,0,.55)",
  shadowStrong: "rgba(0,0,0,.7)",

  chart1: "#8AA8FF",
  chart2: "#4FD1B5",
  chart3: "#FFB547",
  chart4: "#FF8FB1",
  chart5: "#B9A4FF",
  chart6: "#A3B0C8",
  chartGrid: "#222C44",
};

export const THEMES: Record<ThemeId, Theme> = {
  day: { fa: "روز", dark: false, p: day },
  night: { fa: "شب", dark: true, p: night },
};

export const DEFAULT_THEME: ThemeId = "day";

type K = keyof Palette;

/** [text, surface] — every text colour paired with every surface it sits on. */
const ON_SURFACES: K[] = ["canvas", "surface", "surfaceAlt", "card", "cardAlt", "bgTop", "bgMid", "bgBottom"];

export const TEXT_PAIRS: ReadonlyArray<readonly [K, K]> = [
  ...(["ink", "inkMuted", "inkFaint"] as const).flatMap((t) => ON_SURFACES.map((s) => [t, s] as const)),
  ["accentText", "card"],
  ["accentText", "canvas"],
  ["accentText", "surface"],
  ["accentText", "cardAlt"],
  ["accentInk", "accent"],
  ["accentInk", "accentTop"],
  ["accentInk", "accentBottom"],
  ["accentWashInk", "accentWash"],
  ["accentText", "accentWash"],
  ["rewardInk", "reward"],
  ["rewardText", "card"],
  ["rewardText", "rewardWash"],
  ["deepInk", "deep"],
  ["deepInk", "deepAlt"],
  ["deepInkMuted", "deep"],
  ["deepInkMuted", "deepAlt"],
  ...(["ok", "warn", "crit", "info", "attn"] as const).flatMap((t) => [
    [t, `${t}Wash` as K] as const,
    [t, "card"] as const,
    [t, "cardAlt"] as const,
    ["onSolid", t] as const,
  ]),
  ["navInk", "nav"],
  ["navActiveInk", "navActive"],
  ["onDark", "deep"],
  ["toastInk", "toast"],
  ["ink", "accentWash"],
  ["inkMuted", "accentWash"],
];

/** [graphic, surface] pairs that need the 3:1 non-text contrast (WCAG 1.4.11). */
export const GRAPHIC_PAIRS: ReadonlyArray<readonly [K, K]> = [
  ...(["chart1", "chart2", "chart3", "chart4", "chart5", "chart6"] as const).map((c) => [c, "card"] as const),
  ["focus", "canvas"],
  ["focus", "card"],
  ["ring", "card"],
  ["accent", "card"],
  ["knob", "switchTrack"],
  ["knobOn", "accent"],
];
