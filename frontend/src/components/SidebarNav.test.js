import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { MemoryRouter, Route, Routes, useParams } from 'react-router-dom';
import SidebarNav from './SidebarNav';

function QuestionStub() {
  const { id } = useParams();
  return <div>Question {id}</div>;
}

function renderWithRouter(ui, { initialEntries = ['/'] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/practice" element={ui} />
        <Route path="/practice/questions/:id" element={<QuestionStub />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('SidebarNav', () => {
  it('collapses and expands a difficulty group', async () => {
    const user = userEvent.setup();
    const catalog = {
      user_id: 'u1',
      groups: [
        {
          difficulty: 'easy',
          counts: { total: 2, solved: 0, unlocked: 1 },
          questions: [
            { id: 1, title: 'Q1', difficulty: 'easy', order: 1, state: 'unlocked', is_next: true },
            { id: 2, title: 'Q2', difficulty: 'easy', order: 2, state: 'locked', is_next: false },
          ],
        },
      ],
    };

    function Harness() {
      const [collapsedByDiff, setCollapsedByDiff] = useState({ easy: true });
      return (
        <SidebarNav
          catalog={catalog}
          collapsedByDiff={collapsedByDiff}
          toggleDiff={(diff) => setCollapsedByDiff((prev) => ({ ...prev, [diff]: !prev[diff] }))}
          onNavigate={() => {}}
        />
      );
    }

    renderWithRouter(<Harness />, { initialEntries: ['/practice'] });

    expect(screen.getByText('easy')).toBeInTheDocument();
    expect(screen.queryByText('1. Q1')).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /easy/i }));
    expect(screen.getByText('1. Q1')).toBeInTheDocument();
  });

  it('does not render locked questions as links and navigates on unlocked click', async () => {
    const user = userEvent.setup();

    const catalog = {
      user_id: 'u1',
      groups: [
        {
          difficulty: 'easy',
          counts: { total: 2, solved: 0, unlocked: 1 },
          questions: [
            { id: 1, title: 'Second Highest Salary', difficulty: 'easy', order: 1, state: 'unlocked', is_next: true },
            { id: 2, title: 'Duplicate Emails', difficulty: 'easy', order: 2, state: 'locked', is_next: false },
          ],
        },
      ],
    };

    renderWithRouter(
      <SidebarNav
        catalog={catalog}
        collapsedByDiff={{ easy: false }}
        toggleDiff={() => {}}
        onNavigate={() => {}}
      />,
      { initialEntries: ['/practice'] }
    );

    // Locked question should not be a link
    const lockedRow = screen.getByText('2. Duplicate Emails').closest('.sidebar-question');
    expect(lockedRow).toHaveAttribute('aria-disabled', 'true');

    // Unlocked question should navigate
    await user.click(screen.getByText('1. Second Highest Salary'));
    expect(await screen.findByText('Question 1')).toBeInTheDocument();
  });
});
