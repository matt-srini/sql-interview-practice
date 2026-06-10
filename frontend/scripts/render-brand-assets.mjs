/**
 * render-brand-assets.mjs
 * Rasterizes brand SVG sources to PNG at exact pixel sizes using Playwright.
 * Run from the frontend/ directory: node scripts/render-brand-assets.mjs
 */

import { readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

// Support both @playwright/test and playwright imports
let chromium;
try {
  ({ chromium } = await import('@playwright/test'));
} catch {
  ({ chromium } = await import('playwright'));
}

const __dirname = dirname(fileURLToPath(import.meta.url));
const publicDir = resolve(__dirname, '../public');

const TARGETS = [
  { output: 'favicon-16.png',       source: 'favicon.svg',        width: 16,   height: 16,  colorScheme: 'dark'  },
  { output: 'favicon-32.png',       source: 'favicon.svg',        width: 32,   height: 32,  colorScheme: 'dark'  },
  { output: 'favicon-48.png',       source: 'favicon.svg',        width: 48,   height: 48,  colorScheme: 'dark'  },
  { output: 'favicon-light-16.png', source: 'favicon.svg',        width: 16,   height: 16,  colorScheme: 'light' },
  { output: 'favicon-light-32.png', source: 'favicon.svg',        width: 32,   height: 32,  colorScheme: 'light' },
  { output: 'favicon-light-48.png', source: 'favicon.svg',        width: 48,   height: 48,  colorScheme: 'light' },
  { output: 'apple-touch-icon.png', source: 'icon-maskable.svg',  width: 180,  height: 180, colorScheme: 'dark'  },
  { output: 'icon-192.png',         source: 'icon-maskable.svg',  width: 192,  height: 192, colorScheme: 'dark'  },
  { output: 'icon-512.png',         source: 'icon-maskable.svg',  width: 512,  height: 512, colorScheme: 'dark'  },
  { output: 'og-image.png',         source: 'og-image.svg',       width: 1200, height: 630, colorScheme: 'dark'  },
  { output: 'og-image-light.png',   source: 'og-image-light.svg', width: 1200, height: 630, colorScheme: 'light' },
];

const browser = await chromium.launch();

for (const { output, source, width, height, colorScheme = 'dark' } of TARGETS) {
  const isOG = source.startsWith('og-image');
  const svgText = readFileSync(resolve(publicDir, source), 'utf8');

  // Strip the XML declaration so the inline SVG is valid HTML
  const svgMarkup = svgText.replace(/<\?xml[^?]*\?>\s*/g, '');

  // Force the SVG element to exact pixel dimensions
  const inlinedSvg = svgMarkup.replace(
    /(<svg\b[^>]*)\s+(width="[^"]*"\s+height="[^"]*")/,
    `$1 width="${width}px" height="${height}px" style="width:${width}px;height:${height}px;display:block"`
  );

  let head = '';
  if (isOG) {
    head = `
      <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;700&display=swap" rel="stylesheet" />
    `;
  }

  const html = `<!DOCTYPE html>
<html>
  <head>
    <meta charset="UTF-8" />
    ${head}
    <style>*, *::before, *::after { box-sizing: border-box; } html, body { margin: 0; padding: 0; overflow: hidden; }</style>
  </head>
  <body style="margin:0;padding:0;background:#000">
    ${inlinedSvg}
  </body>
</html>`;

  const page = await browser.newPage();
  await page.emulateMedia({ colorScheme });
  await page.setViewportSize({ width, height, deviceScaleFactor: 1 });
  await page.setContent(html, { waitUntil: 'networkidle' });

  if (isOG) {
    try {
      await page.evaluate(() => document.fonts.ready);
      await page.waitForTimeout(400);
    } catch {
      // If font wait fails (e.g. no network), proceed — SVG has system-sans fallback
    }
  }

  const outputPath = resolve(publicDir, output);
  await page.screenshot({ path: outputPath, clip: { x: 0, y: 0, width, height } });
  await page.close();

  console.log(`✓ ${output.padEnd(24)} ${width}×${height}  →  ${outputPath}`);
}

await browser.close();
console.log('\nAll brand assets rendered successfully.');
