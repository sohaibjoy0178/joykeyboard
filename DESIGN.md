---
name: JoyKeyboard Pearl Glass
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
Apple-inspired pearl glass translated to a lightweight Windows utility: pale silver layers, a fine white rim, subtle reflected highlights, clear navy typography and restrained blue controls. Original J/microphone mark uses matching silver/blue glass artwork. Compact bar remains the default; studio and tools open on request. No borrowed Apple branding or macOS dependencies.

## Colors
Blue identifies primary actions and selected controls. Neutral silver keeps surfaces quiet. A warm rose recording state and readable red errors carry text as well as color. Use the same light palette in every tool, popup, input, selection and help view.

## Typography
Native Windows typography ensures readable rendering without remote font dependencies. Bengali uses system Bengali fallback.

## Layout
Default surface: a 384 by 48 logical-pixel frameless bar, always on top, near the top center of the work area. An icon-only brand and narrow grip leave space for language/layout, keyboard, voice, menu and hide controls. Keep the idle surface to one row; feedback and eight candidates expand only when relevant. Remember position and clamp to a connected screen. Opening a workspace is explicit; closing it returns to the bar. Explicit Quit preserves drafts and worker shutdown. The bar must not take focus from the destination editor.

## Elevation & Depth
The bar paints a static rounded glass shell: silver-to-white reflections, a white rim and a soft lower edge. Workspace uses near-white layered surfaces and segmented navigation. No live blur, refraction shader, desktop capture, animated backgrounds or extra rendering dependency. This is a glass-inspired finish, not Apple's native Liquid Glass renderer. Default opacity stays 100% (opaque); 90/80/70% remain available with immediate preview and persistence. Repaint/resize only when needed. Preserve the 384×48 footprint and focus behavior. Installer retains original icon and sign-in startup checkbox; Settings controls the same per-user entry.

## Shapes
Rounded controls and recording panel echo the icon. Transcript text area stays generous and simple.

## Components
Preferences includes a single-chord global voice shortcut recorder, Apply and Reset buttons, and an inline registration status. Default Ctrl+Alt+Space toggles start/finish. Windows registers the chord globally, prevents repeat while held, and reports conflicts without replacing the previous working shortcut. Reflect the saved shortcut in bar, tray and studio hints. Editing a shortcut never starts recording; restart restores it.
Original mark opens the workspace; direct language/layout selectors, keyboard toggle, primary Speak/Finish control, menu and hide control. Match icon strokes at 1.7 logical pixels; use native Windows fonts with Bengali fallback. Tooltips and accessible names describe every icon control. The menu reaches every existing tool, engine, input/output choice, preferences, privacy and Quit. Recording exposes cancel, timer and level. Composition exposes eight clickable candidates. Ready transcripts expose Copy/Open. Errors remain visible until dismissed or replaced; routine status clears after a short delay. All controls reflect the same existing application state.

## Do's and Don'ts
Keep privacy and network behavior clear at engine selection. Never advertise universal PC compatibility or permanent free service. Show API-key instructions in help, not fake credential inputs for an engine that does not use them.
