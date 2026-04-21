import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { sentryVitePlugin } from '@sentry/vite-plugin';

const backendTarget = process.env.VITE_BACKEND_URL || 'http://localhost:8000';
const sentryAuthToken = process.env.SENTRY_AUTH_TOKEN;
const sentryOrg = process.env.SENTRY_ORG;
const sentryProject = process.env.SENTRY_PROJECT;
const sentryRelease = process.env.SENTRY_RELEASE || process.env.RAILWAY_GIT_COMMIT_SHA;

const plugins = [react()];

if (sentryAuthToken && sentryOrg && sentryProject) {
  plugins.push(
    sentryVitePlugin({
      authToken: sentryAuthToken,
      org: sentryOrg,
      project: sentryProject,
      telemetry: false,
      release: sentryRelease ? { name: sentryRelease } : undefined,
      sourcemaps: {
        assets: './dist/**',
      },
    })
  );
}

export default defineConfig({
  plugins,
  build: {
    sourcemap: 'hidden',
  },
  esbuild: {
    loader: 'jsx',
    include: /src\/.*\.js$/,
    exclude: [],
  },
  optimizeDeps: {
    esbuildOptions: {
      loader: {
        '.js': 'jsx',
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': backendTarget,
    },
  },

  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    exclude: ['**/node_modules/**', '**/e2e/**'],
  },
});
