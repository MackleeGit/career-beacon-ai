// src/pages/Dashboard.jsx
import { useState } from 'react';
import { supabase } from '../lib/SupabaseClient';
import Toast from '../components/Toast';
import Recommendations from './Recommendations';
import LearnerMentorship from './LearnerMentorship';

function getLevel(score) {
  if (score >= 100) return { label: '100% estimate', color: 'var(--teal)' };
  if (score >= 80) return { label: 'Advanced', color: 'var(--accent-light)' };
  if (score >= 50) return { label: 'Intermediate', color: 'hsl(38,90%,60%)' };
  return { label: 'Novice', color: 'var(--text-muted)' };
}

function SkillCard({ skill }) {
  const { label, color } = getLevel(skill.proficiency);
  const isMentorVerified =
    skill.evidence_source === 'mentor_verified' ||
    skill.evidence_source === 'diagnostic_assessment';

  return (
    <div
      style={{
        padding: '14px 16px',
        background: 'var(--bg-elevated)',
        border: '1px solid',
        borderColor: isMentorVerified ? 'hsla(174, 72%, 56%, 0.45)' : 'var(--border)',
        borderRadius: 'var(--r-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
            {skill.name}
            {isMentorVerified && (
              <span
                style={{
                  fontSize: '0.68rem',
                  fontWeight: 700,
                  padding: '2px 7px',
                  borderRadius: '999px',
                  background: 'hsla(174, 72%, 56%, 0.18)',
                  color: 'var(--teal)',
                }}
              >
                ✓ Mentor Verified
              </span>
            )}
          </div>
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

export default function Dashboard({ user, career, skills, onSkillUpdated }) {
  const [activeTab, setActiveTab] = useState('graph'); // 'graph' | 'feed' | 'mentorship'
  const [signingOut, setSigningOut] = useState(false);
  const [showLogoutToast, setShowLogoutToast] = useState(false);
  const [prefillMentorQuestion, setPrefillMentorQuestion] = useState(null);

  const handleSignOut = async () => {
    setSigningOut(true);
    setShowLogoutToast(false);
    await supabase.auth.signOut();
  };

  const handleAskMentorAboutLesson = (questionPayload) => {
    setPrefillMentorQuestion(questionPayload);
    setActiveTab('mentorship');
  };

  const displayName = user?.user_metadata?.full_name || user?.email?.split('@')[0] || 'Learner';

  // Compute an importance-weighted estimate from the learner's current skill ratings:
  const totalWeight = skills.reduce((sum, s) => {
    const w = s.importance_score ?? (s.importance === 'essential' ? 1.0 : s.importance === 'optional' ? 0.5 : 0.75);
    return sum + Math.max(0.2, w);
  }, 0);

  const weightedSum = skills.reduce((sum, s) => {
    const w = s.importance_score ?? (s.importance === 'essential' ? 1.0 : s.importance === 'optional' ? 0.5 : 0.75);
    return sum + s.proficiency * Math.max(0.2, w);
  }, 0);

  const avgProgress = skills.length && totalWeight > 0 ? Math.round(weightedSum / totalWeight) : 0;
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
            maxWidth: '960px',
            margin: '0 auto 32px',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div className="logo-mark">
            <div className="logo-mark__icon">CB</div>
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
              onClick={() => setShowLogoutToast(true)}
              disabled={signingOut}
            >
              {signingOut ? 'Signing out...' : 'Sign out'}
            </button>
          </div>
        </header>

        {/* Main content */}
        <main className="container--wide" style={{ maxWidth: '960px' }}>
          {/* Navigation Bar (Skill Graph vs Learning Feed vs Mentorship Ecosystem) */}
          <nav
            style={{
              display: 'flex',
              gap: '8px',
              marginBottom: '24px',
              borderBottom: '1px solid var(--border)',
              paddingBottom: '12px',
              flexWrap: 'wrap',
            }}
          >
            <button
              id="tab-skill-graph"
              type="button"
              className={`btn btn--sm ${activeTab === 'graph' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('graph')}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              📊 Skill Graph
            </button>
            <button
              id="tab-learning-feed"
              type="button"
              className={`btn btn--sm ${activeTab === 'feed' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('feed')}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              📚 Learning Feed &amp; Quizzes
            </button>
            <button
              id="tab-mentorship-hub"
              type="button"
              className={`btn btn--sm ${activeTab === 'mentorship' ? 'btn--primary' : 'btn--ghost'}`}
              onClick={() => setActiveTab('mentorship')}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              🎓 Mentorship, Q&amp;A &amp; Pulse
            </button>
          </nav>

          {activeTab === 'feed' ? (
            <Recommendations
              user={user}
              career={career}
              skills={skills}
              onSkillUpdated={onSkillUpdated}
              onNavigateToGraph={() => setActiveTab('graph')}
              onAskMentorAboutLesson={handleAskMentorAboutLesson}
            />
          ) : activeTab === 'mentorship' ? (
            <LearnerMentorship
              user={user}
              career={career}
              skills={skills}
              prefillQuestion={prefillMentorQuestion}
              onClearPrefillQuestion={() => setPrefillMentorQuestion(null)}
            />
          ) : (
            <>
              {/* Welcome + career banner */}
              <div className="card" style={{ marginBottom: '24px', textAlign: 'left' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '16px',
                    marginBottom: '20px',
                  }}
                >
                  <div>
                    <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '4px', fontWeight: 500 }}>
                      WELCOME BACK
                    </p>
                    <h2 style={{ marginBottom: '4px' }}>
                      Hello, <span className="gradient-text">{displayName}</span>
                    </h2>
                    <p style={{ fontSize: '0.9rem' }}>
                      Your target career:{' '}
                      <strong style={{ color: 'var(--text-primary)' }}>{career?.title ?? 'Not specified'}</strong>
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
                      Avg. estimated proficiency
                    </div>
                  </div>
                </div>

                {/* Overall progress bar */}
                <div style={{ marginBottom: '8px', display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  <span>Estimated career skill profile</span>
                  <span>{masteredCount} / {skills.length} at 100% estimate</span>
                </div>
                <div className="progress-bar" style={{ height: '8px', marginBottom: '18px' }}>
                  <div className="progress-bar__fill" style={{ width: `${avgProgress}%` }} />
                </div>

                {/* Dual-Engine CTAs */}
                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                    Close skill gaps with AI micro-learning sprints or 1-on-1 verified industry mentors.
                  </span>
                  <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      style={{ borderColor: 'var(--teal)', color: 'var(--teal)' }}
                      onClick={() => setActiveTab('mentorship')}
                    >
                      🎓 Match with a Mentor &rarr;
                    </button>
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      onClick={() => setActiveTab('feed')}
                    >
                      Start Micro-Learning Sprint &rarr;
                    </button>
                  </div>
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
                    No skills found. Please try refreshing.
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
            </>
          )}
        </main>
      </div>

      {/* Logout confirmation toast */}
      {showLogoutToast && (
        <Toast
          message="Are you sure you want to log out?"
          confirmLabel="Yes, log out"
          onConfirm={handleSignOut}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </>
  );
}
