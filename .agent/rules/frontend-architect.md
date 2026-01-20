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

## 2. State Management Strategy
- **Server State**: Use **TanStack Query (React Query)** for all API data fetching, caching, and synchronization.
- **Client State**:
  - **Component Local**: `useState` / `useReducer` for state that doesn't leave the component.
  - **Shared Global**: React Context for strictly cross-cutting data (Auth, Tenant Context, Theme).
- **Isolation**: Avoid complex global state stores (Redux/Zustand) unless a specific cross-module interaction requires it.

## 3. Design System & UX
- **Theme**: Controlled via a centralized `ThemeContext` or Tailwind config.
- **Components**: Use atomic design principles. Core UI components (Buttons, Modals) reside in `src/core/components`.
- **Consistency**: All pages must follow the `AdminLayout` or `PublicLayout` patterns.

## 4. API Layer
- **Client Generation**: All domain-specific logic must use the `b2bDomainClient` or equivalent.
- **Aggregation**: Routers/Pages should not call multiple granular services if a backend "Aggregator" endpoint can be created.
