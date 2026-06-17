/**
 * DrillSidebar states (2026-06-17).
 *
 * Guards the concept-drill sidebar against the infinite-loading regression: when the
 * /practice/drill fetch finishes with no data (e.g. a Free user's 403, or a transient
 * error), the sidebar must show a finite "Drill unavailable" fallback — NOT shimmer
 * forever. (AppShell separately makes ?drill= inert for Free/anonymous, so this state
 * is reached only on a real fetch failure for a Pro user.)
 */
import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { DrillSidebar } from './AppShell';

const meta = { color: '#D94F3D', label: 'PySpark' };
const renderDS = (props) => render(
  <MemoryRouter>
    <DrillSidebar topic="pyspark" meta={meta} drillConcept="SCHEMA & TYPE HANDLING" onNavigate={() => {}} {...props} />
  </MemoryRouter>
);

afterEach(cleanup);

describe('DrillSidebar', () => {
  it('shows a loading shimmer while the drill is loading', () => {
    const { container } = renderDS({ drillLoading: true, drillData: null });
    expect(container.querySelector('.path-sidebar-loading')).toBeTruthy();
    expect(container.querySelector('.path-sidebar--drill')).toBeFalsy();
  });

  it('shows a finite fallback — not an infinite shimmer — when the fetch returns no data', () => {
    const { container } = renderDS({ drillLoading: false, drillData: null });
    expect(container.querySelector('.path-sidebar-loading')).toBeFalsy(); // the bug being guarded
    expect(screen.getByText(/Drill unavailable/i)).toBeTruthy();
  });

  it('renders the scoped question list + progress when drill data is present', () => {
    const drillData = {
      concept: 'Schema & Type Handling',
      questions: [
        { id: 41003, title: 'RDD vs DataFrame', state: 'unlocked' },
        { id: 41010, title: 'Casting columns', state: 'solved' },
      ],
    };
    const { container } = renderDS({ drillLoading: false, drillData });
    expect(container.querySelector('.path-sidebar--drill')).toBeTruthy();
    expect(screen.getByText('RDD vs DataFrame')).toBeTruthy();
    expect(screen.getByText(/1\/2 cleared/)).toBeTruthy();
  });
});
