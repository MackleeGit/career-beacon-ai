// src/pages/Landing.jsx
import React from 'react';

export default function Landing({ onSelectRole, onSignIn }) {
  return (
    <div className="landing-page" style={{ minHeight: '100svh', display: 'flex', flexDirection: 'column' }}>
      {/* Top Navbar */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'hsla(224, 20%, 7%, 0.85)',
          backdropFilter: 'blur(12px)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          style={{
            maxWidth: '1100px',
            margin: '0 auto',
            padding: '16px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div className="logo-mark">
            <div className="logo-mark__icon">CB</div>
            <span style={{ fontWeight: 700, fontSize: '1.15rem', letterSpacing: '-0.02em' }}>
              Career Beacon
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={onSignIn}
              style={{ fontWeight: 600 }}
            >
              Sign In
            </button>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={() => onSelectRole('learner')}
              style={{ fontWeight: 600 }}
            >
              Get Started
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section
        style={{
          flex: '1 0 auto',
          maxWidth: '1100px',
          margin: '0 auto',
          padding: '64px 24px 48px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          textAlign: 'center',
        }}
      >
        {/* Academic / Research Badge */}
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '6px 14px',
            background: 'hsla(258, 90%, 66%, 0.12)',
            border: '1px solid var(--accent-border)',
            borderRadius: 'var(--r-full)',
            fontSize: '0.82rem',
            fontWeight: 600,
            color: 'var(--accent-light)',
            marginBottom: '24px',
          }}
        >
          <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent)' }} />
          Dual Semantic Recommendation Framework
        </div>

        <h1
          style={{
            fontSize: 'clamp(2.2rem, 5vw, 3.4rem)',
            fontWeight: 800,
            lineHeight: 1.15,
            letterSpacing: '-0.03em',
            maxWidth: '850px',
            marginBottom: '20px',
          }}
        >
          Bridge Skill Gaps with <span className="gradient-text">Precision Micro-Learning</span> &amp; Verified Mentorship
        </h1>

        <p
          style={{
            fontSize: 'clamp(1rem, 2vw, 1.18rem)',
            color: 'var(--text-secondary)',
            maxWidth: '680px',
            lineHeight: 1.6,
            marginBottom: '48px',
          }}
        >
          Map your career ambitions directly against labor-market taxonomies.
          Master bite-sized lessons filtered by three quality gates, and connect with industry mentors.
        </p>

        {/* Dual Pathway Cards (Learner vs Mentor) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: '24px',
            width: '100%',
            maxWidth: '860px',
            marginBottom: '56px',
            textAlign: 'left',
          }}
        >
          {/* Card 1: Learner */}
          <div
            className="card"
            style={{
              padding: '32px 28px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              border: '1px solid hsla(258, 90%, 66%, 0.3)',
              background: 'linear-gradient(180deg, var(--bg-surface) 0%, hsla(224, 18%, 13%, 0.8) 100%)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: 'var(--r-md)',
                  background: 'hsla(258, 90%, 66%, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.4rem',
                  marginBottom: '18px',
                }}
              >
                🎓
              </div>
              <h2 style={{ fontSize: '1.35rem', marginBottom: '8px' }}>I'm a Learner</h2>
              <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
                Search any target career. Calibrate your baseline skill graph, take atomized micro-quizzes, and track mastery toward industry standards.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <li style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: 'var(--teal)' }}>✓</span> 384-dimensional vector skill matching
                </li>
                <li style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: 'var(--teal)' }}>✓</span> 3-gate noise-filtered technical tutorials
                </li>
                <li style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: 'var(--teal)' }}>✓</span> Direct 1-on-1 booking when you get stuck
                </li>
              </ul>
            </div>
            <button
              type="button"
              className="btn btn--primary"
              style={{ width: '100%', padding: '12px' }}
              onClick={() => onSelectRole('learner')}
            >
              Get Started as Learner →
            </button>
          </div>

          {/* Card 2: Mentor */}
          <div
            className="card"
            style={{
              padding: '32px 28px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              border: '1px solid var(--border)',
              background: 'linear-gradient(180deg, var(--bg-surface) 0%, hsla(224, 18%, 13%, 0.8) 100%)',
              position: 'relative',
              overflow: 'hidden',
            }}
          >
            <div>
              <div
                style={{
                  width: '44px',
                  height: '44px',
                  borderRadius: 'var(--r-md)',
                  background: 'hsla(174, 72%, 56%, 0.15)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '1.4rem',
                  marginBottom: '18px',
                }}
              >
                🧑‍🏫
              </div>
              <h2 style={{ fontSize: '1.35rem', marginBottom: '8px' }}>I'm a Mentor</h2>
              <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '20px' }}>
                Share your real-world engineering and domain expertise. Answer semantically matched Q&amp;As and hold 1-on-1 advisory sessions.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <li style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: 'var(--teal)' }}>✓</span> LinkedIn profile credential verification
                </li>
                <li style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: 'var(--teal)' }}>✓</span> Google Calendar &amp; Meet automated dispatch
                </li>
                <li style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ color: 'var(--teal)' }}>✓</span> Targeted mentee pairing via skill vectors
                </li>
              </ul>
            </div>
            <button
              type="button"
              className="btn btn--secondary"
              style={{ width: '100%', padding: '12px' }}
              onClick={() => onSelectRole('mentor')}
            >
              Join as an Industry Mentor →
            </button>
          </div>
        </div>

        {/* Architecture & Trust Badges */}
        <div
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'center',
            gap: '24px',
            color: 'var(--text-muted)',
            fontSize: '0.88rem',
            borderTop: '1px solid var(--border)',
            paddingTop: '28px',
            width: '100%',
          }}
        >
          <span>⚡ FastEmbed ONNX</span>
          <span>•</span>
          <span>🛡️ Supabase pgvector HNSW</span>
          <span>•</span>
          <span>📊 O*NET &amp; ESCO Taxonomies</span>
          <span>•</span>
          <span>🤝 Verified Mentorship Network</span>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border)',
          padding: '24px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.82rem',
        }}
      >
        Career Beacon • Capstone Research Project • Strathmore University School of Computing
      </footer>
    </div>
  );
}

