// src/pages/LearnerOnboarding.jsx
// Handles the full learner onboarding flow (career search → skill assessment).
// Mentor onboarding lives in MentorOnboarding.jsx
import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/SupabaseClient';
import { searchCareer, getCareerById, saveSkills } from '../lib/api';
import Toast from '../components/Toast';

// ─── Constants ──────────────────────────────────────────────────────────────

// 4-level rating: "Not Yet" is the honest default for a brand-new user.
// Proficiency=0 tells the recommendation engine: teach this from scratch.
const BEHAVIORAL_LEVELS = [
  {
    label: 'Not Yet',
    value: 0,
    tooltip: 'No exposure yet — the system will prioritise beginner content for this skill.',
    color: 'var(--text-muted)',
  },
  {
    label: 'Novice',
    value: 20,
    tooltip: 'Understand syntax & tutorials; require guidance building standalone features.',
    color: 'hsl(213, 94%, 68%)',
  },
  {
    label: 'Intermediate',
    value: 50,
    tooltip: 'Build projects independently; solve production bugs and consult documentation.',
    color: 'hsl(174, 72%, 56%)',
  },
  {
    label: 'Advanced',
    value: 80,
    tooltip: 'Design architectures, review peer code, optimise performance and security.',
    color: 'hsl(142, 71%, 45%)',
  },
];

const CATEGORY_METADATA = {
  'Technical Skills':           { color: 'hsl(174, 72%, 56%)',  bg: 'hsla(174, 72%, 56%, 0.1)' },
  'Domain Knowledge':           { color: 'hsl(258, 90%, 66%)',  bg: 'hsla(258, 90%, 66%, 0.12)' },
  'Tools & Systems':            { color: 'hsl(213, 94%, 68%)',  bg: 'hsla(213, 94%, 68%, 0.1)' },
  'Interpersonal & Leadership': { color: 'hsl(38, 92%, 50%)',   bg: 'hsla(38, 92%, 50%, 0.12)' },
  'Custom Stack':               { color: 'hsl(300, 70%, 60%)',  bg: 'hsla(300, 70%, 60%, 0.1)' },
  'General':                    { color: 'hsl(220, 15%, 55%)',  bg: 'hsla(220, 15%, 55%, 0.1)' },
  'General Competencies':       { color: 'hsl(220, 15%, 55%)',  bg: 'hsla(220, 15%, 55%, 0.1)' },
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

const SKILL_CATEGORIES = [
  'Technical Skills',
  'Domain Knowledge',
  'Tools & Systems',
  'Interpersonal & Leadership',
  'Custom Stack',
];

// Similarity score → human-readable confidence label
function similarityLabel(score) {
  const safeScore = typeof score === 'number' && !isNaN(score) ? score : 0.85;
  if (safeScore >= 0.90) return { text: 'Excellent match', color: 'hsl(142, 71%, 45%)' };
  if (safeScore >= 0.80) return { text: 'Strong match',    color: 'hsl(174, 72%, 56%)' };
  if (safeScore >= 0.70) return { text: 'Good match',      color: 'hsl(213, 94%, 68%)' };
  return                         { text: 'Possible match', color: 'hsl(38, 92%, 50%)' };
}


// ─── Step 1a: Free-text Career Input ────────────────────────────────────────

function CareerInput({ user, onResult, onLogoutRequest }) {
  const [query, setQuery]   = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError]   = useState(null);

  const displayName = user?.user_metadata?.full_name
    || user?.user_metadata?.first_name
    || (user?.email ? user.email.split('@')[0] : '');

  const handleSearch = useCallback(async (e) => {
    if (e) e.preventDefault();
    const q = query.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const result = await searchCareer(q);
      onResult(result);
    } catch (err) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [query, onResult]);

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      {displayName && (
        <p style={{ color: 'var(--teal)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '8px' }}>
          Welcome, {displayName}! 👋
        </p>
      )}
      <h2 style={{ marginBottom: '8px' }}>
        What's your <span className="gradient-text">target career?</span>
      </h2>
      <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
        Enter your target role — we'll match it against our labor-market taxonomy (O*NET / ESCO).
      </p>

      <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="career-input">Career Goal</label>
          <input
            id="career-input"
            type="text"
            placeholder="e.g. Frontend Developer, Data Scientist, DevOps Engineer…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
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
            <><span className="spinner" /> Searching labor taxonomy…</>
          ) : (
            'Find Career Pathway'
          )}
        </button>
      </form>

      {error && (
        <div className="alert alert--error" style={{ marginTop: '16px' }}>{error}</div>
      )}

      <p style={{ textAlign: 'center', marginTop: '24px', fontSize: '0.8rem' }}>
        <button
          id="onboarding-logout-btn"
          type="button"
          onClick={onLogoutRequest}
          style={{
            background: 'none', border: 'none', color: 'var(--text-muted)',
            cursor: 'pointer', fontSize: '0.8rem', textDecoration: 'underline', padding: 0,
          }}
        >
          Log out
        </button>
      </p>
    </div>
  );
}


// ─── Step 1b: Career Card Grid ───────────────────────────────────────────────

