// src/pages/Onboarding.jsx
import { useState, useCallback } from 'react';
import { supabase } from '../lib/SupabaseClient';
import { searchCareer, saveSkills } from '../lib/api';
import Toast from '../components/Toast';

const BEHAVIORAL_LEVELS = [
  {
    label: 'Novice',
    value: 20,
    tooltip: 'Understand syntax & tutorials; require guidance building standalone features.',
  },
  {
    label: 'Intermediate',
    value: 50,
    tooltip: 'Build projects independently; solve production bugs and consult documentation.',
  },
  {
    label: 'Advanced',
    value: 80,
    tooltip: 'Design architectures, review peer code, optimize performance and security.',
  },
];

const CATEGORY_METADATA = {
  'Technical Skills':        { color: 'hsl(174, 72%, 56%)',  bg: 'hsla(174, 72%, 56%, 0.1)' },
  'Domain Knowledge':        { color: 'hsl(258, 90%, 66%)',  bg: 'hsla(258, 90%, 66%, 0.12)' },
  'Tools & Systems':         { color: 'hsl(213, 94%, 68%)',  bg: 'hsla(213, 94%, 68%, 0.1)' },
  'Interpersonal & Leadership': { color: 'hsl(38, 92%, 50%)', bg: 'hsla(38, 92%, 50%, 0.12)' },
  'Custom Stack':            { color: 'hsl(300, 70%, 60%)',  bg: 'hsla(300, 70%, 60%, 0.1)' },
  'General':                 { color: 'hsl(220, 15%, 55%)',  bg: 'hsla(220, 15%, 55%, 0.1)' },
};

const IMPORTANCE_BADGE = {
  essential: {
    label: 'Essential',
    tooltip: 'Importance score ≥ 70% (raw score ≥ 3.8/5.0 in O*NET or designated essential by ESCO)',
    color: 'hsl(142, 71%, 45%)',
    bg: 'hsla(142, 71%, 45%, 0.12)',
    border: 'hsla(142, 71%, 45%, 0.3)',
  },
  optional: {
    label: 'Optional',
    tooltip: 'Supporting competency: Importance score < 70% in O*NET or designated optional by ESCO',
    color: 'hsl(220, 15%, 60%)',
    bg: 'hsla(220, 15%, 60%, 0.1)',
    border: 'hsla(220, 15%, 60%, 0.25)',
  },
};

const SKILL_CATEGORIES = ['Technical Skills', 'Domain Knowledge', 'Tools & Systems', 'Interpersonal & Leadership', 'Custom Stack'];

