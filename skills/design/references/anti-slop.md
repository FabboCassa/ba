# Anti-slop reference

Synthesised from anthropics/skills `frontend-design`, Leonxlnx/taste-skill, pbakaus/impeccable,
Nutlope/hallmark, nextlevelbuilder/ui-ux-pro-max-skill (ideas only, no text copied).
A trait below is allowed only when the brief asks for it or DESIGN.md records why.

## Looks that read as "made by an AI"
- Warm cream ground + high-contrast serif + terracotta/clay accent.
- Near-black ground with ONE acid-green / vermilion / cyan accent.
- Purple→pink or indigo→violet gradients, gradient text, gradient blobs behind everything.
- Broadsheet pastiche: hairline rules, zero radius, dense newspaper columns, for any subject.
- SaaS card kit: content chopped into identical rounded cards, one radius everywhere, the same
  soft grey shadow under each, bento grid as default layout.
- Glass panels stacked on glass panels.
- Template chrome: tracked ALL-CAPS eyebrow above every heading, `A · B · C` meta strings,
  `WORD — fragment` labels, monospace for small labels, `→` appended to every link/button,
  numbered markers 01/02/03 on content that is not a sequence.
- One word in the headline italicised or coloured.
- Hero = big number + small label + three stats + gradient accent.
- Emoji as icons, generic line icons for everything, stock "abstract 3D shapes".
- Inter/Roboto/Poppins/Montserrat/Arial chosen by default; Space Grotesk + Space Mono pairing.

## Motion that reads as generated
- Fade-and-slide-up on every section; hover lift on every card; parallax on everything.
- Many scattered effects instead of ONE authored moment.
- Page-load choreography that makes users wait on a working screen (apps, dashboards).

## Copy that reads as generated
- "Unlock / Elevate / Supercharge / Seamless / Effortless / Cutting-edge / Empower".
- Buttons named "Get started", "Learn more", "Submit" when a specific verb exists.
- Invented metrics, fake logos, fake testimonials.

## Where distinctiveness actually comes from
1. **The subject**: its materials, vernacular, tools, places, era. A tide-table app and a
   jewellery atelier must not share a palette, type or layout.
2. **One bold thing**: spend boldness in one place (type, colour, layout OR motion); keep the rest quiet.
3. **Type as image**: scale, width axes, cropping, rhythm. Two families max, clearly distinct.
4. **Colour by role**: 4-6 named tokens with roles (ground, surface, ink, muted, accent, accent2).
   Tint shadows with the palette, never neutral grey.
5. **Structure = information**: borders, numbers, labels only when they encode something.
6. **Motion with a job**: acknowledge an action, explain a state change, keep continuity, or one
   focal moment. Write the motion thesis before code.

## Quality floor (never shipped below)
- WCAG AA contrast for text (4.5:1, large 3:1); visible keyboard focus.
- `prefers-reduced-motion` path for every animation.
- Works at 390, 768, 1024, 1440 widths; no horizontal scroll; line length < 80ch.
- Real content from the brief; nothing invented that a user could mistake for fact.

## Self-check before building (answer in writing, privately)
- "If I got a similar brief tomorrow, would I produce this same plan?" If yes, change the axis
  that would repeat.
- Remove one accessory before shipping.
