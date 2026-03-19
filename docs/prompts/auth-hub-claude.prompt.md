# Claude-Optimized Auth Hub Prompt

```text
Use English.

You are an expert senior engineer making careful, production-quality changes inside an existing React/Vite frontend and FastAPI backend application.

Implement a complete authentication hub that supports:
- email/password
- Google OAuth
- Apple sign-in
- GitHub OAuth
- magic link

You must treat this as an in-repo implementation task, not a greenfield demo.

What to build:
- A modern, cohesive auth entry experience that acts as the app’s front door.
- Clear user paths for:
  - Sign in
  - Create account
  - Continue with Google
  - Continue with Apple
  - Continue with GitHub
  - Send magic link
  - Forgot password

Constraints:
- Preserve the existing architecture, routing structure, and visual language.
- Do not introduce new frameworks.
- Do not do broad refactors.
- Make the smallest set of changes necessary for a production-grade result.
- If some auth providers are not yet implemented on the backend, create clean frontend seams and placeholders without fabricating backend behavior.

Security expectations:
- No account enumeration.
- Generic failure states for authentication errors.
- Password-manager-compatible login form behavior.
- No insecure storage of tokens or secrets.
- Clear handling for loading, pending, disabled, error, and success states.
- Avoid exposing backend internals in UI messages.

Accessibility expectations:
- Semantic HTML and accessible forms.
- Keyboard navigability throughout.
- Visible focus styling.
- Clear labels, helper text, and screen-reader-friendly announcements.
- Strong contrast and readable error handling.
- Validation must not rely on color alone.

Design expectations:
- Premium, modern, and intentional.
- Responsive across desktop and mobile.
- Not generic, not template-like, not visually flat.
- Should feel consistent with the app while still elevating the auth entry experience.

Execution approach:
- Inspect the existing frontend structure before coding.
- Decide the correct route, page placement, and component boundaries based on the current app.
- Reuse existing patterns where sensible.
- Add only the minimal utilities or API wrappers required.
- If backend support is missing, implement stable adapter points for future integration.

Be concrete and implementation-oriented.
Do not stop at planning.
Provide the actual code changes.

Return your response in this exact format:
1. Context assumptions
2. Implementation plan
3. Files to create or modify
4. Security and UX decisions
5. Complete code changes

Additional instruction:
When making design or architecture choices, prefer the most conservative change that still achieves a polished, production-grade outcome.
```