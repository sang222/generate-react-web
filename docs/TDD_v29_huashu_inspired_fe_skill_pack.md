# TDD v29 - Huashu-Inspired FE Skill Pack

## Goal
Improve FE agent output quality by adding skill-focused, data-backed, output-specific frontend skills inspired by Huashu-style skill design.

## Non-Goals
- Do not copy HTML-only prototype workflow.
- Do not introduce commercial assets.
- Do not let FE agent choose arbitrary CSS/UI frameworks.
- Do not weaken production constraints, API integrity, or existing-project scope safety.

## Added Skills
- `fe-design-direction`
- `fe-ui-implementation`
- `fe-visual-review`

## Support Packs
- `fe-style-packs/*`
- `fe-data-ui`

## Protocol
1. FE story should get design direction before FE implementation.
2. FE implementation must follow selected direction, design tokens, component plan, framework policy, and anti-slop rules.
3. FE visual review checks visual hierarchy, layout, brand/project consistency, interaction quality, implementation fit, framework misuse, and AI slop.

## Runtime Integration in v29
v29 adds the skill packs and wires FE-specific resources into prompt resource loading for FE developer/reviewer roles. Full hard orchestrator state transition can be added later as a dedicated FE design flow.

## Framework Policy
- Existing project: reuse existing styling/component system.
- New React web: Tailwind + tokens by default.
- React Native: StyleSheet + tokens by default; NativeWind only if present or allowed.
- Framer Motion only when motion has user purpose.
- Heavy UI libraries require approval.
