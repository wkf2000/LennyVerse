export function GalaxyLegend() {
  return (
    <aside className="galaxy-status" aria-label="Galaxy legend">
      <h2>Legend</h2>
      <ul>
        <li>Node size: higher influence score means larger stars.</li>
        <li>Node brightness: stronger influence renders brighter stars.</li>
        <li>Edge opacity: baseline relationship visibility for constellation context.</li>
      </ul>
    </aside>
  );
}
