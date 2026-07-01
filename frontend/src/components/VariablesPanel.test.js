import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import VariablesPanel from './VariablesPanel';

afterEach(cleanup);

describe('VariablesPanel', () => {
  it('renders nothing when dataframes is empty', () => {
    const { container } = render(<VariablesPanel dataframes={{}} schema={{}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders variable rows for normal string values', () => {
    const { container } = render(
      <VariablesPanel
        dataframes={{ df_users: 'users.csv' }}
        schema={{ df_users: ['user_id', 'email'] }}
      />
    );
    expect(container.querySelector('.variable-name').textContent).toBe('df_users');
    expect(container.querySelector('.variable-source').textContent).toBe('users.csv');
    const tokens = [...container.querySelectorAll('.variable-column-token')].map((t) => t.textContent);
    expect(tokens).toEqual(['user_id', 'email']);
  });

  it('does not throw when a schema column is an object — coerces safely', () => {
    expect(() => {
      render(
        <VariablesPanel
          dataframes={{ df_test: 'test.csv' }}
          schema={{ df_test: [{ description: 'x' }, 'normal_col'] }}
        />
      );
    }).not.toThrow();
  });

  it('does not throw when a dataframe value is an object — coerces safely', () => {
    expect(() => {
      render(
        <VariablesPanel
          dataframes={{ df_test: { name: 'weird.csv' } }}
          schema={{ df_test: ['col_a'] }}
        />
      );
    }).not.toThrow();
  });

  it('coerces an object column using the name property when available', () => {
    const { container } = render(
      <VariablesPanel
        dataframes={{ df_test: 'data.csv' }}
        schema={{ df_test: [{ name: 'my_col' }] }}
      />
    );
    const tokens = [...container.querySelectorAll('.variable-column-token')].map((t) => t.textContent);
    expect(tokens).toEqual(['my_col']);
  });
});
