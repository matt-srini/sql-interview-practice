import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export default function OnboardingTooltip({ isOpen, steps, onClose }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [anchorRect, setAnchorRect] = useState(null);
  const scrollTimerRef = useRef(null);

  const totalSteps = steps?.length ?? 0;
  const step = totalSteps > 0 ? steps[stepIndex] : null;

  // Reset on close
  useEffect(() => {
    if (!isOpen) {
      setStepIndex(0);
      setAnchorRect(null);
    }
  }, [isOpen]);

  // Scroll target into view then measure its position
  useEffect(() => {
    if (!isOpen || !step?.targetSelector) {
      setAnchorRect(null);
      return;
    }

    const target = document.querySelector(step.targetSelector);
    if (!target) {
      setAnchorRect(null);
      return;
    }

    // Scroll smoothly to the target
    target.scrollIntoView({ behavior: 'smooth', block: 'start' });

    // Measure after scroll settles (smooth scroll takes ~400–600ms)
    clearTimeout(scrollTimerRef.current);
    scrollTimerRef.current = setTimeout(() => {
      const t = document.querySelector(step.targetSelector);
      if (t) setAnchorRect(t.getBoundingClientRect());
    }, 500);

    // Also update on resize / manual scroll
    const updateRect = () => {
      const t = document.querySelector(step.targetSelector);
      if (t) setAnchorRect(t.getBoundingClientRect());
    };
    window.addEventListener('resize', updateRect);
    window.addEventListener('scroll', updateRect, true);

    return () => {
      clearTimeout(scrollTimerRef.current);
      window.removeEventListener('resize', updateRect);
      window.removeEventListener('scroll', updateRect, true);
    };
  }, [isOpen, step]);

  // Highlight the target element
  useEffect(() => {
    if (!isOpen || !step?.targetSelector) return undefined;
    const target = document.querySelector(step.targetSelector);
    if (!target) return undefined;
    target.classList.add('onboarding-target-active');
    return () => target.classList.remove('onboarding-target-active');
  }, [isOpen, step]);

  // Escape to close
  useEffect(() => {
    if (!isOpen) return undefined;
    const onKey = (e) => { if (e.key === 'Escape') onClose?.(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [isOpen, onClose]);

  if (!isOpen || !step || totalSteps === 0 || typeof document === 'undefined') return null;

  const PANEL_W = 320;
  const PANEL_H = 200;
  const GAP = 14;
  const MARGIN = 16;
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  let top, left;

  if (anchorRect) {
    // For tall targets (taller than ~40% of viewport), anchor below the first
    // visible slice rather than below the bottom edge — otherwise the tooltip
    // falls out of view or is pushed to the very bottom.
    const TALL_THRESHOLD = vh * 0.4;
    const isTall = anchorRect.height > TALL_THRESHOLD;
    const anchorBottom = isTall
      ? clamp(anchorRect.top + 80, anchorRect.top, anchorRect.bottom)
      : anchorRect.bottom;

    const spaceBelow = vh - anchorBottom;
    const spaceAbove = isTall ? anchorRect.top : anchorRect.top;
    if (spaceBelow >= PANEL_H + GAP || spaceBelow >= spaceAbove) {
      top = clamp(anchorBottom + GAP, MARGIN, vh - PANEL_H - MARGIN);
    } else {
      top = clamp(anchorRect.top - PANEL_H - GAP, MARGIN, vh - PANEL_H - MARGIN);
    }
    left = clamp(anchorRect.left, MARGIN, vw - PANEL_W - MARGIN);
  } else {
    top = Math.round((vh - PANEL_H) / 2);
    left = Math.round((vw - PANEL_W) / 2);
  }

  const canGoBack = stepIndex > 0;
  const isLastStep = stepIndex === totalSteps - 1;

  function goNext() {
    if (isLastStep) { onClose?.(); return; }
    setAnchorRect(null);
    setStepIndex((i) => i + 1);
  }

  function goBack() {
    setAnchorRect(null);
    setStepIndex((i) => Math.max(0, i - 1));
  }

  return createPortal(
    <div className="onboarding-layer" aria-live="polite">
      <div className="onboarding-backdrop" onClick={() => onClose?.()} />
      <section
        className="onboarding-tooltip"
        role="dialog"
        aria-modal="true"
        aria-label="Quick walkthrough"
        style={{ top: `${top}px`, left: `${left}px` }}
      >
        <div className="onboarding-tooltip-header">
          <span className="onboarding-tooltip-step">Step {stepIndex + 1} of {totalSteps}</span>
          <button
            type="button"
            className="onboarding-tooltip-skip"
            onClick={() => onClose?.()}
            aria-label="Skip walkthrough"
          >
            Skip
          </button>
        </div>
        <h3 className="onboarding-tooltip-title">{step.title}</h3>
        <p className="onboarding-tooltip-copy">{step.body}</p>
        <div className="onboarding-tooltip-actions">
          <button
            type="button"
            className="btn btn-secondary btn-compact"
            onClick={goBack}
            disabled={!canGoBack}
          >
            Back
          </button>
          <button
            type="button"
            className="btn btn-primary btn-compact"
            onClick={goNext}
          >
            {isLastStep ? 'Got it' : 'Next'}
          </button>
        </div>
      </section>
    </div>,
    document.body
  );
}
