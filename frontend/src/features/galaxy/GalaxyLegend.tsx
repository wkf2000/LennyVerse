export function GalaxyLegend() {
  return (
    <aside className="galaxy-panel galaxy-legend" aria-label="Galaxy legend">
      <h2 className="galaxy-panel__title">Legend</h2>
      <ul className="galaxy-legend__list">
        <li>
          <span className="galaxy-legend__dot galaxy-legend__dot--size" aria-hidden /> Size reflects influence — bigger bodies pull more weight in the archive.
        </li>
        <li>
          <span className="galaxy-legend__dot galaxy-legend__dot--glow" aria-hidden /> Brightness tracks signal strength — the hottest stars are the brightest ideas.
        </li>
        <li>
          <span className="galaxy-legend__dot galaxy-legend__dot--edge" aria-hidden /> Lines are semantic bridges between related documents.
        </li>
      </ul>
    </aside>
  );
}
