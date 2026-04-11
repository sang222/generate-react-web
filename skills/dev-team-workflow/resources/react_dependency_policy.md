# React Dependency Policy

- Keep dependencies minimal.
- Do not add optional UI/performance libraries unless explicitly required.
- Do not use deprecated or React-incompatible libraries.
- Do not use `react-virtualized` in React 18+ projects.
- If list virtualization is explicitly required, prefer `react-window`.
- For simple apps like todo apps, do not add any virtualization library.
