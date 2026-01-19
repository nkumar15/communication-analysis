# Frontend Architecture Rules

## Scope
Owned by: **Frontend Architect**
Applies to: **UI Architecture, React Patterns, State Management**

## 1. Directory Structure
- **Module Based**: `frontend/src/modules/{module}/web/`
- **Standard Layers**:
  - `pages/`: Route handlers. minimal logic.
  - `components/`: Presentational components.
  - `layouts/`: Page wrappers (Sidebar, Header).
  - `services/`: API clients (TanStack Query hooks).
- **Isolation Boundaries**:
  - **B2B vs B2C**: Strict isolation. Components in `modules/b2b` MUST NOT import from `modules/b2c` and vice versa.
  - **Shared Components**: Common UI/logic must exist in `src/core/` or `src/shared/` and be imported from there.

## 2. State Management
- **Server State**: Use **TanStack Query (React Query)** for all API data.
- **Client State**:
  - **Local**: `useState` / `useReducer` for component-local state.
  - **Global**: React Context for strictly global data (Auth, Theme).
- **Anti-Pattern**: Do NOT use Redux/Zustand unless complex cross-component state is strictly necessary.

## 3. UI/UX Design System
- **Styling**: TailwindCSS (Utility-first). Avoid inline styles.
- **Components**: Build small, focused, reusable components.
- **Responsiveness**: Mobile-first approach using Tailwind breakpoints (`md:`, `lg:`).

## 4. API Integration
- **Client Generation**: Use typed API clients.
- **Error Handling**: Centralized error interceptor (Toast notifications).
- **Loading States**: Skeletons or Spinners for all async operations.