function CareerCardGrid({ candidates, onSelect, onNoneMatch, onBack }) {
  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <h2 style={{ marginBottom: '6px' }}>
        Select your <span className="gradient-text">exact career path</span>
      </h2>
      <p style={{ marginBottom: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        We found {candidates.length} match{candidates.length !== 1 ? 'es' : ''} in our labor-market catalog. Pick the one that fits you best.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '20px' }}>
        {candidates.map((cand) => {
          const conf = similarityLabel(cand.similarity);
          return (
            <button
              key={cand.id}
              type="button"
              id={`career-card-${cand.id}`}
              onClick={() => onSelect(cand)}
              style={{
                display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between',
                textAlign: 'left', width: '100%', padding: '14px 16px',
                whiteSpace: 'normal', gap: '16px', borderRadius: 'var(--r-md)',
                border: '1px solid var(--border)', background: 'var(--bg-surface)',
                transition: 'border-color 0.15s ease, background 0.15s ease',
                cursor: 'pointer', boxSizing: 'border-box',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-border)';
                e.currentTarget.style.background = 'var(--bg-elevated)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'var(--border)';
                e.currentTarget.style.background = 'var(--bg-surface)';
              }}
            >
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {cand.title}
                </div>
                {cand.description && (
                  <div style={{ fontSize: '0.8rem', lineHeight: '1.45', color: 'var(--text-secondary)', wordBreak: 'break-word' }}>
                    {cand.description.length > 160 ? cand.description.slice(0, 160) + '…' : cand.description}
                  </div>
                )}
              </div>
              <div style={{ flexShrink: 0, alignSelf: 'flex-start', marginTop: '2px', textAlign: 'right' }}>
                {cand.is_ai_proposal && (
                  <span style={{
                    display: 'inline-block', fontSize: '0.68rem', fontWeight: 700,
                    padding: '2px 6px', borderRadius: '4px', marginBottom: '4px',
                    color: 'var(--teal)', background: 'rgba(0, 201, 167, 0.12)', border: '1px solid rgba(0, 201, 167, 0.3)',
                  }}>
                    AI Career Target
                  </span>
                )}
                <span style={{
                  display: 'block', fontSize: '0.72rem', fontWeight: 700,
                  padding: '2px 8px', borderRadius: '10px', whiteSpace: 'nowrap',
                  color: conf.color, background: (conf.color || 'hsl(174, 72%, 56%)').replace(')', ', 0.12)').replace('hsl', 'hsla'),
                }}>
                  {cand.is_ai_proposal ? 'Tailored to your goal' : conf.text}
                </span>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '3px', display: 'block' }}>
                  {cand.is_ai_proposal
                    ? 'AI Synthesized'
                    : `${Math.round((typeof cand.similarity === 'number' && !isNaN(cand.similarity) ? cand.similarity : 0.85) * 100)}% similarity`}
                </span>
              </div>
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <button
          id="none-match-btn"
          type="button"
          className="btn btn--ghost btn--full"
          style={{ borderStyle: 'dashed' }}
          onClick={() => onNoneMatch('ai_form')}
        >
          None of these match — describe with AI
        </button>
        <button
          id="close-loop-btn"
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={() => onNoneMatch('not_found')}
          style={{ color: 'var(--text-muted)', alignSelf: 'center', fontSize: '0.78rem' }}
        >
          Still no match? Request curriculum evaluation →
        </button>
        <button
          type="button"
          className="btn btn--ghost btn--sm"
          onClick={onBack}
          style={{ color: 'var(--text-muted)', alignSelf: 'center' }}
        >
          ← Change my search
        </button>
      </div>
    </div>
  );
}


// ─── Step 1c–1d: AI Fallback Structured Form ─────────────────────────────────

