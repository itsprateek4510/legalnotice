/**
 * Reusable card component.
 * Renders a titled card with optional icon, children content, and an optional
 * "warning" tone that applies a highlighted style.
 */
export default function ResultCard({
  title,
  icon,
  tone = "default",
  children,
}) {
  const className = `card card-${tone}`;
  return (
    <section className={className}>
      <h2 className="card-title">
        {icon && <span className="card-icon" aria-hidden="true">{icon}</span>}
        {title}
      </h2>
      <div className="card-body">{children}</div>
    </section>
  );
}