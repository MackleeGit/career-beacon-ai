import os

# 1. Patch Dashboard.jsx
dash_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "pages", "Dashboard.jsx")
with open(dash_path, "r", encoding="utf-8") as f:
    dash_text = f.read()

dash_text = dash_text.replace(
    "const [feedInitialSubTab, setFeedInitialSubTab] = useState('sprint');",
    "const [feedInitialSubTab, setFeedInitialSubTab] = useState('daily');"
)
dash_text = dash_text.replace(
    "const navigateTo = (tab, subTab = 'sprint') => {",
    "const navigateTo = (tab, subTab = 'daily') => {"
)
dash_text = dash_text.replace(
    "Open your Learning Feed to load your next 10-lesson sprint.",
    "Open your Learning Feed to complete today's Daily Focus Drop."
)
dash_text = dash_text.replace(
    "navigateTo('feed', 'sprint')",
    "navigateTo('feed', 'daily')"
)

with open(dash_path, "w", encoding="utf-8") as f:
    f.write(dash_text)
print("Patched Dashboard.jsx")

# 2. Patch Landing.jsx
landing_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "pages", "Landing.jsx")
with open(landing_path, "r", encoding="utf-8") as f:
    landing_text = f.read()

landing_text = landing_text.replace(
    "Select a target occupation, calibrate your baseline skill graph, and progress through focused 10-lesson learning sprints.",
    "Select a target occupation, calibrate your baseline skill graph, and progress through focused daily learning drops."
)

with open(landing_path, "w", encoding="utf-8") as f:
    f.write(landing_text)
print("Patched Landing.jsx")

# 3. Patch Recommendations.jsx
rec_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "pages", "Recommendations.jsx")
with open(rec_path, "r", encoding="utf-8") as f:
    rec_text = f.read()

# Replace SPRINT_SIZE
rec_text = rec_text.replace("const SPRINT_SIZE = 10;", "// SPRINT_SIZE legacy removed")

# Replace feedSubTab initial state
rec_text = rec_text.replace(
    "const [feedSubTab, setFeedSubTab] = useState(initialSubTab); // 'sprint' | 'completed' | 'saved'",
    "const [feedSubTab, setFeedSubTab] = useState(initialSubTab && initialSubTab !== 'sprint' ? initialSubTab : 'daily');"
)

# Replace initialSubTab effect
rec_text = rec_text.replace(
    """  useEffect(() => {
    if (initialSubTab) {
      setFeedSubTab(initialSubTab);
    }
  }, [initialSubTab]);""",
    """  useEffect(() => {
    if (initialSubTab) {
      setFeedSubTab(initialSubTab === 'sprint' ? 'daily' : initialSubTab);
    }
  }, [initialSubTab]);"""
)

# Remove the sprint load more button block
target_sprint_block = """          <div ref={loadMoreSentinelRef} aria-hidden="true" style={{ height: '1px' }} />
          {feedSubTab === 'sprint' && (
            <div style={{ textAlign: 'center', padding: '22px 16px' }}>
              {loadingMore && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
                  <FeedCardSkeleton count={2} />
                  <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: '8px', color: 'var(--text-secondary)', fontSize: '0.86rem' }}>
                    <div
                      style={{
                        width: '14px',
                        height: '14px',
                        borderRadius: '50%',
                        border: '2px solid var(--accent)',
                        borderTopColor: 'transparent',
                        animation: 'spin 0.8s linear infinite',
                      }}
                    />
                    <span>Loading next sprint modules...</span>
                  </div>
                </div>
              )}
              {loadMoreError && (
                <p role="alert" style={{ color: 'var(--status-danger)', marginBottom: '10px', fontSize: '0.86rem' }}>
                  {loadMoreError}
                </p>
              )}
              {!loadingMore && (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={loadMoreRecommendations}
                >
                  <RotateCcw size={14} />
                  <span>{loadMoreError ? 'Retry Loading Sprint' : 'Load Next 10-Lesson Sprint'}</span>
                </button>
              )}
            </div>
          )}"""

if target_sprint_block in rec_text:
    rec_text = rec_text.replace(target_sprint_block, "")
    print("Removed sprint block (LF)")
elif target_sprint_block.replace("\n", "\r\n") in rec_text:
    rec_text = rec_text.replace(target_sprint_block.replace("\n", "\r\n"), "")
    print("Removed sprint block (CRLF)")
else:
    print("Target sprint block not found directly, checking sub-string...")

with open(rec_path, "w", encoding="utf-8") as f:
    f.write(rec_text)
print("Finished patching Recommendations.jsx")