// ─── Step 1: Career Search & Disambiguation Wheel ──────────────────────────────
function CareerSearch({ onCareerFound, onLogoutRequest }) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [disambiguation, setDisambiguation] = useState(null); // array of candidate roles

  const handleSearch = useCallback(
    async (e, overrideQuery) => {
      if (e) e.preventDefault();
      const targetQuery = (overrideQuery || query).trim();
      if (!targetQuery) return;

      setLoading(true);
      setError(null);
      setDisambiguation(null);

      try {
        const result = await searchCareer(targetQuery);
        if (result.status === 'disambiguation_required') {
          setDisambiguation(result.candidates);
        } else {
          onCareerFound(result);
        }
      } catch (err) {
        setError(err.message || 'Something went wrong. Please try again.');
      } finally {
        setLoading(false);
      }
    },
    [query, onCareerFound]
  );

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <h2 style={{ marginBottom: '8px' }}>
        What's your <span className="gradient-text">target career?</span>
      </h2>
      <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
        Enter your target role to generate a standardized labor-market skill graph.
      </p>

      <form onSubmit={(e) => handleSearch(e)} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="career-input">Career Goal</label>
          <input
            id="career-input"
            type="text"
            placeholder="e.g. Frontend Developer, Data Scientist, DevOps Engineer..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              if (disambiguation) setDisambiguation(null);
            }}
            autoFocus
            autoComplete="off"
            style={{ width: '100%' }}
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
              Analyzing labor taxonomies…
            </>
          ) : (
            'Find Career Pathway'
          )}
        </button>
      </form>

      {/* Disambiguation Wheel / Selector */}
      {disambiguation && (
        <div
          style={{
            marginTop: '20px',
            padding: '16px',
            background: 'var(--bg-elevated)',
            border: '1px solid var(--accent-border)',
            borderRadius: 'var(--r-md)',
          }}
        >
          <div style={{ fontWeight: 600, fontSize: '0.9rem', marginBottom: '8px', color: 'var(--accent-light)' }}>
            Multiple paths found. Choose your exact specialization:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {disambiguation.map((cand) => (
              <button
                key={cand.id}
                type="button"
                onClick={() => handleSearch(null, cand.title)}
                className="btn btn--ghost"
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  textAlign: 'left',
                  width: '100%',
                  padding: '12px 16px',
                  whiteSpace: 'normal',
                  gap: '16px',
                  borderRadius: 'var(--r-md)',
                  border: '1px solid var(--border)',
                  background: 'var(--bg-surface)',
                  transition: 'all 0.2s ease',
                  cursor: 'pointer',
                  boxSizing: 'border-box',
                }}
              >
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '4px' }}>
                    {cand.title}
                  </div>
                  {cand.description && (
                    <div
                      style={{
                        fontSize: '0.8rem',
                        lineHeight: '1.45',
                        color: 'var(--text-secondary)',
                        wordBreak: 'break-word',
                      }}
                    >
                      {cand.description}
                    </div>
                  )}
                </div>
                <span
                  className="badge badge--accent"
                  style={{ flexShrink: 0, alignSelf: 'flex-start', marginTop: '2px', whiteSpace: 'nowrap' }}
                >
                  {Math.round(cand.similarity * 100)}% Match
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {error && (
        <div className="alert alert--error" style={{ marginTop: '16px' }}>
          {error}
        </div>
      )}

      {/* Logout link at bottom */}
      <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.8rem' }}>
        <button
          id="onboarding-logout-btn"
          type="button"
          onClick={onLogoutRequest}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--text-muted)',
            cursor: 'pointer',
            fontSize: '0.8rem',
            textDecoration: 'underline',
            padding: 0,
          }}
        >
          Log out
        </button>
      </p>
    </div>
  );
}

