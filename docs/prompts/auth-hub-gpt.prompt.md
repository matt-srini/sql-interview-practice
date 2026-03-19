# GPT-Optimized Auth Hub Prompt

```text
Use English.

You are a senior full-stack product engineer working inside an existing production-style codebase. Implement a production-grade authentication hub for an app that uses React/Vite on the frontend and FastAPI on the backend.

Your task is to build a modern login and account-access experience that supports all of the following methods in one cohesive auth entry point:
- email/password
- Google OAuth
- Apple sign-in
- GitHub OAuth
- magic link

Primary goals:
- Deliver a polished, modern, premium-feeling authentication experience.
- Preserve the existing project architecture, routing patterns, and visual language.
- Make only minimal, surgical changes.
- Do not introduce new frameworks or unnecessary abstractions.

Functional requirements:
- Include clear flows or entry points for:
  - Sign in
  - Create account
  - Continue with Google
  - Continue with Apple
  - Continue with GitHub
  - Continue with magic link
  - Forgot password
- If backend auth endpoints for some providers do not exist yet, still implement the frontend in a production-ready way with clean integration boundaries, placeholders, or adapter functions. Do not invent unstable backend contracts.
- The result should work as a unified auth hub, not as a plain single-form login page.

Security requirements:
- Prevent account-enumeration leaks.
- Use generic authentication failure messages.
- Use password-manager-friendly field naming and form behavior.
- Do not store sensitive auth data insecurely in localStorage unless there is a strong technical reason and it is explicitly explained.
- Handle loading, retry, failure, and disabled states safely and clearly.
- Avoid misleading success states.

Accessibility requirements:
- Use semantic markup.
- Support keyboard-only navigation.
- Provide visible focus states.
- Use screen-reader-friendly labels and status messaging.
- Ensure strong contrast and readable validation feedback.
- Do not rely on color alone for errors or important state.

Design requirements:
- The page must feel intentional and premium, not generic boilerplate.
- It should look strong on both desktop and mobile.
- Reuse the project’s existing styling direction where appropriate, but make the auth page feel like a deliberate front door to the product.
- Avoid bland layouts and default-looking component-library patterns.

Implementation instructions:
- First inspect the existing frontend structure and determine the best route, page, and component placement.
- Reuse existing conventions where possible.
- Add small supporting utilities only if needed.
- Do not break existing routes or app behavior.
- If backend auth support is absent, create a clean frontend API abstraction that can later be wired to real endpoints.

Output instructions:
Return your answer in exactly this structure:
1. Context assumptions
2. Implementation plan
3. Files to create or modify
4. Security and UX decisions
5. Complete code changes

Quality bar:
- Optimize for correctness, maintainability, accessibility, and production readiness.
- Prefer direct implementation over high-level discussion.
- Keep explanations concise but technically explicit.
- Use low creativity and high precision.
```