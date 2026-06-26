import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import SchemaViewer from './SchemaViewer';

afterEach(() => { cleanup(); });

describe('SchemaViewer', () => {
  it('renders table and column content for a non-empty schema', () => {
    render(<SchemaViewer schema={{ users: ['user_id', 'email'] }} />);
    expect(screen.getByText('users')).toBeInTheDocument();
    expect(screen.getByText('user_id')).toBeInTheDocument();
  });

  it('does not throw and renders nothing when rerendered with an empty schema (regression: "Rendered fewer hooks than expected")', () => {
    // Reproduces the production crash: a mock session's sticky SchemaViewer
    // component transitions from a schema-bearing question to a schema-less one
    // on the SAME mounted instance. Before the fix, the filteredSchema useMemo
    // was called AFTER the early `if (schemaEntries.length === 0) return null`
    // guard, so React saw fewer hooks on the empty-schema render than on the
    // non-empty one and threw "Rendered fewer hooks than expected."
    const { rerender, container } = render(<SchemaViewer schema={{ users: ['user_id', 'email'] }} />);
    expect(() => rerender(<SchemaViewer schema={{}} />)).not.toThrow();
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when schema is an empty object from the first render', () => {
    const { container } = render(<SchemaViewer schema={{}} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when no schema prop is provided', () => {
    const { container } = render(<SchemaViewer />);
    expect(container).toBeEmptyDOMElement();
  });
});
