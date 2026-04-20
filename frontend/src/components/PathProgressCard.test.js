import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PathProgressCard from './PathProgressCard';

function renderCard(path, compact = false) {
  return render(
    <MemoryRouter>
      <PathProgressCard path={path} compact={compact} />
    </MemoryRouter>
  );
}

describe('PathProgressCard', () => {
  it('renders pro-gated CTA when path is inaccessible', () => {
    renderCard({
      slug: 'delta-lake-patterns',
      title: 'Delta Lake Patterns',
      description: 'Learn Delta fundamentals.',
      topic: 'pyspark',
      tier: 'pro',
      role: 'advanced',
      question_count: 7,
      solved_count: 0,
      accessible: false,
    });

    expect(screen.getByText('Pro')).toBeInTheDocument();
    expect(screen.getByText('Unlock with Pro →')).toBeInTheDocument();
    expect(screen.getByText('7 questions')).toBeInTheDocument();
    expect(screen.getByText('0/7')).toBeInTheDocument();
  });

  it('renders continue CTA for started free path', () => {
    renderCard({
      slug: 'joins-and-filtering',
      title: 'Joins & Filtering Mastery',
      description: 'Join patterns from basics to advanced.',
      topic: 'sql',
      tier: 'free',
      role: 'advanced',
      question_count: 7,
      solved_count: 2,
      accessible: true,
    });

    expect(screen.getByText('Continue →')).toBeInTheDocument();
    expect(screen.getByText('2/7')).toBeInTheDocument();
    expect(screen.queryByText('Included with Free')).not.toBeInTheDocument();
  });

  it('hides description in compact mode', () => {
    renderCard(
      {
        slug: 'time-series-analysis',
        title: 'Time Series Analysis',
        description: 'Practice rolling windows and resample workflows.',
        topic: 'python-data',
        tier: 'free',
        role: 'advanced',
        question_count: 6,
        solved_count: 0,
        accessible: true,
      },
      true
    );

    expect(screen.queryByText('Practice rolling windows and resample workflows.')).not.toBeInTheDocument();
    expect(screen.getByText('Start path →')).toBeInTheDocument();
  });
});
