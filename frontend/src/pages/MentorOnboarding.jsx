// src/pages/MentorOnboarding.jsx
import { useState, useEffect } from 'react';
import { submitMentorOnboarding, fetchMentorSkills } from '../lib/api';
import Toast from '../components/Toast';

const PRIMARY_DOMAINS = [
  'Software Architecture & Full-Stack',
  'AI, Machine Learning & Data Science',
  'Cloud Infrastructure, DevOps & SRE',
  'Finance, Accounting & Quantitative Analysis',
  'Healthcare, Nursing & Clinical Practice',
  'Civil, Mechanical & Petroleum Engineering',
  'Culinary Arts, Hospitality & Skilled Trades',
  'Legal, Public Policy & Operations Management',
  'Creative Design, Media & Product Strategy',
];

const PRESET_CATEGORIES = [
  'Technical Skills',
  'Domain Knowledge',
  'Tools & Systems',
  'Interpersonal & Leadership',
];

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MentorOnboarding({ user, userProfile, onComplete }) {
  const [step, setStep] = useState(1); // 1 = Domain & Identity, 2 = Core Expertise, 3 = Schedule & Booking Settings
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);

  // Step 1: Identity & Primary Domain
  const [primaryDomain, setPrimaryDomain] = useState(
    PRIMARY_DOMAINS[0]
  );
  const [headline, setHeadline] = useState(
    userProfile?.headline || user?.user_metadata?.headline || ''
  );
  const [bio, setBio] = useState(
    userProfile?.bio || user?.user_metadata?.bio || ''
  );

  // Step 2: Expertise
  const [expertise, setExpertise] = useState([]); // Array of { skill_id, name, category }
  const [skillSearch, setSkillSearch] = useState('');
  const [availableSkills, setAvailableSkills] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [customSkillName, setCustomSkillName] = useState('');
  const [customCategory, setCustomCategory] = useState('Technical Skills');
  const [showCustomModal, setShowCustomModal] = useState(false);

  // Step 3: Schedule & Availability
  const [weeklyHours, setWeeklyHours] = useState(
    userProfile?.weekly_hours || 4
  );
  const [maxMentees, setMaxMentees] = useState(5);
  const [selectedDays, setSelectedDays] = useState(['Tue', 'Thu']);
  const [timeWindow, setTimeWindow] = useState('Evening'); // Morning, Afternoon, Evening

  const displayName =
    userProfile?.first_name ||
    user?.user_metadata?.first_name ||
    user?.user_metadata?.full_name ||
    (user?.email ? user.email.split('@')[0] : 'Mentor');

  // Debounced search for existing skills taxonomy
  useEffect(() => {
    let active = true;
    const timer = setTimeout(async () => {
      setSearchLoading(true);
      try {
        const res = await fetchMentorSkills(skillSearch, 25);
        if (active) {
          setAvailableSkills(res.skills || []);
        }
      } catch (err) {
        console.error('Skill search error:', err);
      } finally {
        if (active) setSearchLoading(false);
      }
    }, 250);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [skillSearch]);

  const toggleDay = (day) => {
    setSelectedDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day]
    );
  };

  const toggleSelectSkill = (skill) => {
    setExpertise((prev) => {
      const exists = prev.some((s) => s.id === skill.id || s.name.toLowerCase() === skill.name.toLowerCase());
      if (exists) {
        return prev.filter((s) => s.id !== skill.id && s.name.toLowerCase() !== skill.name.toLowerCase());
      }
      return [...prev, { skill_id: skill.id, name: skill.name, category: skill.category || 'Technical Skills' }];
    });
  };

  const handleAddCustomSkill = (e) => {
    e.preventDefault();
    const clean = customSkillName.trim();
    if (!clean) return;

    const exists = expertise.some((s) => s.name.toLowerCase() === clean.toLowerCase());
    if (exists) {
      setToastMessage(`"${clean}" is already in your selected expertise.`);
      return;
    }

    setExpertise((prev) => [
      ...prev,
      {
        skill_id: null,
        name: clean,
        category: customCategory,
      },
    ]);
    setCustomSkillName('');
    setShowCustomModal(false);
  };

  const removeExpertise = (name) => {
    setExpertise((prev) => prev.filter((s) => s.name.toLowerCase() !== name.toLowerCase()));
  };

  const handleSubmit = async () => {
    if (!headline.trim() || headline.length < 2) {
      setError('Please provide a professional headline.');
      setStep(1);
      return;
    }
    if (!bio.trim() || bio.length < 10) {
      setError('Please provide a mentor introduction bio (minimum 10 characters).');
      setStep(1);
      return;
    }
    if (expertise.length === 0) {
      setError('Please select at least 1 core skill or tool.');
      setStep(2);
      return;
    }
    if (selectedDays.length === 0) {
      setError('Please select at least one day per week for session availability.');
      setStep(3);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await submitMentorOnboarding({
        primary_domain: primaryDomain,
        headline: headline.trim(),
        bio: bio.trim(),
        weekly_hours: Number(weeklyHours) || 4,
        max_mentees: Number(maxMentees) || 5,
        available_days: selectedDays,
        preferred_time_window: timeWindow,
        expertise: expertise.map((s) => ({
          skill_id: s.skill_id,
          name: s.name,
          category: s.category,
        })),
      });

      onComplete();
    } catch (err) {
      setError(err.message || 'Failed to save mentor profile. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-center" style={{ minHeight: '100svh', padding: '40px 16px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      <div className="container" style={{ maxWidth: '720px', width: '100%' }}>
        {/* Logo Header */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '32px' }}>
          <div className="logo-mark">
            <div className="logo-mark__icon">CB</div>
            Career Beacon · Mentor Setup
          </div>
        </div>

        <div className="card" style={{ padding: '36px 32px' }}>
          {/* Step Indicator */}
          <div className="step-indicator">
            <div className={`step-dot ${step === 1 ? 'active' : step > 1 ? 'done' : ''}`} />
            <div className={`step-dot ${step === 2 ? 'active' : step > 2 ? 'done' : ''}`} />
            <div className={`step-dot ${step === 3 ? 'active' : ''}`} />
          </div>

          <p style={{ color: 'var(--teal)', fontSize: '0.9rem', fontWeight: 600, marginBottom: '6px' }}>
            Welcome, {displayName}! 🎓
          </p>

          {/* STEP 1: Primary Domain, Headline & Bio */}
          {step === 1 && (
            <div>
              <h2 style={{ marginBottom: '8px' }}>
                Primary Domain & <span className="gradient-text">Mentor Identity</span>
              </h2>
              <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                Establish your primary coaching area and introduce your experience to future mentees.
              </p>

              <div className="form-group">
                <label htmlFor="primary-domain">Primary Technical Domain</label>
                <select
                  id="primary-domain"
                  value={primaryDomain}
                  onChange={(e) => setPrimaryDomain(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    padding: '10px 12px',
                    fontSize: '0.9rem',
                  }}
                >
                  {PRIMARY_DOMAINS.map((domain) => (
                    <option key={domain} value={domain}>
                      {domain}
                    </option>
                  ))}
                </select>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Used for high-precision coarse filtering across mentee recommendation feeds.
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="mentor-headline">Professional Headline</label>
                <input
                  id="mentor-headline"
                  type="text"
                  placeholder="e.g. Senior Staff Backend Engineer at TechCorp | Distributed Systems Specialist"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>

              <div className="form-group">
                <label htmlFor="mentor-bio">Introduction & Mentorship Bio</label>
                <textarea
                  id="mentor-bio"
                  rows={4}
                  placeholder="Share your background, typical guidance topics (e.g. code reviews, career navigation, architecture design), and coaching philosophy."
                  value={bio}
                  onChange={(e) => setBio(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    padding: '10px 12px',
                    fontSize: '0.9rem',
                    fontFamily: 'inherit',
                  }}
                />
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right', marginTop: '4px' }}>
                  {bio.length} characters (min 10)
                </div>
              </div>

              <button
                type="button"
                className="btn btn--primary btn--full"
                onClick={() => {
                  if (!headline.trim() || bio.trim().length < 10) {
                    setError('Please provide both your headline and an introduction bio (min 10 characters).');
                    return;
                  }
                  setError(null);
                  setStep(2);
                }}
              >
                Next: Select Core Skills & Tools →
              </button>
            </div>
          )}

          {/* STEP 2: Expertise & Skills */}
          {step === 2 && (
            <div>
              <h2 style={{ marginBottom: '8px' }}>
                Technical <span className="gradient-text">Skills & Stack</span>
              </h2>
              <p style={{ marginBottom: '20px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                Select the languages, frameworks, and specialized concepts in which you offer guidance.
              </p>

              {/* Selected Skill Chips */}
              <div style={{ marginBottom: '18px' }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px' }}>
                  SELECTED SKILLS ({expertise.length}):
                </div>
                {expertise.length === 0 ? (
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    No skills selected yet. Select from taxonomy below or add custom stack.
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {expertise.map((sk) => (
                      <span
                        key={sk.name}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '4px 10px',
                          borderRadius: '20px',
                          fontSize: '0.82rem',
                          background: 'hsla(174, 72%, 56%, 0.15)',
                          color: 'var(--teal)',
                          border: '1px solid hsla(174, 72%, 56%, 0.3)',
                        }}
                      >
                        {sk.name}
                        <button
                          type="button"
                          onClick={() => removeExpertise(sk.name)}
                          style={{
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-muted)',
                            cursor: 'pointer',
                            fontSize: '0.85rem',
                            padding: 0,
                          }}
                        >
                          ✕
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Taxonomy Search */}
              <div className="form-group" style={{ marginBottom: '12px' }}>
                <label htmlFor="skill-search">Search Knowledge Taxonomy</label>
                <input
                  id="skill-search"
                  type="text"
                  placeholder="e.g. Python, Docker, PostgreSQL, React, System Design…"
                  value={skillSearch}
                  onChange={(e) => setSkillSearch(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Suggestions */}
              <div
                style={{
                  maxHeight: '170px',
                  overflowY: 'auto',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  padding: '8px',
                  background: 'var(--bg-elevated)',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '6px',
                  marginBottom: '16px',
                }}
              >
                {searchLoading ? (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '8px' }}>
                    Searching taxonomy…
                  </div>
                ) : availableSkills.length === 0 ? (
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '8px' }}>
                    No exact taxonomy match found. Click "+ Add Custom Stack" below.
                  </div>
                ) : (
                  availableSkills.map((sk) => {
                    const isSelected = expertise.some(
                      (e) => e.name.toLowerCase() === sk.name.toLowerCase()
                    );
                    return (
                      <button
                        key={sk.id}
                        type="button"
                        onClick={() => toggleSelectSkill(sk)}
                        style={{
                          padding: '4px 10px',
                          borderRadius: 'var(--r-sm)',
                          fontSize: '0.8rem',
                          cursor: 'pointer',
                          border: '1px solid',
                          borderColor: isSelected ? 'var(--teal)' : 'var(--border)',
                          background: isSelected ? 'hsla(174, 72%, 56%, 0.2)' : 'var(--bg-surface)',
                          color: isSelected ? 'var(--teal)' : 'var(--text-primary)',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {isSelected ? '✓ ' : '+ '}
                        {sk.name}
                      </button>
                    );
                  })
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '20px' }}>
                <button
                  type="button"
                  className="btn btn--ghost btn--sm"
                  onClick={() => setShowCustomModal(true)}
                  style={{ borderStyle: 'dashed' }}
                >
                  + Add Custom Stack or Tool
                </button>
              </div>

              {/* Custom Skill Modal */}
              {showCustomModal && (
                <div
                  style={{
                    padding: '14px',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--accent-border)',
                    borderRadius: 'var(--r-md)',
                    marginBottom: '20px',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '8px' }}>
                    Add Custom Competency:
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
                    <input
                      type="text"
                      placeholder="e.g. LangChain, Kubernetes, GraphQL..."
                      value={customSkillName}
                      onChange={(e) => setCustomSkillName(e.target.value)}
                      style={{ flex: 1, minWidth: '160px' }}
                      autoFocus
                    />
                    <select
                      value={customCategory}
                      onChange={(e) => setCustomCategory(e.target.value)}
                      style={{
                        background: 'var(--bg-input)',
                        color: 'var(--text-primary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--r-md)',
                        padding: '8px 12px',
                        fontSize: '0.85rem',
                      }}
                    >
                      {PRESET_CATEGORIES.map((c) => (
                        <option key={c} value={c}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      onClick={() => setShowCustomModal(false)}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="btn btn--primary btn--sm"
                      onClick={handleAddCustomSkill}
                      disabled={!customSkillName.trim()}
                    >
                      Add Skill
                    </button>
                  </div>
                </div>
              )}

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setStep(1)}
                  style={{ flex: 1 }}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => {
                    if (expertise.length === 0) {
                      setError('Please select at least 1 skill or tool.');
                      return;
                    }
                    setError(null);
                    setStep(3);
                  }}
                  style={{ flex: 2 }}
                >
                  Next: Availability Windows →
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: Availability & Dynamic Calendar Integration */}
          {step === 3 && (
            <div>
              <h2 style={{ marginBottom: '8px' }}>
                Availability & <span className="gradient-text">Scheduling Preferences</span>
              </h2>
              <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                Set your standard mentoring windows. Dynamic calendar invitations and one-off secure session links are automatically generated upon confirmed booking.
              </p>

              {/* Days of Week selector */}
              <div className="form-group">
                <label>Available Days of the Week</label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                  {DAYS_OF_WEEK.map((day) => {
                    const isSelected = selectedDays.includes(day);
                    return (
                      <button
                        key={day}
                        type="button"
                        onClick={() => toggleDay(day)}
                        style={{
                          padding: '8px 14px',
                          borderRadius: 'var(--r-md)',
                          fontSize: '0.85rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          border: '1px solid',
                          borderColor: isSelected ? 'var(--teal)' : 'var(--border)',
                          background: isSelected ? 'hsla(174, 72%, 56%, 0.2)' : 'var(--bg-surface)',
                          color: isSelected ? 'var(--teal)' : 'var(--text-secondary)',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        {day}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Time Window Preference */}
              <div className="form-group">
                <label htmlFor="time-window">Preferred Timeframe Window</label>
                <select
                  id="time-window"
                  value={timeWindow}
                  onChange={(e) => setTimeWindow(e.target.value)}
                  style={{
                    width: '100%',
                    background: 'var(--bg-input)',
                    color: 'var(--text-primary)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    padding: '10px 12px',
                    fontSize: '0.9rem',
                  }}
                >
                  <option value="Morning">Morning (08:00 – 12:00 Local)</option>
                  <option value="Afternoon">Afternoon (13:00 – 17:00 Local)</option>
                  <option value="Evening">Evening (18:00 – 21:00 Local)</option>
                  <option value="Flexible">Flexible / By Appointment</option>
                </select>
              </div>

              {/* Weekly Hours Slider */}
              <div className="form-group">
                <label htmlFor="mentor-hours">Estimated Weekly Availability</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <input
                    id="mentor-hours"
                    type="range"
                    min="1"
                    max="20"
                    value={weeklyHours}
                    onChange={(e) => setWeeklyHours(e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: '1rem',
                      color: 'var(--teal)',
                      minWidth: '60px',
                      textAlign: 'right',
                    }}
                  >
                    {weeklyHours} hrs/wk
                  </span>
                </div>
              </div>

              {/* Max Mentees Capacity Slider */}
              <div className="form-group">
                <label htmlFor="mentor-capacity">Maximum Active Mentees (Capacity Gate)</label>
                <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                  <input
                    id="mentor-capacity"
                    type="range"
                    min="1"
                    max="15"
                    value={maxMentees}
                    onChange={(e) => setMaxMentees(e.target.value)}
                    style={{ flex: 1 }}
                  />
                  <span
                    style={{
                      fontWeight: 700,
                      fontSize: '1rem',
                      color: 'var(--accent-light)',
                      minWidth: '90px',
                      textAlign: 'right',
                    }}
                  >
                    {maxMentees} mentees
                  </span>
                </div>
              </div>

              {/* Dynamic Session Note */}
              <div
                style={{
                  padding: '12px 14px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--r-md)',
                  fontSize: '0.82rem',
                  color: 'var(--text-secondary)',
                  marginBottom: '20px',
                }}
              >
                📅 <strong>Dynamic Calendar Invites:</strong> When a mentee books an appointment, our scheduling engine validates against your availability, confirms no double-booking, and sends mutual calendar invites with auto-generated session links.
              </div>

              {error && (
                <div className="alert alert--error" style={{ marginBottom: '16px' }}>
                  {error}
                </div>
              )}

              <div style={{ display: 'flex', gap: '12px' }}>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setStep(2)}
                  style={{ flex: 1 }}
                >
                  ← Back
                </button>
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={handleSubmit}
                  disabled={loading}
                  style={{ flex: 2 }}
                >
                  {loading ? (
                    <>
                      <span className="spinner" />
                      Initializing Mentor Profile…
                    </>
                  ) : (
                    'Complete Mentor Onboarding 🎉'
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        <p style={{ textAlign: 'center', marginTop: '20px', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          Mentors earn organic trust scores based on verified mentee reviews and knowledge contributions.
        </p>
      </div>

      {toastMessage && (
        <Toast
          message={toastMessage}
          onConfirm={() => setToastMessage(null)}
          confirmLabel="OK"
        />
      )}
    </div>
  );
}
