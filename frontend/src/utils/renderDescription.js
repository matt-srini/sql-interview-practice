/**
 * Render a question description string that may contain:
 *   - Fenced code blocks (```...```)
 *   - Inline backtick code (`...`)
 *   - Bold text (**...**)
 *   - Paragraph breaks (\n\n)
 *
 * Returns an array of React nodes suitable for rendering inside a <p>.
 */
export function renderDescription(text) {
  if (!text) return null;
  const parts = text.split(/(```[\s\S]*?```)/g);
  return parts.map((part, i) => {
    if (part.startsWith('```') && part.endsWith('```')) {
      const code = part.slice(3, -3).replace(/^\n/, '');
      return (
        <pre key={i} className="description-code-block">
          <code>{code}</code>
        </pre>
      );
    }
    // Inline backticks and **bold**
    const segments = part.split(/(`[^`]+`|\*\*[^*]+\*\*)/g);
    const inline = segments.map((seg, j) => {
      if (seg.startsWith('`') && seg.endsWith('`')) {
        return <code key={j} className="description-inline-code">{seg.slice(1, -1)}</code>;
      }
      if (seg.startsWith('**') && seg.endsWith('**')) {
        return <strong key={j}>{seg.slice(2, -2)}</strong>;
      }
      return seg;
    });
    // Preserve paragraph breaks (\n\n) as visual spacing
    const withBreaks = [];
    inline.forEach((seg, j) => {
      if (typeof seg === 'string') {
        const lines = seg.split(/\n\n+/);
        lines.forEach((line, k) => {
          withBreaks.push(line);
          if (k < lines.length - 1) {
            withBreaks.push(<br key={`br-${i}-${j}-${k}a`} />);
            withBreaks.push(<br key={`br-${i}-${j}-${k}b`} />);
          }
        });
      } else {
        withBreaks.push(seg);
      }
    });
    return <span key={i}>{withBreaks}</span>;
  });
}
