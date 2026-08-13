// src/pages/Onboarding.jsx
import { useState, useCallback } from 'react';
import { searchCareer, saveSkills } from '../lib/api';

const PROFICIENCY_LEVELS = [
  { label: 'Novice',       value: 20 },
  { label: 'Intermediate', value: 50 },
  { label: 'Advanced',     value: 80 },
];

// ─── Step 1: Career Search ────────────────────────────────────────────────────
function CareerSearch({ onCareerFound }) {
  const [query, setQuery]   = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState(null);

  const handleSearch = useCallback(async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await searchCareer(query.trim());
      onCareerFound(result);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [query, onCareerFound]);

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <h2 style={{ marginBottom: '8px' }}>
        What's your <span className="gradient-text">target career?</span>
      </h2>
      <p style={{ marginBottom: '28px', fontSize: '0.95rem' }}>
        Type anything — we'll match it to a recognised career path using AI.
      </p>

      <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="career-input">Career goal</label>
          <input
            id="career-input"
            type="text"
            placeholder="e.g. AI Web App Developer, UX Designer…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
            autoComplete="off"
          />
        </div>

        <button
          id="career-search-btn"
          type="submit"
          className="btn btn--primary btn--full"
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <>
              <span className="spinner" />
              Analysing…
            </>
          ) : 'Find My Path →'}
        </button>
      </form>

      {error && <div className="alert alert--error">{error}</div>}
    </div>
  );
}

// ─── Step 2: Skill Sliders ────────────────────────────────────────────────────
function SkillAssessment({ career, skills, userId, onComplete }) {
  // Default everyone to Novice (20)
  const [proficiency, setProficiency] = useState(
    () => Object.fromEntries(skills.map((s) => [s.id, 20]))
  );
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const setLevel = (skillId, value) => {
    setProficiency((prev) => ({ ...prev, [skillId]: value }));
  };

  const handleSave = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = Object.entries(proficiency).map(([skill_id, prof]) => ({
        skill_id,
        proficiency: prof,
      }));
      await saveSkills(userId, career.id, payload);
      onComplete({ career, skills: skills.map((s) => ({ ...s, proficiency: proficiency[s.id] })) });
    } catch (err) {
      setError(err.message || 'Failed to save. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot done" />
        <div className="step-dot active" />
      </div>

      {/* Career Header */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0 }}>{career.title}</h2>
          <span className="badge badge--accent">Matched ✓</span>
        </div>
        {career.description && (
          <p style={{ fontSize: '0.9rem' }}>{career.description}</p>
        )}
      </div>

      {/* Proficiency Instructions */}
      <p style={{ marginBottom: '20px', fontSize: '0.875rem', color: 'var(--text-secondary)' }}>
        Rate your current level for each required skill:
      </p>

      {/* Skill List */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '28px' }}>
        {skills.map((skill) => (
          <div
            key={skill.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              padding: '12px 14px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-md)',
              flexWrap: 'wrap',
            }}
          >
            <div>
              <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)' }}>
                {skill.name}
              </div>
              {skill.category && (
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                  {skill.category}
                </div>
              )}
            </div>

            <div className="skill-toggle">
              {PROFICIENCY_LEVELS.map(({ label, value }) => (
                <button
                  key={value}
                  type="button"
                  className={`skill-toggle__btn ${proficiency[skill.id] === value ? 'active' : ''}`}
                  onClick={() => setLevel(skill.id, value)}
                  id={`skill-${skill.id}-${label.toLowerCase()}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>

      {error && <div className="alert alert--error" style={{ marginBottom: '16px' }}>{error}</div>}

      <button
        id="save-skills-btn"
        type="button"
        className="btn btn--primary btn--full"
        onClick={handleSave}
        disabled={loading}
      >
        {loading ? (
          <>
            <span className="spinner" />
            Saving your graph…
          </>
        ) : 'Build My Skill Graph →'}
      </button>
    </div>
  );
}

// ─── Onboarding Orchestrator ─────────────────────────────────────────────────
export default function Onboarding({ user, onComplete }) {
  const [step, setStep]     = useState(1);  // 1 = search, 2 = sliders
  const [career, setCareer] = useState(null);
  const [skills, setSkills] = useState([]);

  const handleCareerFound = ({ career: c, skills: s }) => {
    setCareer(c);
    setSkills(s);
    setStep(2);
  };

  const handleBack = () => {
    setStep(1);
    setCareer(null);
    setSkills([]);
  };

  return (
    <>
      {/* Background decoration */}
      <div className="bg-orb bg-orb--1" />
      <div className="bg-orb bg-orb--2" />

      <div className="page-center">
        <div className="container">
          {/* Logo */}
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '40px' }}>
            <div className="logo-mark">
              <div className="logo-mark__icon">🧭</div>
              Career Beacon
            </div>
          </div>

          <div className="card">
            {step === 1 && (
              <CareerSearch onCareerFound={handleCareerFound} />
            )}
            {step === 2 && career && (
              <>
                {/* Back navigation */}
                <button
                  type="button"
                  onClick={handleBack}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    padding: '0 0 20px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                    transition: 'color var(--duration) var(--ease)',
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-primary)'}
                  onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
                >
                  ← Change career
                </button>

                {/* Empty skills guard */}
                {skills.length === 0 ? (
                  <div style={{ textAlign: 'center', padding: '24px 0' }}>
                    <div style={{ fontSize: '2rem', marginBottom: '12px' }}>⚠️</div>
                    <p style={{ marginBottom: '20px' }}>
                      No skills were returned for <strong style={{ color: 'var(--text-primary)' }}>{career.title}</strong>.
                      This can happen if the AI response was incomplete. Please try a different search term.
                    </p>
                    <button
                      type="button"
                      className="btn btn--ghost"
                      onClick={handleBack}
                    >
                      ← Try again
                    </button>
                  </div>
                ) : (
                  <SkillAssessment
                    career={career}
                    skills={skills}
                    userId={user.id}
                    onComplete={onComplete}
                  />
                )}
              </>
            )}
          </div>

          {/* Footer note */}
          <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            Your data is private and used only to personalise your learning path.
          </p>
        </div>
      </div>
    </>
  );
}
