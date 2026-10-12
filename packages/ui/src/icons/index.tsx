import * as React from "react";
import { cx } from "../lib/cx";
import { GLYPHS, type Glyph, type IconName } from "./glyphs";
import styles from "./icons.module.css";

export { GLYPHS, type IconName } from "./glyphs";

export type IconProps = Omit<React.SVGProps<SVGSVGElement>, "ref" | "stroke"> & {
  /** px (or any CSS length). Default 20. */
  size?: number | string;
  /** Stroke width on the 24px grid. Default 1.9 (some glyphs set their own). */
  stroke?: number;
  /** Accessible name. Without it the icon is decorative (aria-hidden) —
   *  the right default, since icons almost always sit next to a label. */
  title?: string;
  ref?: React.Ref<SVGSVGElement>;
};

export type IconComponent = ((props: IconProps) => React.JSX.Element) & { displayName?: string };

function Svg({ glyph, size = 20, stroke, title, className, ref, ...rest }: IconProps & { glyph: Glyph }) {
  const id = React.useId();
  const a11y = title
    ? { role: "img", "aria-labelledby": id }
    : { "aria-hidden": true as const, focusable: "false" as const };
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke ?? glyph.stroke ?? 1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...a11y}
      {...rest}
      ref={ref}
      className={cx(styles.icon, glyph.flip && styles.flip, className)}
    >
      {title ? <title id={id}>{title}</title> : null}
      {glyph.d}
    </svg>
  );
}

function make(name: IconName): IconComponent {
  const glyph: Glyph = GLYPHS[name];
  const C: IconComponent = (props: IconProps) => <Svg glyph={glyph} {...props} />;
  C.displayName = `Icon(${name})`;
  return C;
}

/** Every icon by name: `const C = Icon[name]; <C size={18} />`. */
export const Icon = Object.fromEntries(
  (Object.keys(GLYPHS) as IconName[]).map((n) => [n, make(n)]),
) as Record<IconName, IconComponent>;

export const ICON_NAMES = Object.keys(GLYPHS) as IconName[];

/** Render an icon chosen at runtime (e.g. from a reward category's `icon` key). */
export function IconByName({ name, ...props }: IconProps & { name: IconName }) {
  const C = Icon[name];
  return <C {...props} />;
}

export const IconHome = Icon.home;
export const IconHouse = Icon.house;
export const IconGrid = Icon.grid;
export const IconList = Icon.list;
export const IconMenu = Icon.menu;
export const IconMore = Icon.more;
export const IconChevronStart = Icon.chevronStart;
export const IconChevronEnd = Icon.chevronEnd;
export const IconChevronUp = Icon.chevronUp;
export const IconChevronDown = Icon.chevronDown;
export const IconArrowStart = Icon.arrowStart;
export const IconArrowEnd = Icon.arrowEnd;
export const IconClose = Icon.close;
export const IconPlus = Icon.plus;
export const IconMinus = Icon.minus;
export const IconCheck = Icon.check;
export const IconCheckCircle = Icon.checkCircle;
export const IconSearch = Icon.search;
export const IconFilter = Icon.filter;
export const IconSort = Icon.sort;
export const IconZoomIn = Icon.zoomIn;
export const IconZoomOut = Icon.zoomOut;
export const IconSettings = Icon.settings;
export const IconLogout = Icon.logout;
export const IconRefresh = Icon.refresh;
export const IconRotate = Icon.rotate;
export const IconHistory = Icon.history;
export const IconLink = Icon.link;
export const IconShare = Icon.share;
export const IconCopy = Icon.copy;
export const IconQr = Icon.qr;
export const IconCamera = Icon.camera;
export const IconImage = Icon.image;
export const IconUpload = Icon.upload;
export const IconDownload = Icon.download;
export const IconFile = Icon.file;
export const IconFileExcel = Icon.fileExcel;
export const IconClipboard = Icon.clipboard;
export const IconSurvey = Icon.survey;
export const IconBook = Icon.book;
export const IconInbox = Icon.inbox;
export const IconEdit = Icon.edit;
export const IconTrash = Icon.trash;
export const IconCalendar = Icon.calendar;
export const IconClock = Icon.clock;
export const IconUser = Icon.user;
export const IconUsers = Icon.users;
export const IconShield = Icon.shield;
export const IconLock = Icon.lock;
export const IconEye = Icon.eye;
export const IconEyeOff = Icon.eyeOff;
export const IconBell = Icon.bell;
export const IconPhone = Icon.phone;
export const IconMessage = Icon.message;
export const IconMegaphone = Icon.megaphone;
export const IconTicket = Icon.ticket;
export const IconInfo = Icon.info;
export const IconAlert = Icon.alert;
export const IconFlag = Icon.flag;
export const IconStar = Icon.star;
export const IconSparkle = Icon.sparkle;
export const IconAward = Icon.award;
export const IconMoon = Icon.moon;
export const IconSun = Icon.sun;
export const IconFlame = Icon.flame;
export const IconMeter = Icon.meter;
export const IconThermometer = Icon.thermometer;
export const IconRuler = Icon.ruler;
export const IconLayers = Icon.layers;
export const IconWind = Icon.wind;
export const IconChimney = Icon.chimney;
export const IconWrench = Icon.wrench;
export const IconBolt = Icon.bolt;
export const IconLeaf = Icon.leaf;
export const IconChart = Icon.chart;
export const IconChartBar = Icon.chartBar;
export const IconTrendUp = Icon.trendUp;
export const IconTrendDown = Icon.trendDown;
export const IconGift = Icon.gift;
export const IconWallet = Icon.wallet;
export const IconCoins = Icon.coins;
export const IconHeart = Icon.heart;
export const IconPaw = Icon.paw;
export const IconMap = Icon.map;
export const IconPin = Icon.pin;
export const IconRoute = Icon.route;
