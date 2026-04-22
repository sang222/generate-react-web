# FE UI Implementation Good / Bad Examples

## Good
- Reuses existing Button/Card/Table primitives.
- Implements selected tokens through existing Tailwind/theme variables.
- Touches only `frontend/src/features/orders/**` for an orders story.
- Uses real API contract props or leaves integration boundary explicit.

## Bad
- Adds MUI to a Tailwind project without approval.
- Creates fake revenue stats because dashboard looks empty.
- Rewrites shared layout for a local screen change.
- Uses gradient glass cards unrelated to the design direction.
