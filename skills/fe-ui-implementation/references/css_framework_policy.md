# CSS / UI Framework Policy

## Existing project
- Reuse the existing styling approach.
- Do not introduce a new framework.
- Do not mix styling systems unless already present.

## New React web project
Preferred default:
- Tailwind CSS
- CSS variables or token file for design tokens

Allowed lightweight helpers when needed:
- clsx
- tailwind-merge
- class-variance-authority
- lucide-react
- framer-motion only when motion has user-purpose

## React Native
Preferred default:
- StyleSheet + shared design tokens

Allowed only if existing or explicitly allowed:
- NativeWind
- Tamagui
- React Native Paper

## Block
Block or escalate if implementation requires:
- adding a large UI framework without approval
- replacing existing styling system
- mixing Tailwind with MUI/AntD randomly
- adding animation library for decorative-only motion
