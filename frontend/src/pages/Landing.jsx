// src/pages/Landing.jsx
import React from 'react';
import ThemeSelector from '../components/ThemeSelector';
import {
  Compass,
  GraduationCap,
  Users,
  Check,
  ArrowRight,
  Layers,
  ShieldCheck,
  BookOpen,
} from '../components/Icons';

export default function Landing({ onSelectRole, onSignIn }) {
  return (
    <div style={{ minHeight: '100svh', display: 'flex', flexDirection: 'column', background: 'var(--background)' }}>
      {/* Top Navigation */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'var(--surface)',
          position: 'sticky',
          top: 0,
          zIndex: 50,
        }}
      >
        <div
          style={{
            maxWidth: '1120px',
            margin: '0 auto',
            padding: '14px 24px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <div className="logo-mark">
            <div className="logo-mark__icon">
              <Compass size={18} />
            </div>
            <span>Career Beacon</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <ThemeSelector />
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={onSignIn}
            >
              Sign In
            </button>
            <button
              type="button"
              className="btn btn--primary btn--sm"
              onClick={() => onSelectRole('learner')}
            >
              <span>Get Started</span>
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main
        style={{
          flex: '1 0 auto',
          maxWidth: '1120px',
          width: '100%',
          margin: '0 auto',
          padding: '64px 24px 56px',
        }}
      >
        {/* Hero Section */}
        <div
          style={{
            maxWidth: '740px',
            margin: '0 auto 52px',
            textAlign: 'center',
          }}
        >
          <div
            style={{
              fontSize: '0.78rem',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              color: 'var(--accent)',
              marginBottom: '14px',
            }}
          >
            Career Readiness &amp; Practitioner Mentorship
          </div>

          <h1
            style={{
              fontSize: 'clamp(1.95rem, 3.8vw, 2.85rem)',
              lineHeight: 1.16,
              marginBottom: '18px',
            }}
          >
            Benchmark your skills, focus your learning sprints, and work with industry mentors.
          </h1>

          <p
            style={{
              fontSize: 'clamp(0.98rem, 1.5vw, 1.08rem)',
              color: 'var(--text-secondary)',
              maxWidth: '620px',
              margin: '0 auto',
              lineHeight: 1.65,
            }}
          >
            Map what you already know against recognized occupational standards, close your highest-impact skill gaps through structured micro-lessons, and book 1-on-1 sessions with experienced practitioners.
          </p>
        </div>

        {/* Dual Pathway Cards (Learner vs Mentor) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: '24px',
            maxWidth: '900px',
            margin: '0 auto 56px',
          }}
        >
          {/* Learner Card */}
          <div
            className="card card--interactive"
            style={{
              padding: '32px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '24px',
            }}
          >
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '20px',
                }}
              >
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: 'var(--r-md)',
                    background: 'var(--accent-soft)',
                    border: '1px solid var(--accent-border)',
                    color: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <GraduationCap size={20} />
                </div>
                <span className="badge badge--accent">Learner Track</span>
              </div>

              <h2 style={{ fontSize: '1.28rem', marginBottom: '10px' }}>For Learners &amp; Career Switchers</h2>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '22px' }}>
                Select a target occupation, calibrate your baseline skill graph, and progress through focused daily learning drops.
              </p>

              <ul
                style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <li style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Check size={15} color="var(--status-success)" />
                  <span>O*NET &amp; ESCO occupational skill calibration</span>
                </li>
                <li style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Check size={15} color="var(--status-success)" />
                  <span>Curated lessons with 5-question mastery checkpoints</span>
                </li>
                <li style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Check size={15} color="var(--status-success)" />
                  <span>1-on-1 mentor booking and searchable Q&amp;A library</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              className="btn btn--primary btn--full"
              onClick={() => onSelectRole('learner')}
            >
              <span>Start as a Learner</span>
              <ArrowRight size={16} />
            </button>
          </div>

          {/* Mentor Card */}
          <div
            className="card card--interactive"
            style={{
              padding: '32px',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
              gap: '24px',
            }}
          >
            <div>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  marginBottom: '20px',
                }}
              >
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: 'var(--r-md)',
                    background: 'var(--surface-elevated)',
                    border: '1px solid var(--border)',
                    color: 'var(--text-primary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <Users size={20} />
                </div>
                <span className="badge badge--neutral">Practitioner Track</span>
              </div>

              <h2 style={{ fontSize: '1.28rem', marginBottom: '10px' }}>For Industry Mentors</h2>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '22px' }}>
                Share domain expertise with learners matched to your discipline, answer technical questions, and endorse verified skills.
              </p>

              <ul
                style={{
                  listStyle: 'none',
                  padding: 0,
                  margin: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px',
                }}
              >
                <li style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Check size={15} color="var(--status-success)" />
                  <span>Matched only with learners working on your core skills</span>
                </li>
                <li style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Check size={15} color="var(--status-success)" />
                  <span>Live mentee skill-gap snapshots before every 1-on-1 session</span>
                </li>
                <li style={{ fontSize: '0.86rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <Check size={15} color="var(--status-success)" />
                  <span>Protected weekly schedule with Google Calendar &amp; .ics invites</span>
                </li>
              </ul>
            </div>

            <button
              type="button"
              className="btn btn--secondary btn--full"
              onClick={() => onSelectRole('mentor')}
            >
              <span>Join as an Industry Mentor</span>
              <ArrowRight size={16} />
            </button>
          </div>
        </div>

        {/* Platform Pillars */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            maxWidth: '900px',
            margin: '0 auto',
            paddingTop: '32px',
            borderTop: '1px solid var(--border)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <BookOpen size={18} color="var(--accent)" style={{ marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.86rem', color: 'var(--text-primary)' }}>
                Occupational Standards
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Grounded in O*NET and ESCO competency frameworks
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <Layers size={18} color="var(--accent)" style={{ marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.86rem', color: 'var(--text-primary)' }}>
                Focused Learning Sprints
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Ordered from foundational concepts to advanced practice
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <ShieldCheck size={18} color="var(--accent)" style={{ marginTop: '2px' }} />
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.86rem', color: 'var(--text-primary)' }}>
                Verified Skill Progression
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                Checkpoint assessments &amp; practitioner skill endorsements
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border)',
          background: 'var(--surface)',
          padding: '20px 24px',
          textAlign: 'center',
          color: 'var(--text-muted)',
          fontSize: '0.8rem',
        }}
      >
        Career Beacon · Career Readiness &amp; Mentorship Platform · Strathmore University School of Computing
      </footer>
    </div>
  );
}
