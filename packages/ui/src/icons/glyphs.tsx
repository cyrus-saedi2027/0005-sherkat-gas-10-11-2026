/* ─────────────────────────────────────────────────────────────
 *  Glyphs — hand-drawn on a 24×24 grid, stroke-only, round caps.
 *
 *  No icon library: no tree-shaking question, no runtime font, and a
 *  domain set (gas meter, chimney, draught seals, insulation layers)
 *  that no general library draws. Keep new glyphs inside 2..22 so a
 *  1.9 stroke never clips at the viewBox edge.
 *
 *  `flip: true` marks glyphs that carry a reading direction; they are
 *  drawn for LTR and mirrored in RTL by icons.module.css.
 * ───────────────────────────────────────────────────────────── */

import type * as React from "react";

export type Glyph = { d: React.ReactNode; flip?: boolean; stroke?: number };

export const GLYPHS = {
  /* ── navigation & structure ── */
  home: { d: <><path d="M3 10.2 12 3l9 7.2V20a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 20z" /><path d="M9 21.5V13h6v8.5" /></> },
  house: { d: <><path d="M2.5 11.8 12 4l9.5 7.8" /><path d="M5 9.8V20.5h14V9.8" /><path d="M10 20.5v-5.5h4v5.5" /></> },
  grid: { d: <><rect x="3" y="3" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="3" width="7.5" height="7.5" rx="2" /><rect x="3" y="13.5" width="7.5" height="7.5" rx="2" /><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2" /></> },
  list: { flip: true, d: <path d="M8.5 6h12M8.5 12h12M8.5 18h12M3.8 6h.01M3.8 12h.01M3.8 18h.01" /> },
  menu: { d: <path d="M4 6.5h16M4 12h16M4 17.5h16" /> },
  more: { stroke: 2.4, d: <path d="M5 12h.01M12 12h.01M19 12h.01" /> },
  chevronStart: { flip: true, d: <path d="m14.5 6-6 6 6 6" /> },
  chevronEnd: { flip: true, d: <path d="m9.5 6 6 6-6 6" /> },
  chevronUp: { d: <path d="m6 14.5 6-6 6 6" /> },
  chevronDown: { d: <path d="m6 9.5 6 6 6-6" /> },
  arrowStart: { flip: true, d: <><path d="M19.5 12h-15" /><path d="m10.5 6-6 6 6 6" /></> },
  arrowEnd: { flip: true, d: <><path d="M4.5 12h15" /><path d="m13.5 6 6 6-6 6" /></> },
  close: { d: <path d="M18 6 6 18M6 6l12 12" /> },
  plus: { d: <path d="M12 5v14M5 12h14" /> },
  minus: { stroke: 2.2, d: <path d="M5 12h14" /> },
  check: { stroke: 2.4, d: <path d="m4.5 12.5 5 5.2L19.5 7" /> },
  checkCircle: { d: <><circle cx="12" cy="12" r="9" /><path d="m8 12.3 2.8 2.9 5.4-5.7" /></> },
  search: { d: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.6-3.6" /></> },
  filter: { d: <path d="M3.5 5h17l-6.5 7.8V19l-4 2v-8.2z" /> },
  sort: { d: <path d="M7.5 4v16m0 0-3-3m3 3 3-3M16.5 20V4m0 0-3 3m3-3 3 3" /> },
  zoomIn: { d: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.6-3.6M11 8v6M8 11h6" /></> },
  zoomOut: { d: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.6-3.6M8 11h6" /></> },
  settings: {
    d: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 14.5a1.7 1.7 0 0 0 .34 1.87l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.11-1.56 1.7 1.7 0 0 0-1.87.34l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.7 1.7 0 0 0 .34-1.87 1.7 1.7 0 0 0-1.56-1.03H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.56-1.11 1.7 1.7 0 0 0-.34-1.87l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.7 1.7 0 0 0 1.87.34H9a1.7 1.7 0 0 0 1.03-1.56V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.7 1.7 0 0 0-.34 1.87V9a1.7 1.7 0 0 0 1.56 1.03H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1.03z" />
      </>
    ),
  },
  logout: { flip: true, d: <><path d="M14 4h4.5A1.5 1.5 0 0 1 20 5.5v13a1.5 1.5 0 0 1-1.5 1.5H14" /><path d="M10 8 6 12l4 4M6 12h9" /></> },
  refresh: { d: <><path d="M19.5 10.5A8 8 0 0 0 5.4 7.4L4 9" /><path d="M4 4.5V9h4.5" /><path d="M4.5 13.5a8 8 0 0 0 14.1 3.1L20 15" /><path d="M20 19.5V15h-4.5" /></> },
  rotate: { d: <><path d="M20 12a8 8 0 1 1-2.4-5.7" /><path d="M20 4.5V9h-4.5" /></> },
  history: { d: <><path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" /><path d="M3.5 4.5V9H8" /><path d="M12 7.5V12l3 1.8" /></> },
  link: { d: <><path d="M10 14a4.5 4.5 0 0 0 6.4 0l3-3a4.5 4.5 0 0 0-6.4-6.4l-1 1" /><path d="M14 10a4.5 4.5 0 0 0-6.4 0l-3 3a4.5 4.5 0 0 0 6.4 6.4l1-1" /></> },
  share: { d: <><circle cx="17.5" cy="5.5" r="2.5" /><circle cx="6.5" cy="12" r="2.5" /><circle cx="17.5" cy="18.5" r="2.5" /><path d="m8.7 10.7 6.6-3.9M8.7 13.3l6.6 3.9" /></> },
  copy: { d: <><rect x="8" y="8" width="12" height="12" rx="2.5" /><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2" /></> },
  qr: { d: <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><path d="M14 14h3v3h-3zM18 18h3v3h-3zM14 21h1M21 14h.01" /></> },

  /* ── files & media ── */
  camera: { d: <><path d="M3 8.5A2.5 2.5 0 0 1 5.5 6h2L9 3.8h6L16.5 6h2A2.5 2.5 0 0 1 21 8.5v9a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5z" /><circle cx="12" cy="12.8" r="3.6" /></> },
  image: { d: <><rect x="3" y="4" width="18" height="16" rx="2.5" /><circle cx="8.5" cy="9.5" r="1.6" /><path d="m21 15.5-5.2-5.2L5.5 20" /></> },
  upload: { d: <><path d="M12 15V4" /><path d="m7.5 8.5 4.5-4.5 4.5 4.5" /><path d="M4 16.5v3A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5v-3" /></> },
  download: { d: <><path d="M12 3.5v11" /><path d="m7.5 10 4.5 4.5 4.5-4.5" /><path d="M4 16.5v3A1.5 1.5 0 0 0 5.5 21h13a1.5 1.5 0 0 0 1.5-1.5v-3" /></> },
  file: { d: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="M9 13h6M9 16.5h4" /></> },
  fileExcel: { d: <><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" /><path d="m9.5 12.5 5 5.5M14.5 12.5l-5 5.5" /></> },
  clipboard: { d: <><path d="M9 4.5H7A2 2 0 0 0 5 6.5v13A2 2 0 0 0 7 21.5h10a2 2 0 0 0 2-2v-13a2 2 0 0 0-2-2h-2" /><rect x="9" y="3" width="6" height="3.2" rx="1" /><path d="m8.8 13.3 2.2 2.2 4.4-4.5" /></> },
  survey: { d: <><rect x="4.5" y="3" width="15" height="18.5" rx="2" /><path d="m7.8 8.5 1.3 1.3 2.3-2.4M13.8 8.7h2.7M7.8 14.8l1.3 1.3 2.3-2.4M13.8 15h2.7" /></> },
  book: { d: <><path d="M4.5 19V5.5A2.5 2.5 0 0 1 7 3h12.5v14H7a2.5 2.5 0 0 0-2.5 2.5A2.5 2.5 0 0 0 7 22h12.5v-5" /><path d="M9 7.5h6.5" /></> },
  inbox: { d: <><path d="M3 13.5 5.6 5.3A2 2 0 0 1 7.5 4h9a2 2 0 0 1 1.9 1.3l2.6 8.2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" /><path d="M3 13.5h5l1.5 2.5h5l1.5-2.5h5" /></> },
  edit: { d: <><path d="M4 20h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 17z" /><path d="m14.5 7.5 3 3" /></> },
  trash: { d: <><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13" /><path d="M10 11v6M14 11v6" /></> },

  /* ── time & calendar ── */
  calendar: { d: <><rect x="3" y="5" width="18" height="16" rx="2.5" /><path d="M3 10h18M8 3v4M16 3v4" /></> },
  clock: { d: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5.2l3.2 2" /></> },

  /* ── people & access ── */
  user: { d: <><circle cx="12" cy="8" r="4" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></> },
  users: { d: <><circle cx="9" cy="8" r="3.4" /><path d="M2.8 20a6.2 6.2 0 0 1 12.4 0" /><path d="M16 5.2a3.4 3.4 0 0 1 0 6.6M17.4 14.4A6.2 6.2 0 0 1 21.2 20" /></> },
  shield: { d: <><path d="M12 3l7.5 3v6c0 4.5-3 7.7-7.5 9.5C7.5 19.7 4.5 16.5 4.5 12V6z" /><path d="m9 12 2.2 2.2L15.5 10" /></> },
  lock: { d: <><rect x="4.5" y="10" width="15" height="11" rx="2.5" /><path d="M8 10V7.5a4 4 0 0 1 8 0V10" /></> },
  eye: { d: <><path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12" /><circle cx="12" cy="12" r="3" /></> },
  eyeOff: { d: <><path d="M4 4l16 16" /><path d="M9.5 9.6A3 3 0 0 0 12 15a3 3 0 0 0 2.4-1.2" /><path d="M6.3 6.5C3.9 8.1 2.5 12 2.5 12s3.5 6.5 9.5 6.5c1.5 0 2.8-.4 3.9-1M17.4 16C19.9 14.4 21.5 12 21.5 12S18 5.5 12 5.5c-.8 0-1.5.1-2.2.3" /></> },

  /* ── communication ── */
  bell: { d: <><path d="M18 8a6 6 0 1 0-12 0c0 6-3 7-3 7h18s-3-1-3-7" /><path d="M13.7 21a2 2 0 0 1-3.4 0" /></> },
  phone: { d: <path d="M5 3.5h3.2l1.6 4.2-2 1.3a11 11 0 0 0 7.2 7.2l1.3-2 4.2 1.6V19a1.5 1.5 0 0 1-1.6 1.5A16.5 16.5 0 0 1 3.5 5.1 1.5 1.5 0 0 1 5 3.5z" /> },
  message: { d: <><path d="M21 14.5a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 3.8V17A2.5 2.5 0 0 1 3 14.5v-8A2.5 2.5 0 0 1 5.5 4h13A2.5 2.5 0 0 1 21 6.5z" /><path d="M8 8.8h8M8 12.3h5" /></> },
  megaphone: { d: <><path d="M3.5 10v3.5A1.5 1.5 0 0 0 5 15h2.5l7.5 4.5v-15L7.5 9H5a1.5 1.5 0 0 0-1.5 1z" /><path d="M18.5 9a4 4 0 0 1 0 5.5" /><path d="m7.5 15 1.3 5h2.7l-1-4.6" /></> },
  ticket: { d: <><path d="M3 9V6.5A1.5 1.5 0 0 1 4.5 5h15A1.5 1.5 0 0 1 21 6.5V9a3 3 0 0 0 0 6v2.5a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 17.5V15a3 3 0 0 0 0-6z" /><path d="M14.5 5.5v2M14.5 11v2M14.5 16.5v2" /></> },

  /* ── status ── */
  info: { d: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5.5M12 7.8v.1" /></> },
  alert: { d: <><path d="M10.3 4.2 2.6 17.6A2 2 0 0 0 4.3 20.5h15.4a2 2 0 0 0 1.7-2.9L13.7 4.2a2 2 0 0 0-3.4 0z" /><path d="M12 9.5v4M12 16.8v.1" /></> },
  flag: { d: <><path d="M5 21.5V4" /><path d="M5 4.5c5-2.5 9 2.5 14 0v9c-5 2.5-9-2.5-14 0" /></> },
  star: { d: <path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8-5.2-2.7-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z" /> },
  sparkle: { d: <><path d="M11 3.5c.6 4.2 2.3 5.9 6.5 6.5-4.2.6-5.9 2.3-6.5 6.5-.6-4.2-2.3-5.9-6.5-6.5 4.2-.6 5.9-2.3 6.5-6.5z" /><path d="M18 15c.3 1.7 1 2.4 2.7 2.7-1.7.3-2.4 1-2.7 2.7-.3-1.7-1-2.4-2.7-2.7 1.7-.3 2.4-1 2.7-2.7z" /></> },
  award: { d: <><circle cx="12" cy="9" r="5.5" /><path d="m8.6 13.4-1.4 7.6 4.8-2.6 4.8 2.6-1.4-7.6" /></> },
  moon: { d: <path d="M20 14.5A8.5 8.5 0 1 1 9.5 4a6.8 6.8 0 0 0 10.5 10.5z" /> },
  sun: { d: <><circle cx="12" cy="12" r="4" /><path d="M12 2.5v2M12 19.5v2M5.3 5.3l1.4 1.4M17.3 17.3l1.4 1.4M2.5 12h2M19.5 12h2M5.3 18.7l1.4-1.4M17.3 6.7l1.4-1.4" /></> },

  /* ── energy & home audit ── */
  flame: { d: <><path d="M12 21.5c-3.9 0-7-2.8-7-6.6 0-3.6 2.4-5.6 3.8-8.7.5 1.9 1.4 3 2.6 3.6.1-3.2 1.6-5.6 4.3-7.3-.4 3 1 5 2.2 6.8 1 1.5 1.1 3 1.1 4.6 0 4.6-3.1 7.6-7 7.6z" /><path d="M12 21.5c-1.7 0-3-1.2-3-2.9 0-1.9 1.5-2.7 2.3-4.4.9 1 3.7 2.4 3.7 4.6 0 1.6-1.3 2.7-3 2.7z" /></> },
  meter: { d: <><rect x="4" y="3" width="16" height="18.5" rx="2.5" /><rect x="7" y="6.3" width="10" height="4.2" rx="1" /><path d="M9.5 6.3v4.2M12 6.3v4.2M14.5 6.3v4.2" /><circle cx="12" cy="15.6" r="2.6" /><path d="m12 15.6 1.5-1.3" /></> },
  thermometer: { d: <><path d="M14 14.6V5a2 2 0 0 0-4 0v9.6a4 4 0 1 0 4 0z" /><path d="M12 10v6.5" /></> },
  ruler: { d: <><rect x="2.5" y="7.5" width="19" height="9" rx="1.5" /><path d="M6.5 7.5v3M10.5 7.5v4.5M14.5 7.5v3M18.5 7.5v4.5" /></> },
  layers: { d: <><path d="m12 3.5 9 4.6-9 4.6-9-4.6z" /><path d="m3 12.2 9 4.6 9-4.6" /><path d="m3 16.2 9 4.6 9-4.6" /></> },
  wind: { d: <><path d="M3 9h10.5a2.5 2.5 0 1 0-2.5-2.5" /><path d="M3 13h14.5a3 3 0 1 1-3 3" /><path d="M3 17h6" /></> },
  chimney: { d: <><path d="M4 21V12.5L12 6l8 6.5V21z" /><path d="M15.5 8.8V3.5h3v7.8" /><path d="M10 21v-4.5h4V21" /></> },
  wrench: { d: <path d="M20.2 8.3a5 5 0 0 1-6.8 5.1l-6.6 6.7a2 2 0 0 1-2.9-2.9l6.7-6.6a5 5 0 0 1 5.1-6.8l-3 3 .6 2.6 2.6.6z" /> },
  bolt: { d: <path d="M13 2.5 4.5 13.5H12L11 21.5l8.5-11H12z" /> },
  leaf: { d: <><path d="M5 19.5C4.2 10.8 9.4 4.6 20 4c-.4 10.6-6.6 15.8-15 15.5z" /><path d="M5 19.5 13.5 11" /></> },

  /* ── charts & trends ── */
  chart: { d: <><path d="M3.5 3.5v16a1 1 0 0 0 1 1h16" /><path d="m7.5 14.5 3.5-4 3 3 5.5-6.5" /></> },
  chartBar: { d: <><path d="M3.5 20.5h17" /><path d="M7 17v-6M12 17V5.5M17 17v-4" /></> },
  trendUp: { d: <><path d="m3 17 6.5-6.5 4 4L21 7" /><path d="M15.5 7H21v5.5" /></> },
  trendDown: { d: <><path d="m3 7 6.5 6.5 4-4L21 17" /><path d="M21 11.5V17h-5.5" /></> },

  /* ── rewards & money ── */
  gift: { d: <><rect x="3" y="8" width="18" height="4.5" rx="1" /><path d="M5 12.5V20a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-7.5M12 8v13" /><path d="M12 8C10.5 4.5 7 4 6.5 6s2.5 2 5.5 2zM12 8c1.5-3.5 5-4 5.5-2S15 8 12 8z" /></> },
  wallet: { d: <><path d="M18.5 7.5V5.5A1.5 1.5 0 0 0 17 4H5.5A2.5 2.5 0 0 0 3 6.5v11A2.5 2.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V9a1.5 1.5 0 0 0-1.5-1.5h-13A2.5 2.5 0 0 1 3 5" /><path d="M16.5 13.8h.01" /></> },
  coins: { d: <><ellipse cx="12" cy="6.5" rx="7" ry="3" /><path d="M5 6.5v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5" /><path d="M5 11.5v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5" /></> },
  heart: { d: <path d="M12 20.5S3.5 15.6 3.5 9.3A4.8 4.8 0 0 1 12 6.4a4.8 4.8 0 0 1 8.5 2.9c0 6.3-8.5 11.2-8.5 11.2z" /> },
  paw: { d: <><path d="M12 12.5c-2.6 0-5 2.7-5 5 0 1.6 1.2 2.5 2.6 2.5 1 0 1.6-.5 2.4-.5s1.4.5 2.4.5c1.4 0 2.6-.9 2.6-2.5 0-2.3-2.4-5-5-5z" /><circle cx="5.5" cy="11" r="1.8" /><circle cx="9.2" cy="6.5" r="1.8" /><circle cx="14.8" cy="6.5" r="1.8" /><circle cx="18.5" cy="11" r="1.8" /></> },

  /* ── places ── */
  map: { d: <><path d="M9 4 3.5 6v14L9 18l6 2 5.5-2V4L15 6z" /><path d="M9 4v14M15 6v14" /></> },
  pin: { d: <><path d="M12 21.5s-7-6.2-7-11.7a7 7 0 0 1 14 0c0 5.5-7 11.7-7 11.7z" /><circle cx="12" cy="9.8" r="2.6" /></> },
  route: { d: <><circle cx="6" cy="18.5" r="2.5" /><circle cx="18" cy="5.5" r="2.5" /><path d="M8.5 18.5H16a3.5 3.5 0 0 0 0-7H8a3 3 0 0 1 0-6h7.5" /></> },
} satisfies Record<string, Glyph>;

export type IconName = keyof typeof GLYPHS;
