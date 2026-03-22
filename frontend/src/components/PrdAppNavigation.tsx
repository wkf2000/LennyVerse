/**
 * Placeholder navigation aligned with docs/prd.md — links are inactive until each feature ships.
 */

export function PrdAppNavigation() {
  return (
    <header className="lv-app-header">
      <div className="lv-app-header__brand">
        <span className="lv-wordmark">LennyVerse</span>
        <span className="lv-app-header__tagline">AI-powered product wisdom</span>
      </div>
      <nav className="lv-prd-nav" aria-label="Product areas (placeholders)">
        <NavSection
          title="Explore"
          items={[
            { code: "VIZ-1", label: "Knowledge Galaxy", current: true },
            { code: "VIZ-2", label: "Concept Map" },
            { code: "VIZ-3", label: "Timeline Explorer" },
            { code: "VIZ-4", label: "Guest Network" },
          ]}
        />
        <NavSection
          title="Discover"
          items={[
            { code: "DSC-1", label: "Semantic Search" },
            { code: "DSC-2", label: "Framework Library" },
            { code: "DSC-3", label: "Guest Profiles" },
            { code: "DSC-4", label: "Decision Advisor" },
            { code: "DSC-5", label: "Topic Deep Dives" },
          ]}
        />
        <NavSection
          title="Learn"
          items={[
            { code: "LRN-1", label: "Learning Paths" },
            { code: "LRN-2", label: "Quizzes" },
            { code: "LRN-3", label: "Mastery Dashboard" },
            { code: "LRN-4", label: "Flashcards" },
            { code: "LRN-5", label: "Study Mode" },
          ]}
        />
        <NavSection
          title="Teach"
          items={[
            { code: "TCH-1", label: "Curriculum Builder" },
            { code: "TCH-2", label: "Assessment Generator" },
            { code: "TCH-3", label: "Case Study Packager" },
            { code: "TCH-4", label: "Cohort Dashboard" },
            { code: "TCH-5", label: "Lesson Plan Export" },
          ]}
        />
        <NavSection
          title="Engage"
          items={[
            { code: "ENG-1", label: "Wisdom of the Day" },
            { code: "ENG-2", label: "Bookmarks & Collections" },
            { code: "ENG-3", label: "Lenny's Take Digest" },
          ]}
        />
      </nav>
    </header>
  );
}

function NavSection({
  title,
  items,
}: {
  title: string;
  items: { code: string; label: string; current?: boolean }[];
}) {
  return (
    <details className="lv-nav-section">
      <summary className="lv-nav-section__summary">
        <span>{title}</span>
        <span className="lv-nav-section__chev" aria-hidden>
          ▾
        </span>
      </summary>
      <ul className="lv-nav-section__list">
        {items.map((item) => (
          <li key={item.code}>
            {item.current ? (
              <span className="lv-nav-item lv-nav-item--current" aria-current="page">
                <span className="lv-nav-item__code">{item.code}</span>
                {item.label}
              </span>
            ) : (
              <button type="button" className="lv-nav-item lv-nav-item--soon" disabled title={`${item.label} — coming soon`}>
                <span className="lv-nav-item__code">{item.code}</span>
                <span className="lv-nav-item__label">{item.label}</span>
                <span className="lv-nav-item__badge">Soon</span>
              </button>
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}
