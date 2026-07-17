# Frontend – Vue 3 + Vite + Vuetify

A modern, scalable frontend built with Vue 3 (Composition API), Vite, and Vuetify 3.
Strong emphasis on clean architecture, reusability, and maintainable styling.

## Tech Stack

- **Framework:** Vue 3 (Composition API + `<script setup>`)
- **Build Tool:** Vite
- **UI Library:** Vuetify 3 (Material Design 3)
- **State Management:** Pinia
- **Routing:** Vue Router 4
- **HTTP Client:** Axios (wrapped in service modules)
- **Styling:** CSS custom properties, SCSS (for Vuetify overrides), global utilities

## Folder Structure

```
src/
|- assets/            # Static assets (images, fonts, etc.)
|     |- css          # Project's global CSS files and Variables
|     |- img          # Images to be shipped with code ( we'll remove these soon )
|- components/        # Reusable UI components
|     |- common/      # Generic, app-agnostic components (AppButton, AppCard, AppBar, AppFooter ...)
|     |- layout/      # Structural components (HeroSection, TieredItems ...)
|     |- view/        # View specific Components (These Components should be made in rare cases
|         |- auth/    # only when layout components aren't Sufficient)
|         |- donate/
|- config/
|     |- types/       # Config type(s) for typescript
|     |- defaults/    # Default configs
|- layouts/           # UI layout that can render multiple views
|     |- TenantLayout.vue
|     |- PublicAdmin.vue
|     |- ...
|- plugins/           # Plugin setup (vuetify, etc.)
|- router/            # Vue Router configuration
|     |- index.js
|     |- public.ts    # Un-authenticated routes
|     |- private.ts   # Authenticated routes
|- services/          # API layer and external integrations
|     |- api.js       # Axios instance + interceptors
|     |- authService.ts
|     |- brandingService.ts
|     |- ...
|- stores/            # Pinia stores (global state management)
|     |- authStore.ts
|     |- brandingStore.ts
|     |- uiStore.ts
|     |- ...
|- views/             # Page‑level components (routed)
|     |- HomeView.vue
|     |- DonateView.vue
|     |- ...
|- App.vue            # Root component (layout shell)
|- main.js            # Application entry point
```

## Core Conventions

### 1. CSS and Static Assets

**CSS/SCSS:**

- Use Vuetify classes for CSS, use custom CSS as last resort, order for usage:
  1.  _Veutify utility classes_ (Spacing, typography, colors, flexbox ...) 2. _Vuetify Component props_ (Dense, outlined, elevation ...)
  2.  _Global SCSS variables_ overriding theme (colors, fonts, breakpoints ...)
  3.  _Custom Scoped CSSS_ (complex animation, unique brand elements ...)
- All styling follows a design‑token first approach to ensure dark theme support out‑of‑the‑box.
- Declare all the css variables in a common place only, Ex: `assets/css/variables.css`
- Custom CSS should be scoped to the component only.

> Before applying any style/css, go over this checklist:
>
> - Can Vuetify utility class do this? → Use it
> - Can Vuetify prop do this? → Use prop
> - Can SCSS variable do this? → Override in settings.scss
> - Is this a complex animation? → Write scoped CSS
> - Is this a brand gradient/pattern? → Write scoped CSS
> - Am I repeating the same custom style? → Create global utility once

<br/>

**Images:**

- Avoid using images, try using icon's wherever you can.
- If an image is needed, do not put in code, get the image from a static store using urls.

### 2. Components

Components should follow a three tier architecture, Generic components, Layout components, View Components. Components should be configurable with defaults to reduce code bloat. Components should never handle business logic, if some business logic is to be added for a components behaviour just emit it and handle in the view. Favor generic, composable components `(<AppButton>, <AppModal>)` over ad‑hoc, one‑off implementations.
**Generic Components:**

- These should consist only app agnostic very dumb components.
- They shouldn't be aware of any positioning, their only concer should be what and how big this looks like.
- Ex: AppButton, AppCard, AppBar, AppFooter etc.

**Layout Components:**

- These Components should combine multiple Generic Components, and generate a chunck that can be directly used by a view or a View Component.
- They should configure which component sits where and how it looks.
- They should handle most of the needs for views.
- Ex: HeroSection, TieredItems, etc.

**View Components:**

- These Components should be created only in deseprate times. Ex: Forms
- They can be overrides, or combine of multiple Layout Components.
- Convention is to create a dir in name of the view and add inside that. Ex: `components/view/donate/DonateForm.vue`

### 3. Conf (App Configuration)

- Configuration's control what text or PR content to show, what styles to apply and what behaviour's to invoke.
- This consist of two directories: types and defaults.
  - Types decalre Typescript types for that config, this gives the base for someone else to use you'r components.
  - Defaults contain deafult config, this will rarely be used, mostly the config will come from backend only. Its there so that we have something to show on UI instead of empty UI.

### 4. Layouts

- These are the root level components after `App.vue`
- Using this we can have multiple UI layout's over different routes.
- Ex: Public Site will look entirely different from private site, then we can have two layouts, that can utilize same components and views (if need be).

### 5. Router

- Router houses all you'r UI routes and logic assossiated with them.
- Lazy‑load route components for performance.
- Use nested routes where a view acts as a layout shell.
- index.js only handle's routing logic and custom route level overrides.
- Actual routes reside in public.ts, private.ts, etc.
  - **public.ts:** un- authenticated public routes.
  - **private.ts:** authenticated private routes.

### 6. Services

- All external communication is handled through dedicated service modules.
- Place Axios configuration, base URL, interceptors, and error handling in services/api.js.
- Create feature‑specific services (e.g., services/userService.js) that only import the Axios instance.
- Never use fetch or axios directly in components or stores.

### 7. Stores

- Handle Pinia Store
- Avoid keeping big or sensitive data inside store.
- Stores only orchestrate data: calling services, caching, and exposing reactive state.
- Components read state via store getters/state and dispatch actions; no direct API calls.

### 8. Views

- Consumed by Layouts they keep the entire strucutre of currently rendered page.
- They can use mulitple Layout or View Components providing them their configurations to tweak them.
- They handle and store all the business logic.
