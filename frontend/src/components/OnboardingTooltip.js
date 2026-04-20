import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

export default function OnboardingTooltip({ isOpen, steps, onClose }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [anchorRect, setAnchorRect] = useState(null);

  const totalSteps = steps?.length ?? 0;
  const step = useMemo(() => (totalSteps > 0 ? steps[stepIndex] : null), [stepIndex, steps, totalSteps]);

  useEffect(() => {
    if (!isOpen) {
      setStepIndex(0);
      setAnchorRect(null);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !step?.targetSelector) return undefined;

    const updatePosition = () => {
      const target = document.querySelector(step.targetSelector);
      if (!target) {
        setAnchorRect(null);
        return;
      }
      setAnchorRect(target.getBoundingClientRect());
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);
    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [isOpen, step]);

  useEffect(() => {
    if (!isOpen || !step?.targetSelector) return undefined;
    const target = document.querySelector(step.targetSelector);
    if (!target) return undefined;
    target.classList.add('onboarding-target-active');
    return () => target.classList.remove('onboarding-target-active');
  }, [isOpen, step]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        onClose?.();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen || !step || totalSteps === 0 || typeof document === 'undefined') {
    return null;
  }

  const panelWidth = 320;
  const panelHeight = 190;
  const fallbackTop = Math.max(20, Math.round((window.innerHeight - panelHeight) / 2));
  const fallbackLeft = Math.max(16, Math.round((window.innerWidth - panelWidth) / 2));

  const top = anchorRect
    ? clamp(anchorRect.bottom + 12, 20, window.innerHeight - panelHeight - 12)
    : fallbackTop;
  const left = anchorRect
    ? clamp(anchorRect.left, 16, window.innerWidth - panelWidth - 16)
    : fallbackLeft;

  const canGoBack = stepIndex > 0;
  const isLastStep = stepIndex === totalSteps - 1;

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
            onClick={() => setStepIndex((index) => Math.max(0, index - 1))}
            disabled={!canGoBack}
          >
            Back
          </button>
          <button
            type="button"
            className="btn btn-primary btn-compact"
            onClick={() => {
              if (isLastStep) onClose?.();
              else setStepIndex((index) => Math.min(totalSteps - 1, index + 1));
            }}
          >
            {isLastStep ? 'Got it' : 'Next'}
          </button>
        </div>
      </section>
    </div>,
    document.body
  );
}
