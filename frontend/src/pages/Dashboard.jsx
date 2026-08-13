// src/pages/Dashboard.jsx
import { useState } from 'react';
import { supabase } from '../lib/SupabaseClient';

const LEVEL_LABEL = { 20: 'Novice', 50: 'Intermediate', 80: 'Advanced', 100: 'Mastered' };

function getLevel(score) {
  if (score >= 100) return { label: 'Mastered',     color: 'var(--teal)' };
  if (score >= 80)  return { label: 'Advanced',     color: 'var(--accent-light)' };
  if (score >= 50)  return { label: 'Intermediate', color: 'hsl(38,90%,60%)' };
  return             { label: 'Novice',             color: 'var(--text-muted)' };
}

function SkillCard({ skill }) {
  const { label, color } = getLevel(skill.proficiency);
  return (
    <div
      style={{
        padding: '14px 16px',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{skill.name}</div>
          {skill.category && (
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>{skill.category}</div>
          )}
        </div>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, color, whiteSpace: 'nowrap' }}>{label}</span>
      </div>

      <div className="progress-bar">
        <div className="progress-bar__fill" style={{ width: `${skill.proficiency}%` }} />
      </div>
    </div>
  );
}

export default function Dashboard({ user, career, skills }) {
  const [signingOut, setSigningOut] = useState(false);

  const handleSignOut = async () => {
    setSigningOut(true);
    await supabase.auth.signOut();
  };

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Learner';

  // Compute aggregate progress
  const avgProgress = skills.length
    ? Math.round(skills.reduce((sum, s) => sum + s.proficiency, 0) / skills.length)
    : 0;

  const masteredCount = skills.filter((s) => s.proficiency >= 100).length;

  return (
    <>
      {/* Background decoration */}
      <div className="bg-orb bg-orb--1" />
      <div className="bg-orb bg-orb--2" />

      <div style={{ minHeight: '100svh', padding: '24px', position: 'relative', zIndex: 1 }}>
        {/* ── Top bar ── */}
        <header
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            maxWidth: '860px',
            margin: '0 auto 40px',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div className="logo-mark">
            <div className="logo-mark__icon">🧭</div>
            Career Beacon
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              {user?.email}
            </span>
            <button
              id="sign-out-btn"
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={handleSignOut}
              disabled={signingOut}
            >
              {signingOut ? 'Signing out…' : 'Sign out'}
            </button>
          </div>
        </header>

        {/* ── Main content ── */}
        <main className="container--wide">
          {/* Welcome + career banner */}
          <div className="card" style={{ marginBottom: '24px', textAlign: 'left' }}>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                flexWrap: 'wrap',
                gap: '16px',
                marginBottom: '24px',
              }}
            >
              <div>
                <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500 }}>
                  WELCOME BACK
                </p>
                <h2 style={{ marginBottom: '4px' }}>
                  Hello, <span className="gradient-text">{displayName}</span> 👋
                </h2>
                <p style={{ fontSize: '0.9rem' }}>
                  Your target career:{' '}
                  <strong style={{ color: 'var(--text-primary)' }}>{career?.title ?? '—'}</strong>
                </p>
              </div>

              <div
                style={{
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  padding: '16px 20px',
                  minWidth: '160px',
                  textAlign: 'center',
                }}
              >
                <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-light)', lineHeight: 1 }}>
                  {avgProgress}%
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Avg. proficiency
                </div>
              </div>
            </div>

            {/* Overall progress bar */}
            <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              <span>Overall progress</span>
              <span>{masteredCount} / {skills.length} mastered</span>
            </div>
            <div className="progress-bar" style={{ height: '8px' }}>
              <div className="progress-bar__fill" style={{ width: `${avgProgress}%` }} />
            </div>
          </div>

          {/* Skill Graph */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px', flexWrap: 'wrap', gap: '8px' }}>
              <h3>Your Skill Graph</h3>
              <span className="badge badge--accent">{skills.length} skills tracked</span>
            </div>

            {skills.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '32px 0' }}>
                No skills found. Something may have gone wrong — try refreshing.
              </p>
            ) : (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))',
                  gap: '12px',
                }}
              >
                {skills.map((skill) => (
                  <SkillCard key={skill.id} skill={skill} />
                ))}
              </div>
            )}
          </div>

          {/* Coming soon teaser */}
          <div
            style={{
              marginTop: '24px',
              padding: '20px 24px',
              borderRadius: 'var(--r-lg)',
              border: '1px dashed var(--border)',
              display: 'flex',
              alignItems: 'center',
              gap: '16px',
              background: 'var(--bg-surface)',
            }}
          >
            <span style={{ fontSize: '1.5rem' }}>🔮</span>
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '2px' }}>
                Personalised learning feed — coming soon
              </div>
              <p style={{ fontSize: '0.85rem', margin: 0 }}>
                Micro-content and mentor recommendations tailored to your skill gaps will appear here.
              </p>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
