import '@testing-library/jest-dom/vitest';
import { vi, afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

// @testing-library/react auto-cleanup checks `typeof afterEach === 'function'`
// in its own module scope.  Without `globals: true` in vitest config, `afterEach`
// is not injected globally, so the auto-cleanup silently never registers.
// Register it explicitly here so the DOM is cleared between every test.
afterEach(cleanup);

vi.mock('react-helmet-async', () => ({
	Helmet: ({ children }) => children ?? null,
	HelmetProvider: ({ children }) => children,
}));