function AIFallbackForm({ onResult, onBack }) {
  const [industry, setIndustry]   = useState('');
  const [roleType, setRoleType]   = useState('');
  const [focus, setFocus]         = useState('');
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  const handleSubmit = useCallback(async (e) => {
    e.preventDefault();
    if (!industry.trim() || !roleType.trim() || !focus.trim()) return;

    setLoading(true);
    setError(null);

    // Build a rich natural-language query from the structured fields
    const richQuery = `${roleType.trim()} in ${industry.trim()} — ${focus.trim()}`;

    try {
      const result = await searchCareer(richQuery, true);
      onResult(result);
    } catch (err) {
      setError(err.message || 'AI search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [industry, roleType, focus, onResult]);

  const isValid = industry.trim() && roleType.trim() && focus.trim();

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <h2 style={{ marginBottom: '6px' }}>
        Describe your career <span className="gradient-text">in your own words</span>
      </h2>
      <p style={{ marginBottom: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        Our AI will standardize your description against labor-market taxonomies and find the best options.
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="ai-industry">Industry / Domain</label>
          <input
            id="ai-industry"
            type="text"
            placeholder="e.g. Software Engineering, Healthcare, Finance, Robotics…"
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            autoFocus
            style={{ width: '100%' }}
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="ai-role">Typical Role / Title</label>
          <input
            id="ai-role"
            type="text"
            placeholder="e.g. Developer, Analyst, Engineer, Designer, Manager…"
            value={roleType}
            onChange={(e) => setRoleType(e.target.value)}
            style={{ width: '100%' }}
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="ai-focus">What do you build, do, or specialise in?</label>
          <textarea
            id="ai-focus"
            placeholder="e.g. I build machine learning pipelines and deploy models to production using Python and cloud services…"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            rows={3}
            maxLength={200}
            style={{
              width: '100%', background: 'var(--bg-input)', color: 'var(--text-primary)',
              border: '1px solid var(--border)', borderRadius: 'var(--r-md)',
              padding: '10px 12px', fontSize: '0.9rem', resize: 'vertical',
              fontFamily: 'inherit', boxSizing: 'border-box',
            }}
          />
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right', marginTop: '3px' }}>
            {focus.length}/200
          </div>
        </div>

        <button
          id="ai-search-btn"
          type="submit"
          className="btn btn--primary btn--full"
          disabled={loading || !isValid}
        >
          {loading ? (
            <><span className="spinner" /> AI is analysing…</>
          ) : (
            'Search with AI'
          )}
        </button>
      </form>

      {error && (
        <div className="alert alert--error" style={{ marginTop: '16px' }}>{error}</div>
      )}

      <button
        type="button"
        className="btn btn--ghost btn--sm"
        onClick={onBack}
        style={{ marginTop: '14px', color: 'var(--text-muted)', width: '100%' }}
      >
        ← Back to career list
      </button>
    </div>
  );
}


// ─── Step 1e: Hard Failure ───────────────────────────────────────────────────

function CareerNotFound({ onRestart }) {
  return (
    <div style={{ textAlign: 'center', padding: '16px 0' }}>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>🔍</div>
      <h2 style={{ marginBottom: '8px' }}>Career not found</h2>
      <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: '1.6' }}>
        We searched our entire catalog and AI knowledge base but couldn't find a reliable match for this career.
        This might be a very niche or emerging role not yet in our taxonomy.
      </p>
      <button
        id="career-restart-btn"
        type="button"
        className="btn btn--primary"
        onClick={onRestart}
      >
        Start Over with a Different Career
      </button>
      <div style={{ marginTop: '20px', padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--r-md)', border: '1px solid var(--border)', fontSize: '0.82rem', color: 'var(--text-muted)' }}>
        <span>Don't see your specific discipline? You can request a curriculum evaluation by contacting the team at </span>
        <a href="mailto:careerbeacon@gmail.com?subject=Career%20Taxonomy%20Request" style={{ color: 'var(--teal)', fontWeight: 600 }}>careerbeacon@gmail.com</a>.
      </div>
      <p style={{ marginTop: '12px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
        Try a broader title — e.g. "Software Engineer" instead of "Quantum ML Researcher"
      </p>
    </div>
  );
}


// ─── Step 2: Skill Assessment ────────────────────────────────────────────────

function SkillAssessment({ career, skills: initialSkills, source, userId, onComplete }) {
  const [skills, setSkills]       = useState(initialSkills);
  // Default all skills to 0 ("Not Yet") — users must actively declare their level.
  // This prevents over-stating baseline proficiency in the recommendation engine.
  const [proficiency, setProficiency] = useState(() =>
    Object.fromEntries(initialSkills.map((s) => [s.id, 0]))
  );
  // Optional & General skills are OPT-IN by default so users only add the ones they want
  const [selectedOptionalIds, setSelectedOptionalIds] = useState(() => new Set());
  const [newSkillName, setNewSkillName]         = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('Technical Skills');
  const [showAddForm, setShowAddForm]           = useState(false);
  const [loading, setLoading]                   = useState(false);
  const [error, setError]                       = useState(null);

  const setLevel = (skillId, value) => {
    setProficiency((prev) => ({ ...prev, [skillId]: value }));
  };

  const toggleOptionalSkill = (skillId) => {
    setSelectedOptionalIds((prev) => {
      const next = new Set(prev);
      if (next.has(skillId)) {
        next.delete(skillId);
      } else {
        next.add(skillId);
      }
      return next;
    });
  };

  const [deletedSkillHistory, setDeletedSkillHistory] = useState(null);

  const handleDeleteSkill = (skillId) => {
    const target = skills.find((s) => s.id === skillId);
    if (!target) return;
    const prevProf = proficiency[skillId] ?? 0;
    setDeletedSkillHistory({ skill: target, proficiency: prevProf });

    setSkills((prev) => prev.filter((s) => s.id !== skillId));
    setProficiency((prev) => {
      const copy = { ...prev };
      delete copy[skillId];
      return copy;
    });
  };

  const handleUndoDelete = () => {
    if (!deletedSkillHistory) return;
    const { skill, proficiency: restoredProf } = deletedSkillHistory;
    setSkills((prev) => [skill, ...prev]);
    setProficiency((prev) => ({ ...prev, [skill.id]: restoredProf }));
    setDeletedSkillHistory(null);
  };

  const handleResetSkills = () => {
    setSkills(initialSkills);
    setSelectedOptionalIds(new Set());
    setProficiency((prev) => {
      const reset = {};
      initialSkills.forEach((s) => {
        reset[s.id] = prev[s.id] ?? 0;
      });
      return reset;
    });
    setDeletedSkillHistory(null);
  };

  const handleAddSkill = (e) => {
    e.preventDefault();
    const cleanName = newSkillName.trim();
    if (!cleanName) return;

    const tempId = `custom-${Date.now()}`;
    const newSkill = {
      id:              tempId,
      name:            cleanName,
      category:        newSkillCategory,
      importance:      null,        // User-added skills carry no source importance label
      source_origin:   'manual',
      provenance_label: 'Your addition',
    };

    setSkills((prev) => [...prev, newSkill]);
    setProficiency((prev) => ({ ...prev, [tempId]: 0 })); // Default "Not Yet"
    setNewSkillName('');
    setShowAddForm(false);
  };

  const [showOptional, setShowOptional] = useState(false);
  const [showGeneralCompetencies, setShowGeneralCompetencies] = useState(false);

  const essentialSkills = skills.filter(
    (s) => s.importance === 'essential' || s.source_origin === 'manual' || !s.importance
  );
  const optionalSkills = skills.filter((s) => s.importance === 'optional');

  const activeSkillsToSave = [
    ...essentialSkills,
    ...optionalSkills.filter((s) => selectedOptionalIds.has(s.id)),
  ];

  const handleSave = async () => {
    if (activeSkillsToSave.length === 0) {
      setError('Your skill graph must have at least one skill selected.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await saveSkills(userId, career, activeSkillsToSave, proficiency);
      onComplete({
        career,
        skills: activeSkillsToSave.map((s) => ({ ...s, proficiency: proficiency[s.id] ?? 0 })),
      });
    } catch (err) {
      setError(err.message || 'Failed to save skill profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Separate actionable domain/technical optional skills from foundational/cognitive general noise
  const domainOptionalSkills = optionalSkills.filter((s) => s.category !== 'General Competencies');
  const generalNoiseSkills = optionalSkills.filter((s) => s.category === 'General Competencies');

  const groupByCategory = (list) =>
    list.reduce((acc, s) => {
      const cat = s.category || 'General';
      if (!acc[cat]) acc[cat] = [];
      acc[cat].push(s);
      return acc;
    }, {});

  const groupedEssential = groupByCategory(essentialSkills);
  const groupedDomainOptional = groupByCategory(domainOptionalSkills);
  const groupedGeneralNoise = groupByCategory(generalNoiseSkills);

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
          {career.provenance_label ? (
            <span className={`badge ${career.provenance_label.includes('AI') ? 'badge--accent' : 'badge--success'}`}>
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
      <div style={{
        marginBottom: '20px', padding: '12px 14px',
        background: 'var(--bg-elevated)', borderRadius: 'var(--r-md)',
        border: '1px solid var(--border)', fontSize: '0.82rem', color: 'var(--text-secondary)',
      }}>
        <strong style={{ color: 'var(--text-primary)' }}>Proficiency Scale Guide:</strong>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 20px', marginTop: '8px' }}>
          {BEHAVIORAL_LEVELS.map(({ label, value, tooltip, color }) => (
            <span key={value} title={tooltip} style={{ cursor: 'help', whiteSpace: 'nowrap' }}>
              <span style={{ color, fontWeight: 700 }}>{label}</span>
              <span style={{ color: 'var(--text-muted)' }}>{value > 0 ? ` (${value}%)` : ' — no exposure'}</span>
            </span>
          ))}
        </div>
        <div style={{ marginTop: '6px' }}>
          • <strong>Importance:</strong> <em>Essential</em> = O*NET score ≥ 3.8/5.0 or ESCO-designated essential.
        </div>
      </div>

      {/* Helper to render category groups */}
      {(() => {
        const renderCategoryList = (groupedMap, isOptInMode = false) =>
          Object.entries(groupedMap).map(([category, catSkills]) => {
            if (!catSkills || catSkills.length === 0) return null;
            const meta = CATEGORY_METADATA[category] || CATEGORY_METADATA['General'];

            return (
              <div key={category} style={{ marginBottom: '20px' }}>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  marginBottom: '10px', paddingBottom: '6px', borderBottom: '1px solid var(--border)',
                }}>
                  <span style={{
                    fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase',
                    letterSpacing: '0.06em', padding: '2px 8px', borderRadius: 'var(--r-sm)',
                    backgroundColor: meta.bg, color: meta.color,
                  }}>
                    {category}
                  </span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {catSkills.length} skill{catSkills.length !== 1 ? 's' : ''}
                  </span>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {catSkills.map((skill) => {
                    const isIncluded = !isOptInMode || selectedOptionalIds.has(skill.id);
                    return (
                      <div
                        key={skill.id}
                        style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          gap: '14px', padding: '12px 16px',
                          background: isIncluded ? 'var(--bg-surface)' : 'rgba(255, 255, 255, 0.015)',
                          border: isIncluded ? '1px solid var(--border)' : '1px dashed var(--border)',
                          borderRadius: 'var(--r-md)', flexWrap: 'wrap',
                          opacity: isIncluded ? 1 : 0.72,
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: '1 1 200px' }}>
                          {isOptInMode ? (
                            <input
                              type="checkbox"
                              checked={isIncluded}
                              onChange={() => toggleOptionalSkill(skill.id)}
                              title={isIncluded ? 'Included in your roadmap (click to remove)' : 'Click to include in your roadmap'}
                              style={{ width: '16px', height: '16px', cursor: 'pointer', accentColor: 'var(--teal)', flexShrink: 0 }}
                            />
                          ) : (
                            <button
                              type="button"
                              onClick={() => handleDeleteSkill(skill.id)}
                              title="Remove skill from your roadmap"
                              style={{
                                background: 'none', border: 'none', color: 'var(--text-muted)',
                                cursor: 'pointer', padding: '4px 6px', fontSize: '0.85rem',
                                borderRadius: '4px', flexShrink: 0,
                              }}
                              onMouseEnter={(e) => (e.currentTarget.style.color = 'hsl(0, 70%, 60%)')}
                              onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                            >
                              ✕
                            </button>
                          )}
                          <div
                            style={{ minWidth: 0, flex: 1, cursor: isOptInMode ? 'pointer' : 'default' }}
                            onClick={isOptInMode ? () => toggleOptionalSkill(skill.id) : undefined}
                          >
                            <div style={{ fontWeight: 600, fontSize: '0.92rem', color: 'var(--text-primary)', wordBreak: 'break-word' }}>
                              {skill.name}
                            </div>
                            <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px', flexWrap: 'wrap' }}>
                              {skill.importance && IMPORTANCE_BADGE[skill.importance] && (() => {
                                const imp = IMPORTANCE_BADGE[skill.importance];
                                return (
                                  <span
                                    title={imp.tooltip}
                                    style={{
                                      fontSize: '0.68rem', fontWeight: 700, padding: '1px 6px',
                                      borderRadius: '10px', letterSpacing: '0.02em', cursor: 'help',
                                      background: imp.bg, color: imp.color,
                                      border: `1px solid ${imp.border}`, whiteSpace: 'nowrap',
                                    }}
                                  >
                                    {imp.label}
                                  </span>
                                );
                              })()}
                              {skill.provenance_label && (
                                <span style={{
                                  fontSize: '0.68rem', fontWeight: 600, padding: '1px 6px',
                                  borderRadius: '10px', letterSpacing: '0.02em', whiteSpace: 'nowrap',
                                  background: skill.provenance_label.includes('AI') || skill.provenance_label === 'Your addition'
                                    ? 'hsla(38, 92%, 50%, 0.15)' : 'hsla(174, 72%, 56%, 0.12)',
                                  color: skill.provenance_label.includes('AI') || skill.provenance_label === 'Your addition'
                                    ? 'hsl(38, 82%, 55%)' : 'hsl(174, 65%, 45%)',
                                  border: `1px solid ${
                                    skill.provenance_label.includes('AI') || skill.provenance_label === 'Your addition'
                                      ? 'hsla(38, 92%, 50%, 0.3)' : 'hsla(174, 72%, 56%, 0.25)'
                                  }`,
                                }}>
                                  {skill.provenance_label}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>

                        {isIncluded ? (
                          <div className="skill-toggle" style={{ flexShrink: 0, marginLeft: 'auto' }}>
                            {BEHAVIORAL_LEVELS.map(({ label, value, tooltip, color }) => {
                              const isActive = proficiency[skill.id] === value;
                              return (
                                <button
                                  key={value}
                                  type="button"
                                  title={tooltip}
                                  id={`skill-${skill.id}-${label.toLowerCase().replace(' ', '-')}`}
                                  className={`skill-toggle__btn ${isActive ? 'active' : ''}`}
                                  onClick={() => setLevel(skill.id, value)}
                                  style={isActive ? { color, borderColor: color } : {}}
                                >
                                  {label}
                                </button>
                              );
                            })}
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            onClick={() => toggleOptionalSkill(skill.id)}
                            style={{ fontSize: '0.76rem', padding: '4px 10px', color: 'var(--teal)', borderColor: 'rgba(0, 201, 167, 0.3)', marginLeft: 'auto' }}
                          >
                            + Add to roadmap
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          });

        const selectedDomainCount = domainOptionalSkills.filter((s) => selectedOptionalIds.has(s.id)).length;
        const selectedGeneralCount = generalNoiseSkills.filter((s) => selectedOptionalIds.has(s.id)).length;

        return (
          <>
            {/* 1. Essential Skills */}
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--teal)', marginBottom: '12px' }}>
                ★ ESSENTIAL CORE SKILLS ({essentialSkills.length}):
              </div>
              {renderCategoryList(groupedEssential, false)}
            </div>

            {/* 2. Optional Supporting Domain & Technical Competencies (Accordion, Opt-In per skill) */}
            {domainOptionalSkills.length > 0 && (
              <div style={{ marginBottom: '20px' }}>
                <button
                  type="button"
                  id="toggle-optional-skills-btn"
                  onClick={() => setShowOptional(!showOptional)}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    borderRadius: 'var(--r-md)',
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    fontSize: '0.85rem',
                    fontWeight: 600,
                    transition: 'all 0.15s ease',
                  }}
                >
                  <span>
                    {showOptional ? '▼ Hide' : '▶ Show'} Supporting & Optional Tools / Competencies ({selectedDomainCount}/{domainOptionalSkills.length} selected)
                  </span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                    {showOptional ? 'Collapse section' : 'Expand to pick supporting tools'}
                  </span>
                </button>
                {showOptional && (
                  <div style={{ marginTop: '14px', paddingLeft: '8px', borderLeft: '2px solid var(--border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                        Check only the supporting skills you want included in your learning roadmap:
                      </span>
                      <div style={{ display: 'flex', gap: '8px' }}>
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          style={{ fontSize: '0.74rem', padding: '3px 8px' }}
                          onClick={() => {
                            setSelectedOptionalIds((prev) => {
                              const next = new Set(prev);
                              domainOptionalSkills.forEach((s) => next.add(s.id));
                              return next;
                            });
                          }}
                        >
                          Select All ({domainOptionalSkills.length})
                        </button>
                        {selectedDomainCount > 0 && (
                          <button
                            type="button"
                            className="btn btn--ghost btn--sm"
                            style={{ fontSize: '0.74rem', padding: '3px 8px', color: 'var(--text-muted)' }}
                            onClick={() => {
                              setSelectedOptionalIds((prev) => {
                                const next = new Set(prev);
                                domainOptionalSkills.forEach((s) => next.delete(s.id));
                                return next;
                              });
                            }}
                          >
                            Clear ({selectedDomainCount})
                          </button>
                        )}
                      </div>
                    </div>
                    {renderCategoryList(groupedDomainOptional, true)}
                  </div>
                )}
              </div>
            )}

            {/* 3. General Foundational & Cognitive Competencies (Browse & Opt-In Individual Items) */}
            {generalNoiseSkills.length > 0 && (
              <div style={{ marginBottom: '24px', padding: '12px 16px', borderRadius: 'var(--r-md)', border: '1px dashed var(--border)', background: 'rgba(255,255,255,0.02)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                  <button
                    type="button"
                    id="toggle-general-noise"
                    onClick={() => setShowGeneralCompetencies(!showGeneralCompetencies)}
                    style={{
                      background: 'none', border: 'none', padding: 0,
                      fontSize: '0.82rem', color: 'var(--text-muted)', cursor: 'pointer',
                      display: 'flex', alignItems: 'center', gap: '8px', fontWeight: 600,
                    }}
                  >
                    <span>{showGeneralCompetencies ? '▼ Hide' : '▶ Browse'} general foundational & cognitive competencies ({selectedGeneralCount}/{generalNoiseSkills.length} selected)</span>
                  </button>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', opacity: 0.7 }}>
                    {selectedGeneralCount > 0 ? `${selectedGeneralCount} added to roadmap` : 'None selected by default'}
                  </span>
                </div>
                {showGeneralCompetencies && (
                  <div style={{ marginTop: '14px', paddingTop: '10px', borderTop: '1px solid var(--border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                      <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', margin: 0 }}>
                        Cross-cutting foundational abilities from O*NET. Click <strong>+ Add to roadmap</strong> on any item you wish to track:
                      </p>
                      {selectedGeneralCount > 0 && (
                        <button
                          type="button"
                          className="btn btn--ghost btn--sm"
                          style={{ fontSize: '0.74rem', padding: '3px 8px', color: 'var(--text-muted)' }}
                          onClick={() => {
                            setSelectedOptionalIds((prev) => {
                              const next = new Set(prev);
                              generalNoiseSkills.forEach((s) => next.delete(s.id));
                              return next;
                            });
                          }}
                        >
                          Clear selected ({selectedGeneralCount})
                        </button>
                      )}
                    </div>
                    {renderCategoryList(groupedGeneralNoise, true)}
                  </div>
                )}
              </div>
            )}
          </>
        );
      })()}

      {/* Add Custom Skill & Reset Bar */}
      <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {showAddForm ? (
          <form
            onSubmit={handleAddSkill}
            style={{
              padding: '14px', background: 'var(--bg-elevated)',
              borderRadius: 'var(--r-md)', border: '1px dashed var(--accent-border)',
              display: 'flex', flexDirection: 'column', gap: '10px',
            }}
          >
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Add a Skill or Tool:</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="e.g. Supabase, TailwindCSS, Django…"
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                autoFocus
                style={{ flex: 1, minWidth: '160px' }}
              />
              <select
                value={newSkillCategory}
                onChange={(e) => setNewSkillCategory(e.target.value)}
                style={{
                  background: 'var(--bg-input)', color: 'var(--text-primary)',
                  border: '1px solid var(--border)', borderRadius: 'var(--r-md)',
                  padding: '8px 12px', fontSize: '0.85rem',
                }}
              >
                {SKILL_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
              <button type="button" className="btn btn--ghost btn--sm" onClick={() => setShowAddForm(false)}>
                Cancel
              </button>
              <button type="submit" className="btn btn--primary btn--sm" disabled={!newSkillName.trim()}>
                Add to Profile
              </button>
            </div>
          </form>
        ) : (
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn--ghost btn--sm"
              onClick={() => setShowAddForm(true)}
              style={{ flex: 1, minWidth: '220px', borderStyle: 'dashed' }}
            >
              + Add a specific stack or tool (e.g. Supabase, Docker, Vue)
            </button>
            {skills.length !== initialSkills.length && (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={handleResetSkills}
                style={{ color: 'var(--text-muted)' }}
                title="Restore all default taxonomy skills"
              >
                ↺ Reset Skills
              </button>
            )}
          </div>
        )}
      </div>

      {error && (
        <div className="alert alert--error" style={{ marginBottom: '16px' }}>{error}</div>
      )}

      <button
        id="save-skills-btn"
        type="button"
        className="btn btn--primary btn--full"
        onClick={handleSave}
        disabled={loading}
      >
        {loading ? (
          <><span className="spinner" /> Calibrating skill profile…</>
        ) : (
          'Save & Generate Learning Pathway'
        )}
      </button>

      {/* Floating Bottom Toast for Undo */}
      {deletedSkillHistory && (
        <Toast
          message={`Removed "${deletedSkillHistory.skill.name}" from your roadmap.`}
          confirmLabel="↺ Undo"
          cancelLabel="Dismiss"
          onConfirm={handleUndoDelete}
          onCancel={() => setDeletedSkillHistory(null)}
        />
      )}
    </div>
  );
}


// ─── Onboarding Orchestrator ──────────────────────────────────────────────────

/*
  Sub-states for the career search phase:
    'input'       — 1a: free text box
    'grid'        — 1b: card grid (disambiguation_required response)
    'ai_form'     — 1c: structured AI fallback form
    'not_found'   — 1e: hard failure
    'assessment'  — 2:  skill rating
*/
export default function Onboarding({ user, onComplete }) {
  const storageKey = user?.id ? `cb_onboarding_draft_${user.id}` : null;
  const savedDraft = (() => {
    if (!storageKey || typeof window === 'undefined') return null;
    try {
      const raw = window.sessionStorage.getItem(storageKey);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  })();

  const [phase, setPhase]               = useState(() => savedDraft?.phase || 'input');
  const [candidates, setCandidates]     = useState(() => savedDraft?.candidates || []);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibratingTitle, setCalibratingTitle] = useState('');
  const [career, setCareer]             = useState(() => savedDraft?.career || null);
  const [skills, setSkills]             = useState(() => savedDraft?.skills || []);
  const [source, setSource]             = useState(() => savedDraft?.source || null);
  const [savedPreviousCareer, setSavedPreviousCareer] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);

  useEffect(() => {
    if (!storageKey || typeof window === 'undefined') return;
    try {
      window.sessionStorage.setItem(
        storageKey,
        JSON.stringify({ phase, candidates, career, skills, source })
      );
    } catch {
      // Ignore sessionStorage quota errors
    }
  }, [storageKey, phase, candidates, career, skills, source]);

  // Handle the raw response from the backend career-search endpoint
  const handleSearchResult = useCallback((result) => {
    if (result.status === 'disambiguation_required') {
      setCandidates(result.candidates);
      setPhase('grid');
    } else if (result.status === 'no_candidates') {
      setPhase('ai_form');
    } else if (result.status === 'generated' && Array.isArray(result.related_candidates) && result.related_candidates.length > 0) {
      // Always display the AI proposal alongside closest vector-matched catalog candidates
      const aiOption = {
        id: '__ai_generated__',
        title: result.career.title,
        description: result.career.description,
        similarity: 0.98,
        is_ai_proposal: true,
        _raw_result: result,
      };
      setCandidates([aiOption, ...result.related_candidates]);
      setPhase('grid');
    } else if (result.status === 'matched' || result.status === 'generated') {
      // High-confidence auto-match or AI-generated profile
      if (!result.career || !result.skills) {
        setPhase('not_found');
        return;
      }
      setCareer(result.career);
      setSkills(result.skills);
      setSource(result.status);
      setPhase('assessment');
    } else {
      setPhase('not_found');
    }
  }, []);

  // User selected a card from the grid — fetch exact career record by ID directly
  const handleCardSelect = useCallback(async (cand) => {
    if (cand.id === '__ai_generated__' && cand._raw_result) {
      setIsCalibrating(false);
      setCareer(cand._raw_result.career);
      setSkills(cand._raw_result.skills);
      setSource('generated');
      setPhase('assessment');
      return;
    }
    setIsCalibrating(true);
    setCalibratingTitle(cand.title);
    try {
      const result = await getCareerById(cand.id);
      handleSearchResult(result);
    } catch {
      // Fallback: search by title if ID fetch fails
      try {
        const result = await searchCareer(cand.title);
        handleSearchResult(result);
      } catch {
        setCareer({ id: cand.id, title: cand.title, description: cand.description, provenance_label: 'Source: Catalog' });
        setSkills([]);
        setSource('matched');
        setPhase('assessment');
      }
    } finally {
      setIsCalibrating(false);
    }
  }, [handleSearchResult]);

  const handleLogout = async () => {
    if (storageKey && typeof window !== 'undefined') {
      try { window.sessionStorage.removeItem(storageKey); } catch {}
    }
    await supabase.auth.signOut();
  };
  const handleCompleteWithCleanup = useCallback((payload) => {
    if (storageKey && typeof window !== 'undefined') {
      try { window.sessionStorage.removeItem(storageKey); } catch {}
    }
    onComplete(payload);
  }, [storageKey, onComplete]);

  const containerWidth = phase === 'assessment' ? '840px' : '620px';

  return (
    <>
      <div className="page-center" style={{ minHeight: '100svh', padding: '40px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div className="container" style={{ maxWidth: containerWidth, width: '100%', transition: 'max-width 0.25s ease' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
            <div className="logo-mark">
              <div className="logo-mark__icon">CB</div>
              Career Beacon
            </div>
          </div>

          <div className="card" style={{ padding: phase === 'assessment' ? '36px 32px' : '32px 28px' }}>
            {/* Resume Banner if user backed out of a career */}
            {(phase === 'input' || phase === 'grid') && savedPreviousCareer && (
              <div style={{
                padding: '12px 14px', background: 'var(--bg-elevated)',
                border: '1px solid var(--accent-border)', borderRadius: 'var(--r-md)',
                marginBottom: '20px', display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap',
              }}>
                <div style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Previous selection: </span>
                  <strong>{savedPreviousCareer.career.title}</strong>
                </div>
                <button
                  type="button"
                  id="resume-previous-career-btn"
                  className="btn btn--primary btn--sm"
                  onClick={() => {
                    setCareer(savedPreviousCareer.career);
                    setSkills(savedPreviousCareer.skills);
                    setSource(savedPreviousCareer.source);
                    setPhase('assessment');
                  }}
                >
                  Resume this career →
                </button>
              </div>
            )}

            {/* 1a: Free text input */}
            {phase === 'input' && (
              <CareerInput
                user={user}
                onResult={handleSearchResult}
                onLogoutRequest={() => setShowLogoutToast(true)}
              />
            )}

            {/* 1b: Card grid */}
            {phase === 'grid' && (
              isCalibrating ? (
                <div style={{ textAlign: 'center', padding: '40px 20px' }}>
                  <div className="spinner" style={{ margin: '0 auto 16px auto', width: '32px', height: '32px' }} />
                  <h3 style={{ marginBottom: '8px', fontSize: '1.1rem' }}>Calibrating Core Competencies</h3>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                    Standardizing vocational pillars for <strong>{calibratingTitle}</strong>...
                  </p>
                </div>
              ) : (
                <CareerCardGrid
                  candidates={candidates}
                  onSelect={handleCardSelect}
                  onNoneMatch={(target) => setPhase(target === 'not_found' ? 'not_found' : 'ai_form')}
                  onBack={() => { setCandidates([]); setPhase('input'); }}
                />
              )
            )}

            {/* 1c–1d: AI fallback form */}
            {phase === 'ai_form' && (
              <AIFallbackForm
                onResult={(result) => {
                  if (result.status === 'disambiguation_required') {
                    setCandidates(result.candidates);
                    setPhase('grid');
                  } else if (result.status === 'generated' && result.related_candidates && result.related_candidates.length > 0) {
                    // Unified Co-existence: Offer the synthesized AI Career alongside the closest Catalog Standards
                    const aiOption = {
                      id: '__ai_generated__',
                      title: result.career.title,
                      description: result.career.description,
                      similarity: 0.98,
                      is_ai_proposal: true,
                      _raw_result: result,
                    };
                    setCandidates([aiOption, ...result.related_candidates]);
                    setPhase('grid');
                  } else if (result.status === 'matched' || result.status === 'generated') {
                    setCareer(result.career);
                    setSkills(result.skills);
                    setSource(result.status);
                    setPhase('assessment');
                  } else {
                    setPhase('not_found');
                  }
                }}
                onBack={() => setPhase(candidates.length > 0 ? 'grid' : 'input')}
              />
            )}

            {/* 1e: Hard failure */}
            {phase === 'not_found' && (
              <CareerNotFound
                onRestart={() => {
                  setCandidates([]);
                  setCareer(null);
                  setSkills([]);
                  setPhase('input');
                }}
              />
            )}

            {/* 2: Skill assessment */}
            {phase === 'assessment' && career && (
              <>
                <button
                  type="button"
                  id="onboarding-back-btn"
                  onClick={() => setShowLogoutToast(true)}
                  style={{
                    background: 'none', border: 'none', color: 'var(--text-muted)',
                    fontSize: '0.85rem', cursor: 'pointer', padding: '0 0 16px',
                    display: 'flex', alignItems: 'center', gap: '4px',
                  }}
                >
                  ← Change career target
                </button>

                <SkillAssessment
                  career={career}
                  skills={skills}
                  source={source}
                  userId={user.id}
                  onComplete={handleCompleteWithCleanup}
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
            phase === 'assessment'
              ? 'Going back will discard your current skill customizations. Are you sure?'
              : 'Are you sure you want to log out?'
          }
          confirmLabel={phase === 'assessment' ? 'Yes, go back' : 'Yes, log out'}
          onConfirm={() => {
            setShowLogoutToast(false);
            if (phase === 'assessment') {
              setSavedPreviousCareer({ career, skills, source });
              setCareer(null);
              setSkills([]);
              setPhase('input');
            } else {
              handleLogout();
            }
          }}
          onCancel={() => setShowLogoutToast(false)}
        />
      )}
    </>
  );
}
