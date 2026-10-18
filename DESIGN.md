---
name: JoyKeyboard Floating Instrument
colors:
  primary: "#D8ED92"
  secondary: "#B9CDC6"
  background: "#101614"
  surface: "#19221E"
  raised: "#232E27"
  border: "#344238"
  text: "#F4F5ED"
  muted: "#A4B2A8"
  error: "#FFB0A5"
typography:
  headline: { fontFamily: Segoe UI Variable Display, fontSize: 32px, fontWeight: 600, lineHeight: 1.15 }
  body: { fontFamily: Segoe UI, fontSize: 14px, fontWeight: 400, lineHeight: 1.5 }
  label: { fontFamily: Segoe UI, fontSize: 12px, fontWeight: 600, lineHeight: 1.3 }
rounded:
  sm: 8px
  md: 14px
  lg: 22px
  toolbar: 16px
spacing:
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
---

# JoyKeyboard

## Overview
Quiet premium keyboard and recording instrument: forest-black surfaces, warm ivory text, pale chartreuse action color, original J/microphone mark. The app opens as a compact floating control bar. The studio and tools are secondary workspaces opened from its menu. No borrowed logos.

## Colors
Chartreuse reserved for active capture and primary actions. Muted green supports status and controls. Error messages have text plus color.

## Typography
Native Windows typography ensures readable rendering without remote font dependencies. Bengali uses system Bengali fallback.

## Layout
Default surface: a 384 by 48 logical-pixel frameless bar, always on top, near the top center of the work area. An icon-only brand and narrow grip leave space for language/layout, keyboard, voice, menu and hide controls. Keep the idle surface to one row; feedback and eight candidates expand only when relevant. Remember position and clamp to a connected screen. Opening a workspace is explicit; closing it returns to the bar. Explicit Quit preserves drafts and worker shutdown. The bar must not take focus from the destination editor.

## Elevation & Depth
Use a solid charcoal surface and one fine edge, without blur, shadows, gradients or idle animation. Default opacity is 100% (opaque); offer 90%, 80% and 70% in Preferences and the bar menu, with immediate preview and persistence. Primary voice button in pale chartreuse; muted coral for recording/errors. Repaint and resize only when state changes. Installer uses the original icon, a simple native wizard and an explicit checked-by-default sign-in startup checkbox. Settings reads and controls the same per-user Windows startup entry; startup shows the idle bar without recording.

## Shapes
Rounded controls and recording panel echo the icon. Transcript text area stays generous and simple.

## Components
Original mark opens the workspace; direct language/layout selectors, keyboard toggle, primary Speak/Finish control, menu and hide control. Match icon strokes at 1.7 logical pixels; use native Windows fonts with Bengali fallback. Tooltips and accessible names describe every icon control. The menu reaches every existing tool, engine, input/output choice, preferences, privacy and Quit. Recording exposes cancel, timer and level. Composition exposes eight clickable candidates. Ready transcripts expose Copy/Open. Errors remain visible until dismissed or replaced; routine status clears after a short delay. All controls reflect the same existing application state.

## Do's and Don'ts
Keep privacy and network behavior clear at engine selection. Never advertise universal PC compatibility or permanent free service. Show API-key instructions in help, not fake credential inputs for an engine that does not use them.
