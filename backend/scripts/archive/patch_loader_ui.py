file_path = "frontend/src/pages/Recommendations.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

old_loader = """      {/* Loading State with Progressive Generation Pipeline */}
      {isCurrentTabLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} aria-busy="true" aria-label="Synthesizing learning recommendations">
          <div
            className="card"
            style={{
              padding: '24px',
              border: '1px solid var(--accent-border)',
              background: 'var(--surface)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '3px',
                background: 'linear-gradient(90deg, var(--accent) 0%, var(--status-info) 50%, var(--accent) 100%)',
                backgroundSize: '200% 100%',
                animation: 'pulse 1.8s ease-in-out infinite',
              }}
            />
            <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
              <div
                style={{
                  width: '40px',
                  height: '40px',
                  borderRadius: 'var(--r-md)',
                  background: 'var(--accent-soft)',
                  color: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <Compass size={20} />
              </div>
              <div style={{ flex: 1 }}>
                <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>
                  Curating Daily Focus Drop for {career?.title || 'your occupational roadmap'}
                </h4>
                <p style={{ margin: '4px 0 0', fontSize: '0.83rem', color: 'var(--text-secondary)' }}>
                  Aligning verified instructional resources with your assessed skill frontier...
                </p>
              </div>
            </div>

            <div style={{ marginTop: '16px' }}>
              <div className="progress-bar" style={{ height: '4px', overflow: 'hidden' }}>
                <div
                  className="progress-bar__fill"
                  style={{
                    width: '100%',
                    background: 'linear-gradient(90deg, var(--accent) 0%, var(--status-info) 50%, var(--accent) 100%)',
                    backgroundSize: '200% 100%',
                    animation: 'pulse 1.4s ease-in-out infinite',
                  }}
                />
              </div>
            </div>
          </div>

          <FeedCardSkeleton count={3} />
        </div>
      )}"""

new_loader = """      {/* Loading State with Progressive Generation Pipeline */}
      {isCurrentTabLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} aria-busy="true" aria-label="Curating daily focus drop">
          <div
            className="card"
            style={{
              padding: '24px',
              border: '1px solid var(--accent-border)',
              background: 'var(--surface)',
              position: 'relative',
              overflow: 'hidden',
              borderRadius: 'var(--r-lg)',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '3px',
                background: 'linear-gradient(90deg, var(--accent) 0%, var(--status-info) 50%, var(--accent) 100%)',
                backgroundSize: '200% 100%',
                animation: 'pulse 1.8s ease-in-out infinite',
              }}
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: 'var(--r-md)',
                    background: 'var(--accent-soft)',
                    color: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Compass size={22} className="spinning" />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                    <span className="badge badge--accent" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                      {PIPELINE_STEPS[pipelinePhase].badge}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Curating 3-Lesson Daily Drop</span>
                  </div>
                  <h4 style={{ margin: 0, fontSize: '1.02rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {PIPELINE_STEPS[pipelinePhase].title}
                  </h4>
                </div>
              </div>

              {/* Stage Progress Pills */}
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', background: 'var(--surface-sunken)', padding: '5px 10px', borderRadius: 'var(--r-full)', border: '1px solid var(--border-subtle)' }}>
                {PIPELINE_STEPS.map((step, idx) => (
                  <div
                    key={idx}
                    style={{
                      width: idx === pipelinePhase ? '24px' : '8px',
                      height: '8px',
                      borderRadius: 'var(--r-full)',
                      background: idx <= pipelinePhase ? 'var(--accent)' : 'var(--border-strong)',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                    title={step.title}
                  />
                ))}
              </div>
            </div>

            <p style={{ margin: '0 0 16px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {PIPELINE_STEPS[pipelinePhase].subtitle}
            </p>

            <div className="progress-bar" style={{ height: '4px' }}>
              <div
                className="progress-bar__fill"
                style={{
                  width: `${((pipelinePhase + 1) / 3) * 100}%`,
                  transition: 'width 0.4s ease',
                  background: 'var(--accent)',
                }}
              />
            </div>
          </div>

          <FeedCardSkeleton count={3} />
        </div>
      )}"""

code_norm = code.replace('\r\n', '\n')
old_norm = old_loader.replace('\r\n', '\n')
new_norm = new_loader.replace('\r\n', '\n')

assert old_norm in code_norm, "Old loader block not found!"
code_norm = code_norm.replace(old_norm, new_norm, 1)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code_norm)

print("Upgraded progressive loader JSX installed successfully!")