// ─── Step 2: Skill Assessment by Domain Category ────────────────────────────────
function SkillAssessment({ career, skills: initialSkills, source, userId, onComplete }) {
  const [skills, setSkills] = useState(initialSkills);
  const [proficiency, setProficiency] = useState(() =>
    Object.fromEntries(initialSkills.map((s) => [s.id, 20]))
  );
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('Technical Skills');
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const setLevel = (skillId, value) => {
    setProficiency((prev) => ({ ...prev, [skillId]: value }));
  };

  const handleDeleteSkill = (skillId) => {
    setSkills((prev) => prev.filter((s) => s.id !== skillId));
    setProficiency((prev) => {
      const copy = { ...prev };
      delete copy[skillId];
      return copy;
    });
  };

  const handleAddSkill = (e) => {
    e.preventDefault();
    const cleanName = newSkillName.trim();
    if (!cleanName) return;

    const tempId = `custom-${Date.now()}`;
    const newSkill = {
      id:           tempId,
      name:         cleanName,
      category:     newSkillCategory,
      importance:   null,        // User-added skills carry no source importance label
      source_origin: 'manual',
      provenance_label: 'Your addition',
    };

    setSkills((prev) => [...prev, newSkill]);
    setProficiency((prev) => ({ ...prev, [tempId]: 20 }));
    setNewSkillName('');
    setShowAddForm(false);
  };

  const handleSave = async () => {
    if (skills.length === 0) {
      setError('Your skill graph must have at least one skill.');
      return;
    }

    setLoading(true);
    setError(null);
    try {
      await saveSkills(userId, career, skills, proficiency);
      onComplete({
        career,
        skills: skills.map((s) => ({
          ...s,
          proficiency: proficiency[s.id] ?? 20,
        })),
      });
    } catch (err) {
      setError(err.message || 'Failed to save skill profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Group skills by domain category; preserve insertion order within each group
  const groupedSkills = skills.reduce((acc, s) => {
    const cat = s.category || 'General';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(s);
    return acc;
  }, {});

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot done" />
        <div className="step-dot active" />
      </div>

      {/* Career Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0, fontSize: '1.4rem' }}>{career.title}</h2>
          {/* Show actual provenance source, not a generic label */}
          {career.provenance_label ? (
            <span
              className={`badge ${
                career.provenance_label.includes('AI') ? 'badge--accent' : 'badge--success'
              }`}
            >
              {career.provenance_label}
            </span>
          ) : source === 'matched' ? (
            <span className="badge badge--success">Source: Catalog · Review pending</span>
          ) : (
            <span className="badge badge--accent">AI Proposal (Editable)</span>
          )}
        </div>
        {career.description && (
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{career.description}</p>
        )}
      </div>

      {/* Behavioral Rubric & Provenance Guide */}
      <div
        style={{
          marginBottom: '20px',
          padding: '12px 14px',
          background: 'var(--bg-elevated)',
          borderRadius: 'var(--r-md)',
          border: '1px solid var(--border)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
        }}
      >
        <strong style={{ color: 'var(--text-primary)' }}>Occupational Standards & Provenance Guide:</strong>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginTop: '6px' }}>
          <div>
            • <strong>Proficiency Rubric:</strong> <em>Novice (20%)</em> understands syntax with guidance; <em>Intermediate (50%)</em> ships features independently; <em>Advanced (80%)</em> leads architecture and peer reviews.
          </div>
          <div>
            • <strong>Importance Classification:</strong> Skills are classified as <em>Essential</em> when O*NET importance score ≥ 70% (raw score ≥ 3.8/5.0) or designated essential by ESCO; otherwise <em>Optional</em>.
          </div>
          <div>
            • <strong>Source Provenance:</strong> Sourced from official labor taxonomies (O*NET 31.0 / ESCO). Records show <em>Review pending</em> until internally verified.
          </div>
        </div>
      </div>

      {/* Skill Groups by Domain Category */}
      {Object.entries(groupedSkills).map(([category, catSkills]) => {
        if (!catSkills || catSkills.length === 0) return null;
        const meta = CATEGORY_METADATA[category] || CATEGORY_METADATA['General'];

        return (
          <div key={category} style={{ marginBottom: '24px' }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                marginBottom: '10px',
                paddingBottom: '6px',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <span
                style={{
                  fontSize: '0.72rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                  padding: '2px 8px',
                  borderRadius: 'var(--r-sm)',
                  backgroundColor: meta.bg,
                  color: meta.color,
                }}
              >
                {category}
              </span>
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                {catSkills.length} skill{catSkills.length !== 1 ? 's' : ''}
              </span>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {catSkills.map((skill) => (
                <div
                  key={skill.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '14px',
                    padding: '12px 16px',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: '1 1 280px' }}>
                    <button
                      type="button"
                      onClick={() => handleDeleteSkill(skill.id)}
                      title="Remove skill from your roadmap"
                      style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--text-muted)',
                        cursor: 'pointer',
                        padding: '4px 6px',
                        fontSize: '0.85rem',
                        borderRadius: '4px',
                        flexShrink: 0,
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.color = 'hsl(0, 70%, 60%)')}
                      onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                    >
                      ✕
                    </button>
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <div style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                        {skill.name}
                      </div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px', flexWrap: 'wrap' }}>
                        {/* Importance badge — only shown when source-backed */}
                        {skill.importance && IMPORTANCE_BADGE[skill.importance] && (() => {
                          const imp = IMPORTANCE_BADGE[skill.importance];
                          return (
                            <span
                              title={imp.tooltip}
                              style={{
                                fontSize: '0.68rem', fontWeight: 700, padding: '1px 6px',
                                borderRadius: '10px', letterSpacing: '0.02em',
                                background: imp.bg, color: imp.color,
                                border: `1px solid ${imp.border}`,
                                cursor: 'help',
                                whiteSpace: 'nowrap',
                              }}
                            >
                              {imp.label}
                            </span>
                          );
                        })()}
                        {/* Provenance badge */}
                        {skill.provenance_label && (
                          <span
                            style={{
                              fontSize: '0.68rem',
                              fontWeight: 600,
                              padding: '1px 6px',
                              borderRadius: '10px',
                              letterSpacing: '0.02em',
                              whiteSpace: 'nowrap',
                              background: skill.provenance_label.includes('AI') || skill.provenance_label === 'Your addition'
                                ? 'hsla(38, 92%, 50%, 0.15)'
                                : 'hsla(174, 72%, 56%, 0.12)',
                              color: skill.provenance_label.includes('AI') || skill.provenance_label === 'Your addition'
                                ? 'hsl(38, 82%, 55%)'
                                : 'hsl(174, 65%, 45%)',
                              border: `1px solid ${
                                skill.provenance_label.includes('AI') || skill.provenance_label === 'Your addition'
                                  ? 'hsla(38, 92%, 50%, 0.3)'
                                  : 'hsla(174, 72%, 56%, 0.25)'
                              }`,
                            }}
                          >
                            {skill.provenance_label}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Behavioral Toggle Group */}
                  <div className="skill-toggle" style={{ flexShrink: 0, marginLeft: 'auto' }}>
                    {BEHAVIORAL_LEVELS.map(({ label, value, tooltip }) => (
                      <button
                        key={value}
                        type="button"
                        title={tooltip}
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
          </div>
        );
      })}

      {/* Add Custom Skill Section */}
      <div style={{ marginBottom: '24px' }}>
        {showAddForm ? (
          <form
            onSubmit={handleAddSkill}
            style={{
              padding: '14px',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--r-md)',
              border: '1px dashed var(--accent-border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
            }}
          >
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Add a Skill or Tool:</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="e.g. Supabase, TailwindCSS, Django..."
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                autoFocus
                style={{ flex: 1, minWidth: '160px' }}
              />
              <select
                value={newSkillCategory}
                onChange={(e) => setNewSkillCategory(e.target.value)}
                style={{
                  background: 'var(--bg-input)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  padding: '8px 12px',
                  fontSize: '0.85rem',
                }}
              >
                {SKILL_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setShowAddForm(false)}
              >
                Cancel
              </button>
              <button type="submit" className="btn btn--primary btn--sm" disabled={!newSkillName.trim()}>
                Add to Profile
              </button>
            </div>
          </form>
        ) : (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => setShowAddForm(true)}
            style={{ width: '100%', borderStyle: 'dashed' }}
          >
            + Add a specific stack or tool (e.g. Supabase, Docker, Vue)
          </button>
        )}
      </div>

      {error && (
        <div className="alert alert--error" style={{ marginBottom: '16px' }}>
          {error}
        </div>
      )}

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
            Calibrating skill profile…
          </>
        ) : (
          'Save & Generate Learning Pathway'
        )}
      </button>
    </div>
  );
}

