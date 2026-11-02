// src/pages/LearnerOnboarding.jsx
// Handles the full learner onboarding flow (career search -> skill assessment).
import { useState, useEffect, useCallback } from 'react';
import { supabase } from '../lib/SupabaseClient';
import { searchCareer, getCareerById, saveSkills } from '../lib/api';
import Toast from '../components/Toast';
import ThemeSelector from '../components/ThemeSelector';
import {
  Compass,
  Search,
  Sparkles,
  ChevronDown,
  ChevronRight,
  RotateCcw,
  X,
  Plus,
  Check,
  ArrowLeft,
  ArrowRight,
  LogOut,
  Target,
} from '../components/Icons';

// ─── Constants ──────────────────────────────────────────────────────────────

const BEHAVIORAL_LEVELS = [
  {
    label: 'Not Yet',
    value: 0,
    tooltip: 'No exposure yet — the system will prioritise foundational concepts for this skill.',
    color: 'var(--text-muted)',
  },
  {
    label: 'Novice',
    value: 20,
    tooltip: 'Understand basic concepts; require guidance and oversight applying them in practice.',
    color: 'var(--status-info)',
  },
  {
    label: 'Intermediate',
    value: 50,
    tooltip: 'Apply independently in standard workflows; solve routine problems using industry references.',
    color: 'var(--accent)',
  },
  {
    label: 'Advanced',
    value: 80,
    tooltip: 'Execute complex tasks, lead standards, guide peers, and optimize workflows and quality.',
    color: 'var(--status-success)',
  },
];

const CATEGORY_METADATA = {
  'Technical Skills':           { color: 'var(--accent)',         bg: 'var(--accent-soft)' },
  'Domain Knowledge':           { color: 'var(--status-info)',    bg: 'var(--status-info-bg)' },
  'Tools & Systems':            { color: 'var(--teal)',           bg: 'var(--teal-soft)' },
  'Interpersonal & Leadership': { color: 'var(--status-warning)', bg: 'var(--status-warning-bg)' },
  'Custom Stack':               { color: 'var(--accent)',         bg: 'var(--accent-soft)' },
  'General':                    { color: 'var(--text-secondary)', bg: 'var(--surface-elevated)' },
  'General Competencies':       { color: 'var(--text-secondary)', bg: 'var(--surface-elevated)' },
};

const IMPORTANCE_BADGE = {
  essential: {
    label: 'Essential',
    tooltip: 'Importance score >= 70% (raw score >= 3.8/5.0 in O*NET or designated essential by ESCO)',
    color: 'var(--status-success)',
    bg: 'var(--status-success-bg)',
    border: 'var(--status-success-bd)',
  },
  optional: {
    label: 'Optional',
    tooltip: 'Supporting competency: Importance score < 70% in O*NET or designated optional by ESCO',
    color: 'var(--text-secondary)',
    bg: 'var(--surface-elevated)',
    border: 'var(--border)',
  },
};

const SKILL_CATEGORIES = [
  'Technical Skills',
  'Domain Knowledge',
  'Tools & Systems',
  'Interpersonal & Leadership',
  'Custom Stack',
];

function similarityLabel(score) {
  const safeScore = typeof score === 'number' && !isNaN(score) ? score : 0.85;
  if (safeScore >= 0.90) return { text: 'Excellent match', badgeClass: 'badge--success' };
  if (safeScore >= 0.80) return { text: 'Strong match',    badgeClass: 'badge--accent' };
  if (safeScore >= 0.70) return { text: 'Good match',      badgeClass: 'badge--info' };
  return                         { text: 'Possible match', badgeClass: 'badge--warning' };
}

// ─── Step 1a: Free-text Career Input ────────────────────────────────────────

