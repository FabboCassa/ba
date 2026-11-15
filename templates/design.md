---
name: <Direction name>
status: exploring | approved
slug: <slug>
prototype: docs/design/<slug>/proto-v<N>.html
catalog: {palette: <id>, type: <id>, layout: <id>, motion: <id>, surface: <id>}
colors:
  bg: "#......"
  surface: "#......"
  ink: "#......"
  muted: "#......"
  accent: "#......"
  accent2: "#......"
typography:
  display: {fontFamily: <Family>, weights: [..], source: <google|local|url>}
  body: {fontFamily: <Family>, weights: [..]}
  scale: {xs: 0.75rem, sm: 0.875rem, base: 1rem, lg: 1.25rem, xl: 1.75rem, 2xl: 2.5rem, 3xl: 4rem}
  lineHeight: {body: 1.55, heading: 1.05}
rounded: {none: 0, sm: <px>, md: <px>, pill: 999px}
spacing: {1: 4px, 2: 8px, 3: 12px, 4: 16px, 6: 24px, 8: 32px, 12: 48px, 16: 64px}
shadow: {raised: "<tinted shadow>", none: none}
motion:
  durations: {instant: 120ms, quick: 200ms, moment: <ms>}
  easing: {standard: "<cubic-bezier>", emphasized: "<cubic-bezier>"}
breakpoints: {sm: 390px, md: 768px, lg: 1024px, xl: 1440px}
---

## Overview
<2-3 sentences: subject, audience, the one idea that makes this design its own.>

## Colors
- **bg (#...)**: <role, where used>
- **accent (#...)**: <the only driver of interaction | ...>

## Typography
<roles, scale use, treatments allowed (cropping, width axis), what never happens>

## Layout
<grid, alignment, density, ASCII wireframe of the key screen>

## Surfaces & components
<radius by hierarchy, borders vs shadows, buttons, inputs, cards/lists, nav, empty/error states>

## Motion
- Focal moment: <the one authored sequence, or "none">
- Feedback: <what acknowledges actions, durations>
- Continuity: <state/navigation transitions>
- Reduced motion: <what replaces each animation>

## Voice
<copy tone, verbs for main actions, words never used>

## Do / Don't
- Do: ...
- Don't: ...

## Deliberate exceptions
<anti-slop traits kept on purpose + why; design-lint rules waived>

## Changelog
- v1: <direction chosen, why>
- v2: <feedback → change>
