// src/pages/Recommendations.jsx
import { useState, useEffect } from 'react';
import { getRecommendations, recordContentOpen, submitQuiz } from '../lib/api';

export default function Recommendations({ user, career, onSkillUpdated, onNavigateToGraph }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [activeQuizLesson, setActiveQuizLesson] = useState(null); // Lesson object when quiz is open
  const [quizAnswers, setQuizAnswers] = useState({}); // { [questionIdx]: selectedOption }
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [quizResult, setQuizResult] = useState(null); // Result returned from backend
  const [passedLessons, setPassedLessons] = useState(new Set());

  // Fetch recommendations on mount
  useEffect(() => {
    let isMounted = true;

    async function fetchFeed() {
      if (!user?.id) return;
      setLoading(true);
      setError(null);
      try {
        const res = await getRecommendations(user.id, 5);
        if (isMounted) {
          setRecommendations(res.recommendations || []);
        }
      } catch (err) {
        if (isMounted) {
          console.error('Failed to load recommendations:', err);
          setError(err.message || 'Could not load recommendations');
        }
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchFeed();
    return () => { isMounted = false; };
  }, [user?.id]);

  // Open Quiz Modal / Drawer
  const handleStartQuiz = (lesson) => {
    setActiveQuizLesson(lesson);
    setQuizAnswers({});
    setQuizResult(null);
  };

  // Select an option for a question
  const handleSelectOption = (qIdx, option) => {
    if (quizResult) return; // Prevent edits after submission
    setQuizAnswers((prev) => ({
      ...prev,
      [qIdx]: option,
    }));
  };

  // Submit Quiz to Backend
  const handleSubmitQuiz = async () => {
    if (!activeQuizLesson || submittingQuiz) return;
    setSubmittingQuiz(true);
    try {
      const res = await submitQuiz(user.id, activeQuizLesson.id, quizAnswers);
      setQuizResult(res);

      if (res.passed) {
        setPassedLessons((prev) => new Set([...prev, activeQuizLesson.id]));
        // Inform parent App state to update skill graph
        if (onSkillUpdated && activeQuizLesson.associated_skill_id && res.new_proficiency != null) {
          onSkillUpdated({
            skillId: activeQuizLesson.associated_skill_id,
            newProficiency: res.new_proficiency,
            skillMastered: res.skill_mastered,
          });
        }
        const refreshed = await getRecommendations(user.id, 5);
        setRecommendations(refreshed.recommendations || []);
      }
    } catch (err) {
      alert(`Quiz submission error: ${err.message}`);
    } finally {
      setSubmittingQuiz(false);
    }
  };

  // Helper for difficulty label & color
  const getDifficultyMeta = (level) => {
    switch (level) {
      case 1: return { label: 'Level 1: Beginner', color: 'hsl(142, 70%, 50%)' };
      case 2: return { label: 'Level 2: Elementary', color: 'hsl(174, 72%, 56%)' };
      case 3: return { label: 'Level 3: Intermediate', color: 'hsl(38, 92%, 55%)' };
      case 4: return { label: 'Level 4: Advanced', color: 'hsl(280, 85%, 65%)' };
      case 5: return { label: 'Level 5: Expert', color: 'hsl(0, 80%, 60%)' };
      default: return { label: `Level ${level}`, color: 'var(--accent-light)' };
    }
  };

  return (
    <div style={{ maxWidth: '860px', margin: '0 auto', textAlign: 'left' }}>
      {/* Feed Hero Header */}
      <div
        className="card"
        style={{
          marginBottom: '28px',
          background: 'linear-gradient(135deg, hsla(258,90%,66%,0.08) 0%, hsla(174,72%,56%,0.05) 100%), var(--bg-surface)',
          borderColor: 'var(--accent-border)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
              <span className="badge badge--accent" style={{ fontSize: '0.75rem', letterSpacing: '0.04em' }}>
                STAGE 2 HYBRID RANKED
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Target: <strong style={{ color: 'var(--text-primary)' }}>{career?.title || 'Selected Path'}</strong>
              </span>
            </div>
            <h2 style={{ fontSize: '1.6rem', marginBottom: '8px' }}>
              Your Personalized <span className="gradient-text">Learning Frontier</span>
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', maxWidth: '560px' }}>
              Micro-lessons tailored to your biggest skill gaps. Each lesson is atomized into 3 core takeaways and an interactive 5-question checkpoint (+10% skill progress upon passing).
            </p>
          </div>

          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={onNavigateToGraph}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            ← View Skill Graph
          </button>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          className="card"
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '64px 20px',
            gap: '16px',
          }}
        >
          <div className="spinner spinner--lg" />
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Running pgvector coarse filter & graph re-ranking...
          </p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="card" style={{ borderColor: 'hsla(0, 80%, 60%, 0.4)', textAlign: 'center', padding: '40px 20px' }}>
          <p style={{ color: 'hsl(0, 80%, 65%)', fontWeight: 600, marginBottom: '8px' }}>
            Failed to load recommendations
          </p>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '16px' }}>{error}</p>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={() => window.location.reload()}
          >
            Retry Feed Generation
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && recommendations.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <h3 style={{ marginBottom: '8px' }}>No micro-content lessons found yet</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '480px', margin: '0 auto 20px' }}>
            The content ingestion worker is currently parsing resources for your career track. Please check back shortly or review your current skill baselines.
          </p>
          <button type="button" className="btn btn--primary btn--sm" onClick={onNavigateToGraph}>
            Review Skill Graph
          </button>
        </div>
      )}

      {/* Recommendation Feed Items */}
      {!loading && !error && recommendations.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {recommendations.map((lesson, idx) => {
            const diffMeta = getDifficultyMeta(lesson.difficulty_level);
            const isPassed = passedLessons.has(lesson.id);

            // Split bullets for clean rendering
            const bulletList = (lesson.summary_bullets || '')
              .split('\n')
              .map((b) => b.trim())
              .filter((b) => b.length > 0);

            return (
              <article
                key={lesson.id}
                className="card"
                style={{
                  position: 'relative',
                  overflow: 'hidden',
                  border: isPassed ? '1px solid hsla(174, 72%, 56%, 0.4)' : '1px solid var(--border)',
                  background: isPassed ? 'hsla(174, 72%, 56%, 0.03)' : 'var(--bg-surface)',
                  transition: 'all 0.2s var(--ease)',
                }}
              >
                {/* Top Meta Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span
                      style={{
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        padding: '3px 8px',
                        borderRadius: 'var(--r-full)',
                        background: 'hsla(258, 90%, 66%, 0.15)',
                        color: 'var(--accent-light)',
                        border: '1px solid hsla(258, 90%, 66%, 0.3)',
                      }}
                    >
                      #{idx + 1} Best Fit
                    </span>

                    <span className="badge badge--secondary" style={{ fontSize: '0.75rem' }}>
                      {lesson.skill_name}
                    </span>

                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: diffMeta.color }}>
                      {diffMeta.label}
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {isPassed && (
                      <span
                        style={{
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          color: 'var(--teal)',
                          background: 'hsla(174,72%,56%,0.15)',
                          padding: '2px 8px',
                          borderRadius: 'var(--r-full)',
                        }}
                      >
                        ✓ Lesson passed
                      </span>
                    )}
                  </div>
                </div>

                {/* Title */}
                <h3 style={{ fontSize: '1.25rem', marginBottom: '12px', lineHeight: 1.35 }}>
                  {lesson.title}
                </h3>

                {/* Takeaways Container */}
                <div
                  style={{
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--r-md)',
                    padding: '14px 16px',
                    marginBottom: '16px',
                  }}
                >
                  <p style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '8px', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    Core Technical Takeaways
                  </p>
                  <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {bulletList.map((bullet, bIdx) => {
                      const cleanBullet = bullet.replace(/^[•*-]\s*/, '');
                      return (
                        <li key={bIdx} style={{ fontSize: '0.88rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'flex-start', gap: '8px', lineHeight: 1.45 }}>
                          <span style={{ color: 'var(--teal)', fontWeight: 700, lineHeight: 1.2 }}>•</span>
                          <span>{cleanBullet}</span>
                        </li>
                      );
                    })}
                  </ul>
                </div>

                {/* Bottom Action Footer */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  {lesson.source_url ? (
                    <a
                      href={lesson.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => { recordContentOpen(user.id, lesson.id).catch((err) => console.error('Could not record lesson open:', err)); }}
                      style={{ fontSize: '0.82rem', color: 'var(--accent-light)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      Read full source material ↗
                    </a>
                  ) : <div />}

                  <button
                    type="button"
                    className={`btn ${isPassed ? 'btn--secondary' : 'btn--primary'} btn--sm`}
                    onClick={() => handleStartQuiz(lesson)}
                    style={{ minWidth: '140px' }}
                  >
                    {isPassed ? `Retake Quiz (${lesson.quizzes?.length || 0} questions)` : `Take Quiz (${lesson.quizzes?.length || 0} questions)`}
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}

      {/* ── Active Quiz Modal Overlay ── */}
      {activeQuizLesson && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'hsla(0, 0%, 0%, 0.75)',
            backdropFilter: 'blur(6px)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '16px',
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget && !submittingQuiz) setActiveQuizLesson(null);
          }}
        >
          <div
            className="card"
            style={{
              width: '100%',
              maxWidth: '680px',
              maxHeight: '90vh',
              overflowY: 'auto',
              background: 'var(--bg-surface)',
              border: '1px solid var(--accent-border)',
              borderRadius: 'var(--r-lg)',
              boxShadow: 'var(--shadow-md)',
              padding: '24px 28px',
              textAlign: 'left',
            }}
          >
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', gap: '12px' }}>
              <div>
                <span className="badge badge--accent" style={{ fontSize: '0.75rem', marginBottom: '6px' }}>
                  {activeQuizLesson.skill_name} Assessment
                </span>
                <h3 style={{ fontSize: '1.25rem', lineHeight: 1.3 }}>{activeQuizLesson.title}</h3>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                  Answer all {activeQuizLesson.quizzes?.length || 0} questions. A passing score of 60% increases the skill proficiency estimate by 10 points on the first pass.
                </p>
              </div>

              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setActiveQuizLesson(null)}
                disabled={submittingQuiz}
                style={{ fontSize: '1.1rem', padding: '4px 8px' }}
              >
                ✕
              </button>
            </div>

            {/* Questions List */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', marginBottom: '24px' }}>
              {(activeQuizLesson.quizzes || []).map((q, qIdx) => {
                const selectedOption = quizAnswers[qIdx];
                const feedbackItem = quizResult?.feedback?.[qIdx];

                return (
                  <div
                    key={qIdx}
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--r-md)',
                      padding: '16px',
                    }}
                  >
                    <p style={{ fontSize: '0.95rem', fontWeight: 600, marginBottom: '12px' }}>
                      {qIdx + 1}. {q.question}
                    </p>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
                      {(q.options || []).map((opt, oIdx) => {
                        const isSelected = selectedOption === opt;
                        let optionStyle = {
                          display: 'flex',
                          alignItems: 'center',
                          padding: '10px 14px',
                          borderRadius: 'var(--r-sm)',
                          fontSize: '0.88rem',
                          cursor: quizResult ? 'default' : 'pointer',
                          transition: 'all 0.15s var(--ease)',
                          border: '1px solid var(--border)',
                          background: 'var(--bg-input)',
                          color: 'var(--text-primary)',
                        };

                        if (isSelected && !quizResult) {
                          optionStyle.border = '1px solid var(--accent-light)';
                          optionStyle.background = 'hsla(258, 90%, 66%, 0.15)';
                          optionStyle.color = '#fff';
                        }

                        // Post-submission styling
                        if (quizResult && feedbackItem) {
                          if (opt === feedbackItem.correct_answer) {
                            optionStyle.border = '1px solid var(--teal)';
                            optionStyle.background = 'hsla(174, 72%, 56%, 0.15)';
                            optionStyle.color = 'var(--teal)';
                          } else if (isSelected && !feedbackItem.is_correct) {
                            optionStyle.border = '1px solid hsl(0, 80%, 60%)';
                            optionStyle.background = 'hsla(0, 80%, 60%, 0.15)';
                            optionStyle.color = 'hsl(0, 80%, 75%)';
                          }
                        }

                        return (
                          <div
                            key={oIdx}
                            style={optionStyle}
                            onClick={() => handleSelectOption(qIdx, opt)}
                          >
                            <span style={{ marginRight: '10px', opacity: 0.6 }}>
                              {String.fromCharCode(65 + oIdx)}.
                            </span>
                            <span>{opt}</span>
                          </div>
                        );
                      })}
                    </div>

                    {/* Post-submission explanation */}
                    {feedbackItem && (
                      <div
                        style={{
                          marginTop: '10px',
                          padding: '8px 12px',
                          borderRadius: 'var(--r-sm)',
                          fontSize: '0.8rem',
                          background: feedbackItem.is_correct ? 'hsla(174, 72%, 56%, 0.08)' : 'hsla(0, 80%, 60%, 0.08)',
                          color: feedbackItem.is_correct ? 'var(--teal)' : 'hsl(0, 80%, 75%)',
                        }}
                      >
                        {feedbackItem.is_correct ? '✓ Correct! ' : '✗ Incorrect. '}
                        {feedbackItem.explanation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Quiz Result Banner */}
            {quizResult && (
              <div
                style={{
                  padding: '16px 20px',
                  borderRadius: 'var(--r-md)',
                  background: quizResult.passed ? 'hsla(174,72%,56%,0.12)' : 'hsla(0,80%,60%,0.10)',
                  border: quizResult.passed ? '1px solid var(--teal)' : '1px solid hsla(0,80%,60%,0.3)',
                  marginBottom: '20px',
                  textAlign: 'center',
                }}
              >
                <h4 style={{ fontSize: '1.2rem', color: quizResult.passed ? 'var(--teal)' : 'hsl(0,80%,75%)', marginBottom: '4px' }}>
                  {quizResult.passed ? 'Assessment Passed!' : 'Need a bit more practice'}
                </h4>
                <p style={{ fontSize: '0.9rem', color: 'var(--text-primary)', marginBottom: '8px' }}>
                  You scored <strong>{quizResult.score} / {quizResult.total}</strong> ({quizResult.percentage}%).
                  {quizResult.passed ? (
                    <span> <strong>+{quizResult.proficiency_increment} proficiency points</strong> applied to your <strong>{activeQuizLesson.skill_name}</strong> estimate.</span>
                  ) : (
                    <span> Passing score is 60%. Review the explanations above and try again.</span>
                  )}
                </p>

                {quizResult.new_proficiency && (
                  <p style={{ fontSize: '0.85rem', color: 'var(--accent-light)' }}>
                    New {activeQuizLesson.skill_name} proficiency: <strong>{quizResult.new_proficiency}%</strong>
                    {quizResult.skill_mastered && ' (Estimate reached 100%)'}
                  </p>
                )}

                {/* "Ask MENTOR" Summon on repeated failure */}
                {quizResult.ask_mentor_suggested && (
                  <div
                    style={{
                      marginTop: '12px',
                      padding: '10px 14px',
                      borderRadius: 'var(--r-sm)',
                      background: 'hsla(258,90%,66%,0.15)',
                      border: '1px solid var(--accent-border)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                      Struggling with {activeQuizLesson.skill_name}? Connect with a mentor.
                    </span>
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => alert(`Routing to Mentorship Q&A for '${activeQuizLesson.skill_name}' (Interval 7 Marketplace).`)}
                    >
                      Ask MENTOR
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Modal Actions */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
              {!quizResult ? (
                <>
                  <button
                    type="button"
                    className="btn btn--ghost btn--sm"
                    onClick={() => setActiveQuizLesson(null)}
                    disabled={submittingQuiz}
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={handleSubmitQuiz}
                    disabled={submittingQuiz || Object.keys(quizAnswers).length < (activeQuizLesson.quizzes?.length || 1)}
                  >
                    {submittingQuiz ? 'Evaluating...' : 'Submit Answers'}
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="btn btn--primary btn--sm"
                  onClick={() => setActiveQuizLesson(null)}
                >
                  Close & Return to Feed
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
