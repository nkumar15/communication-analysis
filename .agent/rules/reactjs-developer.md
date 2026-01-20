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

## 3. Hooks & State Patterns
- **Naming**: Custom hooks must start with `use`.
- **Top Level**: Only call hooks at the top level of functions.
- **Dependencies**: Exhaustive dependency arrays for `useEffect` / `useMemo`.
- **Query Hooks**: API calls MUST be wrapped in `useQuery` or `useMutation`.

## 4. Component Implementation
- **One Component Per File**: Unless very small and tightly coupled.
- **Exports**: Named exports preferred over default exports (`export const MyComponent...`).
- **Imports**: Absolute imports from `src/` preferred.
- **Styling**: TailwindCSS (Utility-first). Avoid inline styles unless dynamic (e.g., animations).
- **Responsiveness**: Use Tailwind breakpoints (`md:`, `lg:`) for mobile-first layouts.

## 5. UI Feedback & Errors
- **Loading**: Use Skeletons for page loads and Spinners for button actions.
- **Toasts**: Use `toast.error()` for API failures via centralized interceptors.
- **Validation**: Use Formik/Yup or React Hook Form for client-side validation.

## 6. Testing Strategy
- **Framework**: Vitest + React Testing Library.
- **Focus**: Test user-visible behavior (e.g., "click button -> show modal") rather than state internals.
- **Mocks**: Use MSW (Mock Service Worker) for network-level mocking.

## 7. Security & Secrets
- **Credential Safety**: Never hardcode API keys or secrets in the frontend. If a secret is needed (e.g., Firebase config), check `.env.example` and prompt the user.
- **Exposure**: NEVER expose sensitive backend secrets to the frontend.