// ─── Onboarding Orchestrator ──────────────────────────────────────────────────
export default function Onboarding({ user, onComplete }) {
  const [step, setStep] = useState(1); // 1 = search, 2 = assessment
  const [career, setCareer] = useState(null);
  const [skills, setSkills] = useState([]);
  const [source, setSource] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);

  const handleCareerFound = ({ career: c, skills: s, status }) => {
    setCareer(c);
    setSkills(s);
    setSource(status);
    setStep(2);
  };

  const handleBack = () => {
    setStep(1);
    setCareer(null);
    setSkills([]);
  };

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  return (
    <>
      <div className="bg-orb bg-orb--1" />
      <div className="bg-orb bg-orb--2" />

      <div className="page-center" style={{ minHeight: '100svh', padding: '40px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div className="container" style={{ maxWidth: step === 2 ? '840px' : '620px', width: '100%', transition: 'max-width 0.25s ease' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
            <div className="logo-mark">
              <div className="logo-mark__icon">CB</div>
              Career Beacon
            </div>
          </div>

          <div className="card" style={{ padding: step === 2 ? '36px 32px' : '32px 28px' }}>
            {step === 1 && (
              <CareerSearch
                onCareerFound={handleCareerFound}
                onLogoutRequest={() => setShowLogoutToast(true)}
              />
            )}
            {step === 2 && career && (
              <>
                <button
                  type="button"
                  id="onboarding-back-btn"
                  onClick={() => setShowLogoutToast(true)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-muted)',
                    fontSize: '0.85rem',
                    cursor: 'pointer',
                    padding: '0 0 16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px',
                  }}
                >
                  ← Change career target
                </button>

                <SkillAssessment
                  career={career}
                  skills={skills}
                  source={source}
                  userId={user.id}
                  onComplete={onComplete}
                />
              </>
            )}
          </div>

          <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Your assessment is calibrated against labor-market benchmarks and privacy-protected.
          </p>
        </div>
      </div>

      {showLogoutToast && (
        <Toast
          message={
            step === 2
              ? 'Going back will discard your current skill customizations. Are you sure?'
              : 'Are you sure you want to log out?'
          }
          confirmLabel={step === 2 ? 'Yes, go back' : 'Yes, log out'}
          onConfirm={() => {
            setShowLogoutToast(false);
            if (step === 2) handleBack();
            else handleLogout();
          }}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </>
  );
}
