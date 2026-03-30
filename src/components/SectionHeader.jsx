export default function SectionHeader({ eyebrow, title, text }) {
  return (
    <header className="section-header">
      {eyebrow ? <span className="section-header__eyebrow">{eyebrow}</span> : null}
      <h2>{title}</h2>
      {text ? <p>{text}</p> : null}
    </header>
  );
}
