// src/pages/MentorOnboarding.jsx
import { useState, useEffect } from 'react';
import { supabase } from '../lib/SupabaseClient';
import {
  submitMentorOnboarding,
  fetchMentorSkills,
  searchMentorCareers,
  getCareerById,
} from '../lib/api';
import Toast from '../components/Toast';
import ThemeSelector from '../components/ThemeSelector';
import {
  Compass,
  Check,
  Plus,
  X,
  ArrowLeft,
  ArrowRight,
  Calendar,
  Search,
  Sparkles,
  LogOut,
} from '../components/Icons';

const PRESET_CATEGORIES = [
  'Technical Skills',
  'Domain Knowledge',
  'Tools & Systems',
  'Interpersonal & Leadership',
];

const DAYS_OF_WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MentorOnboarding({ user, userProfile, onComplete }) {
  const [step, setStep] = useState(1); // 1 = Role & Identity, 2 = Core Expertise, 3 = Schedule & Booking Settings
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [showLogoutToast, setShowLogoutToast] = useState(false);

  const handleLogout = async () => {
    await supabase.auth.signOut();
  };

  // Step 1: Career Discipline & Identity
  const [careerQuery, setCareerQuery] = useState('');
  const [careerSearchResults, setCareerSearchResults] = useState({ direct_matches: [], vector_matches: [] });
  const [searchingCareers, setSearchingCareers] = useState(false);
  const [selectedCareer, setSelectedCareer] = useState(null);
  const [careerNormalizedSkills, setCareerNormalizedSkills] = useState([]);
  const [loadingCareerSkills, setLoadingCareerSkills] = useState(false);

  const [headline, setHeadline] = useState(
    userProfile?.headline || user?.user_metadata?.headline || ''
  );
  const [bio, setBio] = useState(
    userProfile?.bio || user?.user_metadata?.bio || ''
  );

  // Step 2: Expertise
  const [expertise, setExpertise] = useState([]);
  const [skillSearch, setSkillSearch] = useState('');
  const [availableSkills, setAvailableSkills] = useState([]);
  const [searchLoading, setSearchLoading] = useState(false);
  const [customSkillName, setCustomSkillName] = useState('');
  const [customCategory, setCustomCategory] = useState('Technical Skills');
  const [showCustomModal, setShowCustomModal] = useState(false);

  // Debounced Career Search (Direct keyword + Vector semantic matching)
  useEffect(() => {
    if (!careerQuery.trim() || careerQuery.trim().length < 2) {
      setCareerSearchResults({ direct_matches: [], vector_matches: [] });
      return;
    }
    let active = true;
    const timer = setTimeout(async () => {
      setSearchingCareers(true);
      try {
        const res = await searchMentorCareers(careerQuery);
        if (active) {
          setCareerSearchResults(res || { direct_matches: [], vector_matches: [] });
        }
      } catch (err) {
        console.error('Mentor career search error:', err);
      } finally {
        if (active) setSearchingCareers(false);
      }
    }, 250);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [careerQuery]);

  const handleSelectCareer = async (c) => {
    setSelectedCareer(c);
    setCareerQuery(c.title);
    setCareerSearchResults({ direct_matches: [], vector_matches: [] });
    setLoadingCareerSkills(true);
    try {
      const res = await getCareerById(c.id);
      const skills = res.skills || [];
      // Clean normalized skills: essential vocational competencies from DB
      const essential = skills.filter((s) => s.importance === 'essential' || s.source_origin === 'llm');
      const cleanList = essential.length > 0 ? essential : skills.slice(0, 10);
      setCareerNormalizedSkills(cleanList);
    } catch (err) {
      console.error('Error fetching career skills:', err);
    } finally {
      setLoadingCareerSkills(false);
    }
  };

  // Step 3: Schedule & Availability
  const [weeklyHours, setWeeklyHours] = useState(userProfile?.weekly_hours || 4);
  const [maxMentees, setMaxMentees] = useState(5);
  const [selectedDays, setSelectedDays] = useState(['Tue', 'Thu']);
  const [timeWindow, setTimeWindow] = useState('Evening');

  const displayName =
    userProfile?.first_name ||
    user?.user_metadata?.first_name ||
    user?.user_metadata?.full_name ||
    (user?.email ? user.email.split('@')[0] : 'Mentor');

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
      const exists = prev.some(
        (s) => (s.id && skill.id && s.id === skill.id) || s.name.toLowerCase() === skill.name.toLowerCase()
      );
      if (exists) {
        return prev.filter(
          (s) => s.name.toLowerCase() !== skill.name.toLowerCase()
        );
      }
      return [
        ...prev,
        { skill_id: skill.id || skill.skill_id || null, name: skill.name, category: skill.category || 'Technical Skills' },
      ];
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
    if (!selectedCareer) {
      setError('Please select an occupational discipline or role from the catalog search.');
      setStep(1);
      return;
    }
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
        primary_domain: selectedCareer.title,
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
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            {step > 1 && (
              <button
                type="button"
                onClick={() => setStep((s) => Math.max(1, s - 1))}
                className="btn btn--ghost btn--sm"
                title="Go back to previous step"
                style={{ padding: '6px 10px', gap: '6px' }}
              >
                <ArrowLeft size={15} />
                <span>Back</span>
              </button>
            )}
            <div className="logo-mark">
              <div className="logo-mark__icon">
                <Compass size={18} />
              </div>
              <span>Career Beacon · Mentor Setup</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              id="mentor-header-logout-btn"
              type="button"
              onClick={() => setShowLogoutToast(true)}
              className="btn btn--ghost btn--sm"
              style={{ color: 'var(--text-secondary)' }}
            >
              <LogOut size={15} />
              <span>Sign out</span>
            </button>
            <ThemeSelector />
          </div>
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
        <div className="container" style={{ maxWidth: '720px', width: '100%' }}>
          <div className="card" style={{ padding: '36px 32px' }}>
            {/* Step Indicator */}
            <div className="step-indicator">
              <div className={`step-dot ${step === 1 ? 'active' : step > 1 ? 'done' : ''}`} />
              <div className={`step-dot ${step === 2 ? 'active' : step > 2 ? 'done' : ''}`} />
              <div className={`step-dot ${step === 3 ? 'active' : ''}`} />
            </div>

            <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '6px' }}>
              Welcome, {displayName}
            </div>

            {/* STEP 1: Career Discipline, Headline & Bio */}
            {step === 1 && (
              <div>
                <h2 style={{ marginBottom: '8px' }}>Occupational Discipline &amp; Mentor Identity</h2>
                <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                  Select the career discipline you coach in and introduce your professional background to prospective mentees.
                </p>

                <div className="form-group" style={{ position: 'relative' }}>
                  <label htmlFor="mentor-career-search">Occupational Discipline / Role You Mentor</label>
                  <div style={{ position: 'relative' }}>
                    <Search
                      size={16}
                      color="var(--text-muted)"
                      style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
                    />
                    <input
                      id="mentor-career-search"
                      type="text"
                      placeholder="Type a career role e.g. Data Scientist, Software Developer, Nurse, Accountant..."
                      value={careerQuery}
                      onChange={(e) => {
                        setCareerQuery(e.target.value);
                        if (selectedCareer && e.target.value !== selectedCareer.title) {
                          setSelectedCareer(null);
                          setCareerNormalizedSkills([]);
                        }
                      }}
                      style={{ paddingLeft: '36px' }}
                      autoComplete="off"
                    />
                    {searchingCareers && (
                      <span className="spinner spinner--sm" style={{ position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)' }} />
                    )}
                  </div>

                  {/* Dual Dropdown: Exact Keyword Matches + Semantic Vector Matches */}
                  {!selectedCareer && (careerSearchResults.direct_matches?.length > 0 || careerSearchResults.vector_matches?.length > 0) && (
                    <div
                      style={{
                        position: 'absolute',
                        zIndex: 100,
                        width: '100%',
                        maxHeight: '260px',
                        overflowY: 'auto',
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--r-md)',
                        boxShadow: 'var(--shadow-lg)',
                        marginTop: '4px',
                        padding: '6px',
                      }}
                    >
                      {careerSearchResults.direct_matches?.length > 0 && (
                        <div style={{ marginBottom: '8px' }}>
                          <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', padding: '4px 8px' }}>
                            Exact Catalog Matches
                          </div>
                          {careerSearchResults.direct_matches.map((c) => (
                            <button
                              key={c.id}
                              type="button"
                              onClick={() => handleSelectCareer(c)}
                              style={{
                                width: '100%',
                                textAlign: 'left',
                                padding: '8px 10px',
                                borderRadius: 'var(--r-sm)',
                                border: 'none',
                                background: 'none',
                                cursor: 'pointer',
                                display: 'flex',
                                flexDirection: 'column',
                              }}
                              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-elevated)')}
                              onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                            >
                              <span style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{c.title}</span>
                              {c.description && (
                                <span style={{ fontSize: '0.76rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                  {c.description}
                                </span>
                              )}
                            </button>
                          ))}
                        </div>
                      )}

                      {careerSearchResults.vector_matches?.length > 0 && (
                        <div>
                          <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent)', padding: '4px 8px' }}>
                            Related Pathways (Semantic Search)
                          </div>
                          {careerSearchResults.vector_matches.map((c) => (
                            <button
                              key={c.id}
                              type="button"
                              onClick={() => handleSelectCareer(c)}
                              style={{
                                width: '100%',
                                textAlign: 'left',
                                padding: '8px 10px',
                                borderRadius: 'var(--r-sm)',
                                border: 'none',
                                background: 'none',
                                cursor: 'pointer',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--surface-elevated)')}
                              onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
                            >
                              <div>
                                <div style={{ fontWeight: 600, fontSize: '0.88rem', color: 'var(--text-primary)' }}>{c.title}</div>
                                {c.description && (
                                  <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {c.description}
                                  </div>
                                )}
                              </div>
                              <span className="badge badge--neutral" style={{ fontSize: '0.7rem' }}>
                                {Math.round((c.similarity || 0.8) * 100)}% match
                              </span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {selectedCareer && (
                    <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="badge badge--accent" style={{ fontSize: '0.8rem', padding: '4px 10px' }}>
                        Selected: {selectedCareer.title}
                      </span>
                      <button
                        type="button"
                        className="btn btn--ghost btn--xs"
                        onClick={() => {
                          setSelectedCareer(null);
                          setCareerNormalizedSkills([]);
                        }}
                      >
                        Change
                      </button>
                    </div>
                  )}
                  <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Selects your target occupation from the database to load normalized vocational competencies in Step 2.
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="mentor-headline">Professional Headline</label>
                  <input
                    id="mentor-headline"
                    type="text"
                    placeholder="e.g. Senior Staff Backend Engineer at TechCorp | Distributed Systems"
                    value={headline}
                    onChange={(e) => setHeadline(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label htmlFor="mentor-bio">Introduction &amp; Mentorship Bio</label>
                  <textarea
                    id="mentor-bio"
                    rows={4}
                    placeholder="Share your background, typical guidance topics (architecture design, career navigation, clinical practice), and coaching approach."
                    value={bio}
                    onChange={(e) => setBio(e.target.value)}
                  />
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', textAlign: 'right', marginTop: '4px' }}>
                    {bio.length} characters (min 10)
                  </div>
                </div>

                {error && (
                  <div className="alert alert--error" style={{ marginBottom: '16px' }}>
                    {error}
                  </div>
                )}

                <button
                  type="button"
                  className="btn btn--primary btn--full"
                  onClick={() => {
                    if (!selectedCareer) {
                      setError('Please search and select an occupational discipline or role from the catalog.');
                      return;
                    }
                    if (!headline.trim() || bio.trim().length < 10) {
                      setError('Please provide both your headline and an introduction bio (min 10 characters).');
                      return;
                    }
                    setError(null);
                    setStep(2);
                  }}
                >
                  <span>Next: Select Core Skills &amp; Tools</span>
                  <ArrowRight size={16} />
                </button>

                <div style={{ textAlign: 'center', marginTop: '24px' }}>
                  <button
                    id="mentor-step1-logout-btn"
                    type="button"
                    onClick={() => setShowLogoutToast(true)}
                    className="btn btn--ghost btn--xs"
                    style={{ border: 'none', color: 'var(--text-muted)' }}
                  >
                    <LogOut size={13} />
                    <span>Sign out</span>
                  </button>
                </div>
              </div>
            )}

            {/* STEP 2: Expertise & Skills */}
            {step === 2 && (
              <div>
                <h2 style={{ marginBottom: '8px' }}>Core Competencies &amp; Stack</h2>
                <p style={{ marginBottom: '20px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                  Select the competencies, tools, and specialized subjects in which you offer verified guidance.
                </p>

                {/* Selected Skill Chips */}
                <div style={{ marginBottom: '18px' }}>
                  <div
                    style={{
                      fontSize: '0.76rem',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em',
                      color: 'var(--text-muted)',
                      marginBottom: '8px',
                    }}
                  >
                    Selected Expertise ({expertise.length})
                  </div>
                  {expertise.length === 0 ? (
                    <div
                      style={{
                        padding: '12px 14px',
                        borderRadius: 'var(--r-md)',
                        background: 'var(--surface-elevated)',
                        border: '1px dashed var(--border)',
                        fontSize: '0.84rem',
                        color: 'var(--text-muted)',
                      }}
                    >
                      No skills selected yet. Choose from the taxonomy below or add a custom competency.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {expertise.map((sk) => (
                        <span
                          key={sk.name}
                          className="badge badge--accent"
                          style={{ padding: '5px 10px', fontSize: '0.8rem' }}
                        >
                          <span>{sk.name}</span>
                          <button
                            type="button"
                            aria-label={`Remove ${sk.name}`}
                            onClick={() => removeExpertise(sk.name)}
                            style={{
                              background: 'none',
                              border: 'none',
                              color: 'currentColor',
                              cursor: 'pointer',
                              display: 'inline-flex',
                              padding: 0,
                            }}
                          >
                            <X size={13} />
                          </button>
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                {/* Database-Grounded Clean Normalized Vocational Competencies */}
                {loadingCareerSkills ? (
                  <div style={{ padding: '14px', background: 'var(--surface-elevated)', borderRadius: 'var(--r-md)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                    <span className="spinner spinner--sm" />
                    <span>Loading database-grounded competencies for {selectedCareer?.title}...</span>
                  </div>
                ) : careerNormalizedSkills.length > 0 && (
                  <div style={{ marginBottom: '20px' }}>
                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        marginBottom: '8px',
                      }}
                    >
                      <div
                        style={{
                          fontSize: '0.76rem',
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          letterSpacing: '0.05em',
                          color: 'var(--accent)',
                        }}
                      >
                        Normalized Vocational Competencies ({selectedCareer?.title})
                      </div>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        1-tap verify
                      </span>
                    </div>

                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                      {careerNormalizedSkills.map((preset) => {
                        const isSelected = expertise.some(
                          (e) => e.name.toLowerCase() === preset.name.toLowerCase()
                        );
                        return (
                          <button
                            key={preset.name}
                            type="button"
                            onClick={() => toggleSelectSkill(preset)}
                            style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: '6px',
                              padding: '5px 11px',
                              borderRadius: 'var(--r-full)',
                              fontSize: '0.8rem',
                              fontWeight: isSelected ? 600 : 500,
                              cursor: 'pointer',
                              border: '1px solid',
                              borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
                              background: isSelected ? 'var(--accent-soft)' : 'var(--surface-elevated)',
                              color: isSelected ? 'var(--accent-light)' : 'var(--text-primary)',
                              transition: 'all 0.15s ease',
                            }}
                          >
                            {isSelected ? <Check size={13} color="var(--accent)" /> : <Plus size={13} />}
                            <span>{preset.name}</span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Taxonomy Search */}
                <div className="form-group" style={{ marginBottom: '12px' }}>
                  <label htmlFor="skill-search">Search Knowledge Taxonomy</label>
                  <div style={{ position: 'relative' }}>
                    <Search
                      size={16}
                      color="var(--text-muted)"
                      style={{
                        position: 'absolute',
                        left: '12px',
                        top: '50%',
                        transform: 'translateY(-50%)',
                        pointerEvents: 'none',
                      }}
                    />
                    <input
                      id="skill-search"
                      type="text"
                      placeholder="e.g. Python, Docker, PostgreSQL, Financial Modeling, System Design..."
                      value={skillSearch}
                      onChange={(e) => setSkillSearch(e.target.value)}
                      style={{ paddingLeft: '36px' }}
                    />
                  </div>
                </div>

                {/* Suggestions */}
                <div
                  style={{
                    maxHeight: '180px',
                    overflowY: 'auto',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    padding: '10px',
                    background: 'var(--surface-elevated)',
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: '6px',
                    marginBottom: '16px',
                  }}
                >
                  {searchLoading ? (
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '6px' }}>
                      Searching taxonomy...
                    </div>
                  ) : availableSkills.length === 0 ? (
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', padding: '6px' }}>
                      No exact taxonomy match found. Use &ldquo;Add Custom Competency&rdquo; below.
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
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '5px 10px',
                            borderRadius: 'var(--r-sm)',
                            fontSize: '0.8rem',
                            fontWeight: isSelected ? 600 : 500,
                            cursor: 'pointer',
                            border: '1px solid',
                            borderColor: isSelected ? 'var(--accent-border)' : 'var(--border)',
                            background: isSelected ? 'var(--accent-soft)' : 'var(--surface)',
                            color: isSelected ? 'var(--accent-light)' : 'var(--text-primary)',
                          }}
                        >
                          {isSelected ? <Check size={13} /> : <Plus size={13} />}
                          <span>{sk.name}</span>
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
                    <Plus size={14} />
                    <span>Add Custom Competency or Tool</span>
                  </button>
                </div>

                {showCustomModal && (
                  <div
                    style={{
                      padding: '16px',
                      background: 'var(--surface-elevated)',
                      border: '1px solid var(--accent-border)',
                      borderRadius: 'var(--r-md)',
                      marginBottom: '20px',
                    }}
                  >
                    <div style={{ fontWeight: 600, fontSize: '0.85rem', marginBottom: '10px' }}>
                      Add Custom Competency
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}>
                      <input
                        type="text"
                        placeholder="e.g. LangChain, Kubernetes, OpenTelemetry..."
                        value={customSkillName}
                        onChange={(e) => setCustomSkillName(e.target.value)}
                        style={{ flex: 1, minWidth: '180px' }}
                        autoFocus
                      />
                      <select
                        value={customCategory}
                        onChange={(e) => setCustomCategory(e.target.value)}
                        style={{ width: 'auto', minWidth: '180px' }}
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

                {error && (
                  <div className="alert alert--error" style={{ marginBottom: '16px' }}>
                    {error}
                  </div>
                )}

                <div style={{ display: 'flex', gap: '12px' }}>
                  <button
                    type="button"
                    className="btn btn--ghost"
                    onClick={() => setStep(1)}
                    style={{ flex: 1 }}
                  >
                    <ArrowLeft size={15} />
                    <span>Back</span>
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
                    <span>Next: Availability Windows</span>
                    <ArrowRight size={15} />
                  </button>
                </div>
              </div>
            )}

            {/* STEP 3: Availability & Dynamic Calendar Integration */}
            {step === 3 && (
              <div>
                <h2 style={{ marginBottom: '8px' }}>Availability &amp; Scheduling Preferences</h2>
                <p style={{ marginBottom: '24px', fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                  Configure your standard weekly mentoring windows. Calendar invitations and conference rooms are generated automatically when a connected mentee books a slot.
                </p>

                <div className="form-group">
                  <label>Available Days of the Week</label>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '4px' }}>
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
                            fontSize: '0.84rem',
                            fontWeight: 600,
                            cursor: 'pointer',
                            border: '1px solid',
                            borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
                            background: isSelected ? 'var(--accent-soft)' : 'var(--surface)',
                            color: isSelected ? 'var(--accent-light)' : 'var(--text-secondary)',
                          }}
                        >
                          {day}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div className="form-group">
                  <label htmlFor="time-window">Preferred Timeframe Window</label>
                  <select
                    id="time-window"
                    value={timeWindow}
                    onChange={(e) => setTimeWindow(e.target.value)}
                  >
                    <option value="Morning">Morning (08:00 – 12:00 Local)</option>
                    <option value="Afternoon">Afternoon (13:00 – 17:00 Local)</option>
                    <option value="Evening">Evening (18:00 – 21:00 Local)</option>
                    <option value="Flexible">Flexible / By Appointment</option>
                  </select>
                </div>

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
                      className="mono"
                      style={{
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        color: 'var(--accent)',
                        minWidth: '72px',
                        textAlign: 'right',
                      }}
                    >
                      {weeklyHours} hrs/wk
                    </span>
                  </div>
                </div>

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
                      className="mono"
                      style={{
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        color: 'var(--text-primary)',
                        minWidth: '90px',
                        textAlign: 'right',
                      }}
                    >
                      {maxMentees} mentees
                    </span>
                  </div>
                </div>

                <div
                  style={{
                    padding: '14px 16px',
                    background: 'var(--surface-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    fontSize: '0.83rem',
                    color: 'var(--text-secondary)',
                    marginBottom: '20px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px',
                  }}
                >
                  <Calendar size={17} color="var(--accent)" style={{ marginTop: '2px' }} />
                  <div>
                    <strong style={{ color: 'var(--text-primary)' }}>Dynamic Calendar Protection:</strong> Booked 45-minute slots lock automatically across both calendars and include Google Calendar links plus downloadable <code>.ics</code> reminders.
                  </div>
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
                    <ArrowLeft size={15} />
                    <span>Back</span>
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
                        <span>Initializing Mentor Workspace...</span>
                      </>
                    ) : (
                      <>
                        <span>Complete Mentor Onboarding</span>
                        <Check size={16} />
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {toastMessage && (
        <Toast
          message={toastMessage}
          onConfirm={() => setToastMessage(null)}
          confirmLabel="OK"
        />
      )}

      {showLogoutToast && (
        <Toast
          message="Are you sure you want to sign out?"
          onConfirm={handleLogout}
          onCancel={() => setShowLogoutToast(false)}
          confirmLabel="Yes, sign out"
          cancelLabel="Cancel"
          confirmDanger
        />
      )}
    </div>
  );
}
