import { describe, it, expect } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import BrandMark from './BrandMark';

afterEach(cleanup);

describe('BrandMark', () => {
  it('renders the mark as inline SVG — never an <img> that can fail to fetch', () => {
    // Regression guard for the recurring "logo missing" prod-blocker: the mark used
    // to be <img src="/branding/mark-no-bg.svg">, a runtime fetch that broke on any
    // server blip / moved file / SPA-fallback mis-serve. Inline SVG = zero network.
    const { container } = render(<BrandMark />);
    expect(container.querySelector('img')).toBeNull();
    const svg = container.querySelector('svg.brand-mark-img');
    expect(svg).not.toBeNull();
  });

  it('draws the two-rect monogram with the theme-keyed classes', () => {
    const { container } = render(<BrandMark />);
    const rects = container.querySelectorAll('svg rect');
    expect(rects.length).toBe(2);
    expect(container.querySelector('rect.brand-mark-primary')).not.toBeNull();
    expect(container.querySelector('rect.brand-mark-secondary')).not.toBeNull();
    // Light fills are baked in as attributes so the mark renders even if CSS fails.
    expect(container.querySelector('rect.brand-mark-primary').getAttribute('fill')).toBe('#166534');
  });

  it('stays decorative (aria-hidden) and merges an extra className', () => {
    const { container } = render(<BrandMark className="x-extra" />);
    const svg = container.querySelector('svg');
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.classList.contains('brand-mark-img')).toBe(true);
    expect(svg.classList.contains('x-extra')).toBe(true);
  });
});