function CareerInput({ user, onResult, onLogoutRequest }) {
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const displayName =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.first_name ||
    (user?.email ? user.email.split('@')[0] : '');

  const handleSearch = useCallback(
    async (e) => {
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
    },
    [query, onResult]
  );

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      {displayName && (
        <div
          style={{
            fontSize: '0.84rem',
            fontWeight: 600,
            color: 'var(--accent)',
            marginBottom: '6px',
          }}
        >
          Welcome, {displayName}
        </div>
      )}
      <h2 style={{ marginBottom: '8px' }}>Define your target career</h2>
      <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
        Enter the role you are working towards. We will benchmark it against O*NET and ESCO occupational taxonomies to build your skill profile.
      </p>

      <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="career-input">Target Occupation or Role</label>
          <div style={{ position: 'relative' }}>
            <Search
              size={17}
              color="var(--text-muted)"
              style={{
                position: 'absolute',
                left: '13px',
                top: '50%',
                transform: 'translateY(-50%)',
                pointerEvents: 'none',
              }}
            />
            <input
              id="career-input"
              type="text"
              placeholder="e.g. Frontend Developer, Data Scientist, Financial Analyst..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              autoFocus
              autoComplete="off"
              style={{ paddingLeft: '40px' }}
            />
          </div>
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
              <span>Searching labor taxonomy...</span>
            </>
          ) : (
            <>
              <span>Find Career Pathway</span>
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="alert alert--error" style={{ marginTop: '16px' }}>
          {error}
        </div>
      )}

      <div style={{ textAlign: 'center', marginTop: '24px' }}>
        <button
          id="onboarding-logout-btn"
          type="button"
          onClick={onLogoutRequest}
          className="btn btn--ghost btn--xs"
          style={{ border: 'none', color: 'var(--text-muted)' }}
        >
          <LogOut size={13} />
          <span>Sign out</span>
        </button>
      </div>
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

      <h2 style={{ marginBottom: '6px' }}>Select your career pathway</h2>
      <p style={{ marginBottom: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        We found {candidates.length} match{candidates.length !== 1 ? 'es' : ''} in our occupational catalog. Choose the option that best aligns with your goal.
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', marginBottom: '22px' }}>
        {candidates.map((cand) => {
          const conf = similarityLabel(cand.similarity);
          const simPct = Math.round(
            (typeof cand.similarity === 'number' && !isNaN(cand.similarity) ? cand.similarity : 0.85) * 100
          );

          return (
            <button
              key={cand.id}
              type="button"
              id={`career-card-${cand.id}`}
              onClick={() => onSelect(cand)}
              className="card card--interactive"
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                justifyContent: 'space-between',
                textAlign: 'left',
                width: '100%',
                padding: '16px 18px',
                gap: '16px',
                cursor: 'pointer',
              }}
            >
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: '0.96rem', color: 'var(--text-primary)', marginBottom: '4px' }}>
                  {cand.title}
                </div>
                {cand.description && (
                  <div style={{ fontSize: '0.82rem', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
                    {cand.description.length > 165 ? cand.description.slice(0, 165) + '...' : cand.description}
                  </div>
                )}
              </div>

              <div style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                {cand.is_ai_proposal ? (
                  <span className="badge badge--accent">
                    <Sparkles size={11} />
                    <span>AI Career Target</span>
                  </span>
                ) : (
                  <span className={`badge ${conf.badgeClass}`}>{conf.text}</span>
                )}
                <span className="mono" style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {cand.is_ai_proposal ? 'AI Synthesized' : `${simPct}% match`}
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
          className="btn btn--secondary btn--full"
          onClick={() => onNoneMatch('ai_form')}
        >
          <Sparkles size={15} />
          <span>None of these match — describe with AI</span>
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', flexWrap: 'wrap', gap: '8px' }}>
          <button
            type="button"
            className="btn btn--ghost btn--xs"
            onClick={onBack}
            style={{ border: 'none' }}
          >
            <ArrowLeft size={14} />
            <span>Change search</span>
          </button>
          <button
            id="close-loop-btn"
            type="button"
            className="btn btn--ghost btn--xs"
            onClick={() => onNoneMatch('not_found')}
            style={{ border: 'none', color: 'var(--text-muted)' }}
          >
            <span>Request curriculum evaluation</span>
            <ArrowRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Step 1c–1d: AI Fallback Structured Form ─────────────────────────────────

function AIFallbackForm({ onResult, onBack }) {
  const [industry, setIndustry] = useState('');
  const [roleType, setRoleType] = useState('');
  const [focus, setFocus] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = useCallback(
    async (e) => {
      e.preventDefault();
      if (!industry.trim() || !roleType.trim() || !focus.trim()) return;

      setLoading(true);
      setError(null);
      const richQuery = `${roleType.trim()} in ${industry.trim()} — ${focus.trim()}`;

      try {
        const result = await searchCareer(richQuery, true);
        onResult(result);
      } catch (err) {
        setError(err.message || 'AI search failed. Please try again.');
      } finally {
        setLoading(false);
      }
    },
    [industry, roleType, focus, onResult]
  );

  const isValid = industry.trim() && roleType.trim() && focus.trim();

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <h2 style={{ marginBottom: '6px' }}>Describe your target role</h2>
      <p style={{ marginBottom: '20px', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
        Provide a brief breakdown of your domain and responsibilities so we can map them to occupational competencies.
      </p>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="ai-industry">Industry / Domain</label>
          <input
            id="ai-industry"
            type="text"
            placeholder="e.g. Software Engineering, Healthcare, Finance, Civil Engineering..."
            value={industry}
            onChange={(e) => setIndustry(e.target.value)}
            autoFocus
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="ai-role">Typical Role / Title</label>
          <input
            id="ai-role"
            type="text"
            placeholder="e.g. Developer, Analyst, Engineer, Practitioner..."
            value={roleType}
            onChange={(e) => setRoleType(e.target.value)}
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label htmlFor="ai-focus">Core Responsibilities &amp; Focus</label>
          <textarea
            id="ai-focus"
            placeholder="e.g. Building data pipelines, deploying predictive models, and maintaining cloud infrastructure..."
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
            rows={3}
            maxLength={200}
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
            <>
              <span className="spinner" />
              <span>Analyzing career profile...</span>
            </>
          ) : (
            <>
              <Sparkles size={15} />
              <span>Map Career Competencies</span>
            </>
          )}
        </button>
      </form>

      {error && (
        <div className="alert alert--error" style={{ marginTop: '16px' }}>
          {error}
        </div>
      )}

      <button
        type="button"
        className="btn btn--ghost btn--sm"
        onClick={onBack}
        style={{ marginTop: '14px', width: '100%' }}
      >
        <ArrowLeft size={14} />
        <span>Back to career list</span>
      </button>
    </div>
  );
}

// ─── Step 1e: Hard Failure ───────────────────────────────────────────────────

function CareerNotFound({ onRestart }) {
  return (
    <div style={{ textAlign: 'center', padding: '16px 0' }}>
      <div className="step-indicator" style={{ justifyContent: 'center' }}>
        <div className="step-dot active" />
        <div className="step-dot" />
      </div>

      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: 'var(--r-md)',
          background: 'var(--surface-elevated)',
          border: '1px solid var(--border)',
          color: 'var(--text-secondary)',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: '16px',
        }}
      >
        <Search size={22} />
      </div>

      <h2 style={{ marginBottom: '8px' }}>Career not found</h2>
      <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '24px', lineHeight: 1.6 }}>
        We searched our occupational catalog and taxonomy models but could not verify a reliable match for this query. Try a broader occupation title.
      </p>
      <button
        id="career-restart-btn"
        type="button"
        className="btn btn--primary"
        onClick={onRestart}
      >
        <RotateCcw size={15} />
        <span>Try a Different Career Title</span>
      </button>
      <div
        style={{
          marginTop: '20px',
          padding: '12px 16px',
          background: 'var(--surface-elevated)',
          borderRadius: 'var(--r-md)',
          border: '1px solid var(--border)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
        }}
      >
        <span>Need a specialized discipline added? Request a curriculum evaluation at </span>
        <a
          href="mailto:careerbeacon@gmail.com?subject=Career%20Taxonomy%20Request"
          style={{ color: 'var(--accent)', fontWeight: 600 }}
        >
          careerbeacon@gmail.com
        </a>
        .
      </div>
    </div>
  );
}

