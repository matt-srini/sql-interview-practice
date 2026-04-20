export default function Skeleton({ as = 'div', className = '', width, height, style, ...rest }) {
  const Element = as;
  const mergedStyle = {
    ...(width ? { width } : {}),
    ...(height ? { height } : {}),
    ...(style || {}),
  };

  return <Element className={`skeleton-block skeleton-shimmer ${className}`.trim()} style={mergedStyle} {...rest} />;
}
