import '@testing-library/jest-dom/vitest';
import { vi } from 'vitest';

vi.mock('react-helmet-async', () => ({
	Helmet: ({ children }) => children ?? null,
	HelmetProvider: ({ children }) => children,
}));