// ─── Step 2: Skill Assessment ────────────────────────────────────────────────

function SkillAssessment({ career, skills: initialSkills, source, userId, onComplete }) {
  const [skills, setSkills] = useState(initialSkills);
  const [proficiency, setProficiency] = useState(() =>
    Object.fromEntries(initialSkills.map((s) => [s.id, 0]))
  );
  const [selectedOptionalIds, setSelectedOptionalIds] = useState(() => new Set());
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillCategory, setNewSkillCategory] = useState('Technical Skills');
  const [showAddForm, setShowAddForm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [deletedSkillHistory, setDeletedSkillHistory] = useState(null);
  const [showOptional, setShowOptional] = useState(false);
  const [showGeneralCompetencies, setShowGeneralCompetencies] = useState(false);

  const setLevel = (skillId, value) => {
    setProficiency((prev) => ({ ...prev, [skillId]: value }));
  };

  const toggleOptionalSkill = (skillId) => {
    setSelectedOptionalIds((prev) => {
      const next = new Set(prev);
      if (next.has(skillId)) next.delete(skillId);
      else next.add(skillId);
      return next;
    });
  };

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
      id: tempId,
      name: cleanName,
      category: newSkillCategory,
      importance: null,
      source_origin: 'manual',
      provenance_label: 'Your addition',
    };

    setSkills((prev) => [...prev, newSkill]);
    setProficiency((prev) => ({ ...prev, [tempId]: 0 }));
    setNewSkillName('');
    setShowAddForm(false);
  };

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

  const selectedDomainCount = domainOptionalSkills.filter((s) => selectedOptionalIds.has(s.id)).length;
  const selectedGeneralCount = generalNoiseSkills.filter((s) => selectedOptionalIds.has(s.id)).length;

  const renderCategoryList = (groupedMap, isOptInMode = false) =>
    Object.entries(groupedMap).map(([category, catSkills]) => {
      if (!catSkills || catSkills.length === 0) return null;
      const meta = CATEGORY_METADATA[category] || CATEGORY_METADATA['General'];

      return (
        <div key={category} style={{ marginBottom: '20px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              marginBottom: '10px',
              paddingBottom: '6px',
              borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <span
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
                padding: '2px 8px',
                borderRadius: 'var(--r-sm)',
                background: meta.bg,
                color: meta.color,
              }}
            >
              {category}
            </span>
            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
              {catSkills.length} skill{catSkills.length !== 1 ? 's' : ''}
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {catSkills.map((skill) => {
              const isIncluded = !isOptInMode || selectedOptionalIds.has(skill.id);
              return (
                <div
                  key={skill.id}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '14px',
                    padding: '12px 14px',
                    background: isIncluded ? 'var(--surface)' : 'var(--surface-subtle)',
                    border: isIncluded ? '1px solid var(--border)' : '1px dashed var(--border)',
                    borderRadius: 'var(--r-md)',
                    flexWrap: 'wrap',
                    opacity: isIncluded ? 1 : 0.78,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: '1 1 200px' }}>
                    {isOptInMode ? (
                      <input
                        type="checkbox"
                        checked={isIncluded}
                        onChange={() => toggleOptionalSkill(skill.id)}
                        title={isIncluded ? 'Included in your roadmap' : 'Click to include in your roadmap'}
                        style={{ width: '16px', height: '16px', cursor: 'pointer', accentColor: 'var(--accent)', flexShrink: 0 }}
                      />
                    ) : (
                      <button
                        type="button"
                        aria-label={`Remove ${skill.name}`}
                        onClick={() => handleDeleteSkill(skill.id)}
                        title="Remove skill from your roadmap"
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '4px',
                          borderRadius: '4px',
                          display: 'inline-flex',
                          flexShrink: 0,
                        }}
                      >
                        <X size={14} />
                      </button>
                    )}

                    <div
                      style={{ minWidth: 0, flex: 1, cursor: isOptInMode ? 'pointer' : 'default' }}
                      onClick={isOptInMode ? () => toggleOptionalSkill(skill.id) : undefined}
                    >
                      <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                        {skill.name}
                      </div>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center', marginTop: '4px', flexWrap: 'wrap' }}>
                        {skill.importance && IMPORTANCE_BADGE[skill.importance] && (() => {
                          const imp = IMPORTANCE_BADGE[skill.importance];
                          return (
                            <span
                              title={imp.tooltip}
                              style={{
                                fontSize: '0.68rem',
                                fontWeight: 600,
                                padding: '1px 7px',
                                borderRadius: 'var(--r-full)',
                                background: imp.bg,
                                color: imp.color,
                                border: `1px solid ${imp.border}`,
                              }}
                            >
                              {imp.label}
                            </span>
                          );
                        })()}
                        {skill.provenance_label && (
                          <span className="badge badge--neutral" style={{ fontSize: '0.68rem', padding: '1px 7px' }}>
                            {skill.provenance_label}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {isIncluded ? (
                    <div className="skill-toggle" style={{ flexShrink: 0, marginLeft: 'auto' }}>
                      {BEHAVIORAL_LEVELS.map(({ label, value, tooltip }) => {
                        const isActive = proficiency[skill.id] === value;
                        return (
                          <button
                            key={value}
                            type="button"
                            title={tooltip}
                            id={`skill-${skill.id}-${label.toLowerCase().replace(' ', '-')}`}
                            className={`skill-toggle__btn ${isActive ? 'active' : ''}`}
                            onClick={() => setLevel(skill.id, value)}
                          >
                            {label}
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn btn--ghost btn--xs"
                      onClick={() => toggleOptionalSkill(skill.id)}
                      style={{ marginLeft: 'auto', color: 'var(--accent)', borderColor: 'var(--accent-border)' }}
                    >
                      <Plus size={12} />
                      <span>Add to roadmap</span>
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      );
    });

  return (
    <div>
      <div className="step-indicator">
        <div className="step-dot done" />
        <div className="step-dot active" />
      </div>

      {/* Career Header */}
      <div style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '6px', flexWrap: 'wrap' }}>
          <h2 style={{ margin: 0 }}>{career.title}</h2>
          {career.provenance_label ? (
            <span className={`badge ${career.provenance_label.includes('AI') ? 'badge--accent' : 'badge--success'}`}>
              {career.provenance_label}
            </span>
          ) : source === 'matched' ? (
            <span className="badge badge--success">Source: Catalog</span>
          ) : (
            <span className="badge badge--accent">AI Proposal (Editable)</span>
          )}
        </div>
        {career.description && (
          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>{career.description}</p>
        )}
      </div>

      {/* Proficiency Scale Guide */}
      <div
        style={{
          marginBottom: '22px',
          padding: '14px 16px',
          background: 'var(--surface-elevated)',
          borderRadius: 'var(--r-md)',
          border: '1px solid var(--border)',
          fontSize: '0.82rem',
          color: 'var(--text-secondary)',
        }}
      >
        <div style={{ fontWeight: 700, color: 'var(--text-primary)', marginBottom: '6px' }}>
          Proficiency Calibration Guide
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px 20px' }}>
          {BEHAVIORAL_LEVELS.map(({ label, value, tooltip, color }) => (
            <span key={value} title={tooltip} style={{ cursor: 'help', whiteSpace: 'nowrap' }}>
              <strong style={{ color }}>{label}</strong>
              <span style={{ color: 'var(--text-muted)' }}>
                {value > 0 ? ` (${value}%)` : ' — no prior exposure'}
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* 1. Essential Skills */}
      <div style={{ marginBottom: '20px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.82rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--accent)',
            marginBottom: '12px',
          }}
        >
          <Target size={15} />
          <span>Essential Core Competencies ({essentialSkills.length})</span>
        </div>
        {renderCategoryList(groupedEssential, false)}
      </div>

      {/* 2. Optional Supporting Domain Skills */}
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
              background: 'var(--surface-elevated)',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '0.85rem',
              fontWeight: 600,
            }}
          >
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
              {showOptional ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              <span>
                Supporting &amp; Optional Competencies ({selectedDomainCount}/{domainOptionalSkills.length} selected)
              </span>
            </span>
            <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
              {showOptional ? 'Collapse' : 'Expand'}
            </span>
          </button>

          {showOptional && (
            <div style={{ marginTop: '14px', paddingLeft: '12px', borderLeft: '2px solid var(--border)' }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '12px',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Select the supporting skills you want included in your learning roadmap:
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className="btn btn--ghost btn--xs"
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
                      className="btn btn--ghost btn--xs"
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

      {/* 3. General Foundational Competencies */}
      {generalNoiseSkills.length > 0 && (
        <div
          style={{
            marginBottom: '24px',
            padding: '12px 16px',
            borderRadius: 'var(--r-md)',
            border: '1px dashed var(--border)',
            background: 'var(--surface-subtle)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
            <button
              type="button"
              id="toggle-general-noise"
              onClick={() => setShowGeneralCompetencies(!showGeneralCompetencies)}
              style={{
                background: 'none',
                border: 'none',
                padding: 0,
                fontSize: '0.82rem',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 600,
              }}
            >
              {showGeneralCompetencies ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
              <span>
                General foundational competencies ({selectedGeneralCount}/{generalNoiseSkills.length} selected)
              </span>
            </button>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {selectedGeneralCount > 0 ? `${selectedGeneralCount} added` : 'Optional'}
            </span>
          </div>
          {showGeneralCompetencies && (
            <div style={{ marginTop: '14px', paddingTop: '12px', borderTop: '1px solid var(--border)' }}>
              {renderCategoryList(groupedGeneralNoise, true)}
            </div>
          )}
        </div>
      )}

      {/* Add Custom Skill & Reset Bar */}
      <div style={{ marginBottom: '24px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {showAddForm ? (
          <form
            onSubmit={handleAddSkill}
            style={{
              padding: '16px',
              background: 'var(--surface-elevated)',
              borderRadius: 'var(--r-md)',
              border: '1px solid var(--accent-border)',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            <div style={{ fontWeight: 600, fontSize: '0.85rem' }}>Add a Custom Skill or Tool</div>
            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              <input
                type="text"
                placeholder="e.g. Supabase, TailwindCSS, Django..."
                value={newSkillName}
                onChange={(e) => setNewSkillName(e.target.value)}
                autoFocus
                style={{ flex: 1, minWidth: '180px' }}
              />
              <select
                value={newSkillCategory}
                onChange={(e) => setNewSkillCategory(e.target.value)}
                style={{ width: 'auto', minWidth: '180px' }}
              >
                {SKILL_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>
                    {cat}
                  </option>
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
              <Plus size={14} />
              <span>Add a specific stack or tool (e.g. Docker, Vue, PyTorch)</span>
            </button>
            {skills.length !== initialSkills.length && (
              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={handleResetSkills}
                title="Restore all default taxonomy skills"
              >
                <RotateCcw size={14} />
                <span>Reset Skills</span>
              </button>
            )}
          </div>
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
            <span>Calibrating skill profile...</span>
          </>
        ) : (
          <>
            <span>Save &amp; Generate Learning Pathway</span>
            <ArrowRight size={16} />
          </>
        )}
      </button>

      {deletedSkillHistory && (
        <Toast
          message={`Removed "${deletedSkillHistory.skill.name}" from your roadmap.`}
          confirmLabel="Undo"
          cancelLabel="Dismiss"
          onConfirm={handleUndoDelete}
          onCancel={() => setDeletedSkillHistory(null)}
        />
      )}
    </div>
  );
}

// ─── Onboarding Orchestrator ──────────────────────────────────────────────────

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

  const [phase, setPhase] = useState(() => savedDraft?.phase || 'input');
  const [candidates, setCandidates] = useState(() => savedDraft?.candidates || []);
  const [isCalibrating, setIsCalibrating] = useState(false);
  const [calibratingTitle, setCalibratingTitle] = useState('');
  const [career, setCareer] = useState(() => savedDraft?.career || null);
  const [skills, setSkills] = useState(() => savedDraft?.skills || []);
  const [source, setSource] = useState(() => savedDraft?.source || null);
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

  const handleSearchResult = useCallback((result) => {
    if (result.status === 'disambiguation_required') {
      setCandidates(result.candidates);
      setPhase('grid');
    } else if (result.status === 'no_candidates') {
      setPhase('ai_form');
    } else if (
      result.status === 'generated' &&
      Array.isArray(result.related_candidates) &&
      result.related_candidates.length > 0
    ) {
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

  const handleCardSelect = useCallback(
    async (cand) => {
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
        try {
          const result = await searchCareer(cand.title);
          handleSearchResult(result);
        } catch {
          setCareer({
            id: cand.id,
            title: cand.title,
            description: cand.description,
            provenance_label: 'Source: Catalog',
          });
          setSkills([]);
          setSource('matched');
          setPhase('assessment');
        }
      } finally {
        setIsCalibrating(false);
      }
    },
    [handleSearchResult]
  );

  const handleLogout = async () => {
    if (storageKey && typeof window !== 'undefined') {
      try {
        window.sessionStorage.removeItem(storageKey);
      } catch {}
    }
    await supabase.auth.signOut();
  };

  const handleCompleteWithCleanup = useCallback(
    (payload) => {
      if (storageKey && typeof window !== 'undefined') {
        try {
          window.sessionStorage.removeItem(storageKey);
        } catch {}
      }
      onComplete(payload);
    },
    [storageKey, onComplete]
  );

  const containerWidth = phase === 'assessment' ? '860px' : '620px';

  return (
    <div style={{ minHeight: '100svh', display: 'flex', flexDirection: 'column', background: 'var(--background)' }}>
      {/* Top Bar */}
      <header
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'var(--surface)',
          padding: '14px 24px',
        }}
      >
        <div
          style={{
            maxWidth: '1080px',
            margin: '0 auto',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <div className="logo-mark">
            <div className="logo-mark__icon">
              <Compass size={18} />
            </div>
            <span>Career Beacon</span>
          </div>
          <ThemeSelector />
        </div>
      </header>

      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '36px 16px 56px',
        }}
      >
        <div className="container" style={{ maxWidth: containerWidth, width: '100%' }}>
          <div className="card" style={{ padding: phase === 'assessment' ? '36px 32px' : '32px 28px' }}>
            {/* Resume Banner */}
            {(phase === 'input' || phase === 'grid') && savedPreviousCareer && (
              <div
                style={{
                  padding: '12px 16px',
                  background: 'var(--accent-soft)',
                  border: '1px solid var(--accent-border)',
                  borderRadius: 'var(--r-md)',
                  marginBottom: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
              >
                <div style={{ fontSize: '0.85rem' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Previous selection: </span>
                  <strong style={{ color: 'var(--text-primary)' }}>{savedPreviousCareer.career.title}</strong>
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
                  <span>Resume career</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            )}

            {phase === 'input' && (
              <CareerInput
                user={user}
                onResult={handleSearchResult}
                onLogoutRequest={() => setShowLogoutToast(true)}
              />
            )}

            {phase === 'grid' &&
              (isCalibrating ? (
                <div style={{ textAlign: 'center', padding: '44px 20px' }}>
                  <div className="spinner spinner--lg" style={{ margin: '0 auto 16px auto' }} />
                  <h3 style={{ marginBottom: '8px' }}>Calibrating Core Competencies</h3>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                    Standardizing vocational pillars for <strong>{calibratingTitle}</strong>...
                  </p>
                </div>
              ) : (
                <CareerCardGrid
                  candidates={candidates}
                  onSelect={handleCardSelect}
                  onNoneMatch={(target) => setPhase(target === 'not_found' ? 'not_found' : 'ai_form')}
                  onBack={() => {
                    setCandidates([]);
                    setPhase('input');
                  }}
                />
              ))}

            {phase === 'ai_form' && (
              <AIFallbackForm
                onResult={(result) => {
                  if (result.status === 'disambiguation_required') {
                    setCandidates(result.candidates);
                    setPhase('grid');
                  } else if (
                    result.status === 'generated' &&
                    result.related_candidates &&
                    result.related_candidates.length > 0
                  ) {
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

            {phase === 'assessment' && career && (
              <>
                <button
                  type="button"
                  id="onboarding-back-btn"
                  onClick={() => setShowLogoutToast(true)}
                  className="btn btn--ghost btn--xs"
                  style={{ marginBottom: '16px', border: 'none', paddingLeft: 0 }}
                >
                  <ArrowLeft size={14} />
                  <span>Change career target</span>
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

          <p style={{ textAlign: 'center', marginTop: '18px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Assessments are calibrated against O*NET and ESCO occupational standards.
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
          confirmDanger={phase !== 'assessment'}
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
    </div>
  );
}
