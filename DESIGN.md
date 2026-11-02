---
name: Torrent Downloader
description: A restrained local transfer workspace adopting the owner-supplied redesign.
colors:
  primary: "#315edc"
  primary-hover: "#244dbd"
  sidebar: "#141b27"
  ground: "#f7f8fa"
  surface: "#ffffff"
  border: "#e4e8ee"
  ink: "#202b3a"
  readable-muted: "#65748a"
  sidebar-muted: "#9cacc3"
  nav-active: "#27385c"
  nav-indicator: "#7395ff"
  focus: "#4b7cff"
  downloading: "#256f59"
  downloading-bg: "#e7f5ef"
  paused: "#a16b28"
  paused-bg: "#fbf1e1"
  error: "#b94343"
  error-bg: "#fbeaea"
typography:
  headline:
    fontFamily: 'Inter, "Segoe UI Variable", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "clamp(27px, 2.3vw, 34px)"
    fontWeight: 710
    lineHeight: 1.17
    letterSpacing: "-0.035em"
  title:
    fontSize: "20px"
    fontWeight: 700
    lineHeight: 1.3
    letterSpacing: "-0.035em"
  body:
    fontFamily: 'Inter, "Segoe UI Variable", "Segoe UI", ui-sans-serif, system-ui, sans-serif'
    fontSize: "14px"
  control:
    fontSize: "13px"
    fontWeight: 650
  label:
    fontSize: "10px"
    fontWeight: 650
    letterSpacing: "0.085em"
rounded:
  chip: "6px"
  control: "9px"
  panel: "13px"
  modal: "17px"
spacing:
  compact: "8px"
  control-gap: "9px"
  card-gap: "15px"
  mobile-gutter: "16px"
  panel: "24px"
  modal: "30px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 15px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
  button-ghost:
    textColor: "#374357"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "0 15px"
  search-input:
    backgroundColor: "{colors.surface}"
    textColor: "#40516a"
    rounded: "{rounded.control}"
  nav-active:
    backgroundColor: "{colors.nav-active}"
    textColor: "{colors.surface}"
    rounded: "{rounded.control}"
    padding: "12px 13px"
  status-downloading:
    backgroundColor: "{colors.downloading-bg}"
    textColor: "{colors.downloading}"
    rounded: "{rounded.chip}"
    padding: "6px 8px"
  summary-card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "21px 23px 20px"
---

# Design System: Torrent Downloader

## Overview

**Creative North Star: "The Local Transfer Workspace"**

The owner-supplied interface establishes a quiet utility workspace: a dark slate navigation rail, a pale working ground, white panels, and clear royal-blue actions. Compact typography and consistent alignment support repeated inspection of live transfers without turning the dashboard into decoration.

Visual authority is `C:/Users/nithi/Downloads/torrent-downloader-redesigned.zip`, extracted for comparison in `.runtime/redesign-reference/`. The adopted system is implemented in `frontend/src/styles/redesign.css`, imported after `app.css` by `main.tsx`; both stylesheets contribute to the final cascade. The archive predates the current five-source search, so its visual language was merged into the working product rather than replacing its backend or current behavior. This name describes the adopted direction; it is not a new brand identity.

**Key Characteristics:**

- Slate navigation, pale ground, white working surfaces.
- Blue actions with restrained status colors and visible keyboard focus.
- Compact tables on desktop and readable transfer cards on narrow screens.
- Live state, qualified availability estimates, and progressive source feedback.

## Colors

### Primary

Royal blue identifies primary actions, active drawer tabs, and interactive emphasis. Its deeper hover value reinforces state without changing the interface's character. The lighter focus color supplies a visible outline.

### Neutral

Dark slate anchors navigation; cool ground separates white panels. Ink supports primary content, while readable muted text carries compact secondary labels. Borders define grouping without heavy outlines. Sidebar muted text uses its own lighter value against slate; it is not interchangeable with muted text on white.

### Semantic states

Green on pale green identifies downloading, amber on pale amber identifies paused or queued work, and red on pale red identifies errors. Metadata and completed/seeding states use their implemented blue variants. Search availability uses explicit labels and icons alongside color, with source-count disclosure and an estimate disclaimer.

**The Meaningful Color Rule.** Keep status labels and source feedback visible; color alone must not explain a transfer or availability state.

## Typography

The inherited family is Inter followed by Segoe UI Variable, Segoe UI, and system sans-serif fallbacks. No font file is bundled by this redesign; Inter is used only when available. The root size is the body token. Preserve the supplied labels and type character.

