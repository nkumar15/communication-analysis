# ReactJS Developer Rules

## Scope
Owned by: **Senior React Developer**
Applies to: **Component Implementation, Hooks, CSS**

## 1. Core Engineering Principles
- **DRY (Don't Repeat Yourself)**: Extract reusable logic into Custom Hooks (`useMyLogic`) and UI into Components.
- **Component Reusability**: If a UI pattern appears twice, make it a shared component in `components/`.
- **Unidirectional Data Flow**: State flows DOWN. Events flow UP. Avoid complex prop drilling (use Context if > 3 layers).


## 2. Functional Components
- **Mechanism**: Use Function Components + Hooks. **NO** Class components.
- **Props**: Destructure props in function signature.
- **Memoization**: Use `useMemo` and `useCallback` for expensive operations or stable dependencies.

## 3. Hooks Rules
- **Naming**: Custom hooks must start with `use`.
- **Top Level**: Only call hooks at the top level of functions.
- **Dependencies**: Exhaustive dependency arrays for `useEffect` / `useMemo`.

## 4. Component Organization
- **One Component Per File**: Unless very small and tightly coupled.
- **Exports**: Named exports preferred over default exports (`export const MyComponent...`).
- **Imports**: Absolute imports from `src/` preferred.

## 5. Testing
- **Unit**: Jest + React Testing Library.
- **Scope**: Test behavior (user interactions), not implementation details.
- **Mocking**: Mock API calls using MSW or Jest mocks.
