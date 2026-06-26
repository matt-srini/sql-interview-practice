// Flat ESLint config — intentionally minimal.
//
// Its single job is to enforce the React Rules of Hooks at lint/CI time. That is
// the static guard that would have caught the SchemaViewer "Rendered fewer hooks
// than expected" crash (a useMemo sat below an early return). We deliberately do
// NOT pull in a broad ruleset (eslint:recommended, no-unused-vars, etc.) so that
// `npm run lint` cannot fail CI on pre-existing style nits unrelated to this guard
// — rules-of-hooks is the one invariant we hold the line on.
import reactHooks from 'eslint-plugin-react-hooks';

export default [
  {
    files: ['src/**/*.{js,jsx}'],
    plugins: { 'react-hooks': reactHooks },
    languageOptions: {
      ecmaVersion: 'latest',
      sourceType: 'module',
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // Hard error: a hook called conditionally / after an early return crashes
      // the app at runtime. This is the recurrence guard for the mock SchemaViewer
      // hooks-count crash.
      'react-hooks/rules-of-hooks': 'error',
      // Advisory only: missing-dependency hints are useful but not crash-class, and
      // the codebase has intentional `eslint-disable-line` opt-outs. Warnings do not
      // fail CI (no --max-warnings), so this stays informative without blocking.
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
];