Headlines use the responsive headline token, section titles use the title token, and compact controls use the control token. Table headers use the small uppercase label treatment. Transfer names use slightly heavier compact text with wrapping; search result titles are larger (15px, weight 600, line height 1.5) to support scanning long names. Speed values use tabular numerals. Supporting explanations use comfortable line heights rather than enlarged dashboard typography.

## Layout

Desktop navigation occupies a fixed rail (248px); the main shell offsets by the same amount. The topbar is 75px high, and the workspace centers within a maximum width of 1740px. Horizontal gutters interpolate from 22px to 48px. Four summary panels precede queue controls and the transfer table.

At 1250px the rail becomes 216px. At 1000px summaries become two columns and secondary transfer columns hide. At 900px navigation becomes a full-width horizontal strip with horizontal scrolling, the main offset clears, and search results reflow into stacked information with availability and action below. At 650px workspace gutters become 16px, compact row spacing is prepared, and topbar/navigation controls have a 44px minimum height. The inherited 600px rules convert the table to transfer cards and complete the search form reflow; source controls, loading feedback, results, and pagination stay available. Search also has an intermediate 1100px column adjustment.

The detail drawer is right-aligned with width `min(510px, 100%)`; the add dialog uses `min(560px, 100%)`. Long names wrap rather than widening the viewport.

## Elevation & Depth

Depth combines tonal layering, thin borders, and soft shadows. Summary panels have `0 2px 4px #172d4b06, 0 10px 26px #172d4b03`; the transfer table has `0 3px 12px #1e355108`. The primary action has a small `0 2px 5px #25489b25` shadow. Menus, the detail drawer, and the add dialog use stronger shadows to communicate temporary layers. Drawer and modal scrims blur the background slightly; reduced-motion mode removes that blur and inherited rules disable animation and transitions. Button state changes otherwise use 160ms easing.

## Shapes

Controls are softly rounded, with smaller chips and larger panel corners as defined in the frontmatter. Modal corners are gentler still. Thin cool borders organize panels and fields. Round dots and slim progress tracks communicate state; they do not replace text. Small outline icons complement labels throughout navigation, controls, and status summaries.

## Components

### Buttons and fields

Blue filled buttons lead actions; ghost and icon controls use restrained outlines and pale hover fills. Focus-visible outlines are 2px with a 3px offset; fields use a lighter blue outline with a 1px offset. Standard controls have a 40px minimum height, search form controls use 44px, and small-screen topbar/navigation controls use 44px. Preserve disabled, pending, success, and failure states instead of presenting a static reference mockup.

### Navigation and summary panels

The active navigation item has a slate-blue fill, a thin border, a light-blue inset indicator, and white text. Transfer categories keep live counts. Four summary cards report live transfer information; muted captions and restrained colored icon tiles keep values prominent. The dedicated Find torrents view follows the same surface vocabulary.

### Transfer queue and detail drawer

The queue preserves filtering, sorting, progress, selection, keyboard-accessible actions, and descriptive status chips. Selected rows are pale blue; hover is subtler. Mobile cards retain names, status, progress, and actions while secondary columns yield. The drawer preserves tabs, transfer settings, files, events, task controls, and VLC stream preparation. Its progress summary and streaming section are lightly tinted panels within the white drawer.

### Add dialog

The add dialog retains magnet and torrent-file entry, validation, optional settings, pending feedback, and cancel/close behavior. Its white rounded surface is separated from the app by a dark translucent scrim. Match its type and fields to the adopted reference.

### Torrent search

Keep Bitsearch, UIndex, LimeTorrents, The Pirate Bay, and TorrentDownload. Each source reports Searching, result count, Unavailable, or Stopped independently. Results appear as providers finish; the Stop search control retains results already received. Search again restarts loading, and pagination uses the last submitted criteria. Results remain available when switching views.

Availability labels are estimates, not connection tests or speed guarantees. Keep the guidance disclosure, optional raw counts, best-availability/source sorting, warning messages, add-pending state, Added confirmation, and links back to transfers. Loading placeholders coexist with live source feedback; they must not conceal already-returned results.

## Do's and Don'ts

### Do:

- Do follow the supplied archive's slate, blue, pale-ground, and white-surface direction.
- Do preserve readable muted labels, visible focus, wrapping names, and mobile action access.
- Do extend the same controls and surfaces to current search and VLC workflows.
- Do treat `.impeccable/review/` screenshots as QA evidence, not shipping image assets.

### Don't:

- Don't replace live state or current five-provider search with the archive's older implementation.
- Don't replace the supplied labels or typography with a newly invented visual identity.
- Don't imply that source counts guarantee speed or completion.
- Don't introduce decorative raster imagery into this utility interface; no generated raster assets ship in this redesign.
