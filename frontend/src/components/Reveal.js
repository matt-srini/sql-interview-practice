import { useRef, useState, useEffect } from 'react';

// ── Shared hooks ────────────────────────────────────────────────────────────
export function useInView(ref, margin = '-8%') {
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) setInView(true); },
      { rootMargin: margin, threshold: 0.05 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return inView;
}

// ── Section entrance animation wrapper ─────────────────────────────────────
export function Reveal({ children, delay = 0, className = '' }) {
  const ref = useRef(null);
  const inView = useInView(ref);
  return (
    <div
      ref={ref}
      className={`lp-reveal${inView ? ' is-visible' : ''} ${className}`}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
