---
name: JoyKeyboard Light and Dark Glass
colors:
  primary: "#0068D9"
  secondary: "#E5F0FF"
  background: "#EEF2F7"
  surface: "#F8FAFE"
  raised: "#FFFFFF"
  border: "#CBD5E3"
  text: "#172337"
  muted: "#526279"
  error: "#AE2638"
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
Two equal modes: **Light Glass** and **Dark Glass**. Both use actual per-pixel transparency. Workspace retains compositor blur; floating bar disables native accent blur because it ignores custom rounded clipping and draws a rectangular backing. Light uses silver tint/navy text; dark uses a smoke tint/ivory text. Neither mode uses opaque outer surfaces. Switch from Preferences or the bar Theme menu; keep selection after restart. Legacy Clear Glass maps to Light Glass; existing light/dark choices remain intact.

## Colors
Light shell alpha 140–150/255; dark shell alpha at least 165/255 for legibility over bright backgrounds. Controls, tool panels and inputs use translucent overlays matching their mode. Text and icons stay fully opaque at 100% bar opacity. Both use the same reflected rims and blue voice action. Native popups retain readable matching opaque surfaces. Missing blur uses denser 210/255 tint in the chosen mode, never switches modes.

## Typography
Native Windows typography ensures readable rendering without remote font dependencies. Bengali uses system Bengali fallback.

## Layout
Default surface: a 384 by 48 logical-pixel frameless bar, always on top, near the top center of the work area. An icon-only brand and narrow grip leave space for language/layout, keyboard, voice, menu and hide controls. Keep the idle surface to one row; feedback and eight candidates expand only when relevant. Remember position and clamp to a connected screen. Opening a workspace is explicit; closing it returns to the bar. Explicit Quit preserves drafts and worker shutdown. The bar must not take focus from the destination editor.

## Elevation & Depth
Bar paints a rounded translucent shell with no native backdrop blur or extra background surface. Workspace keeps compositor blur. Never enable native accent blur on the bar: Windows ignores its custom rounded mask. Transparent PNG previews exclude the desktop crop. Keep bar footprint/focus behavior and 70/80/90/100% foreground opacity option. At 100% foreground remains fully opaque while both Light Glass and Dark Glass backgrounds stay translucent. Workspace uses a draggable title, double-click maximize/restore, minimize, close-to-bar and a resize grip because native frames cannot provide Qt per-pixel transparency. Native OS dialogs retain Windows styling. Windows blur is not Apple's proprietary Liquid Glass renderer; no refraction shader is claimed.

## Shapes
Rounded controls and recording panel echo the icon. Transcript text area stays generous and simple.

## Components
Preferences includes a single-chord global voice shortcut recorder, Apply and Reset buttons, and an inline registration status. Default Ctrl+Alt+Space toggles start/finish. Hover Speak/Stop to show the saved keys, press-once/start-again/stop instructions and where to customize them. Keep shortcut text out of the bar's layout so it stays 384×48. Change action label to Stop while recording. Windows registers the chord globally, prevents repeat while held, and reports conflicts without replacing the previous working shortcut. Reflect the saved shortcut in bar, tray and studio hints. Editing a shortcut never starts recording; restart restores it.
Original mark opens the workspace; direct language/layout selectors, keyboard toggle, primary Speak/Stop control, menu and hide control. Match icon strokes at 1.7 logical pixels; use native Windows fonts with Bengali fallback. Tooltips and accessible names describe every icon control. The menu reaches every existing tool, engine, input/output choice, preferences, privacy and Quit. Recording exposes cancel, timer and level. Composition exposes eight clickable candidates. Ready transcripts expose Copy/Open. Errors remain visible until dismissed or replaced; routine status clears after a short delay. All controls reflect the same existing application state.

## Do's and Don'ts
Keep privacy and network behavior clear at engine selection. Never advertise universal PC compatibility or permanent free service. Show API-key instructions in help, not fake credential inputs for an engine that does not use them.
