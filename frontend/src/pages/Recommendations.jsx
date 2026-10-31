// src/pages/Recommendations.jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import { getRecommendations, recordContentOpen, submitQuiz } from '../lib/api';

const SOURCE_BADGE_META = {
  youtube: { icon: '🎥', label: 'YouTube Lecture', bg: 'hsla(0, 85%, 60%, 0.14)', color: 'hsl(0, 85%, 68%)', border: 'hsla(0, 85%, 60%, 0.3)' },
  structured_tutorial: { icon: '📘', label: 'Interactive Tutorial', bg: 'hsla(145, 70%, 48%, 0.14)', color: 'hsl(145, 70%, 60%)', border: 'hsla(145, 70%, 48%, 0.3)' },
  open_textbook: { icon: '📚', label: 'Open Textbook', bg: 'hsla(210, 85%, 60%, 0.14)', color: 'hsl(210, 85%, 68%)', border: 'hsla(210, 85%, 60%, 0.3)' },
  clinical_science: { icon: '🏥', label: 'NCBI / Europe PMC', bg: 'hsla(174, 72%, 56%, 0.14)', color: 'var(--teal)', border: 'hsla(174, 72%, 56%, 0.3)' },
  mdn: { icon: '⚡', label: 'MDN Web Docs', bg: 'hsla(38, 92%, 55%, 0.14)', color: 'hsl(38, 92%, 62%)', border: 'hsla(38, 92%, 55%, 0.3)' },
  openalex: { icon: '🎓', label: 'OpenAlex Academic', bg: 'hsla(258, 90%, 66%, 0.14)', color: 'var(--accent-light)', border: 'hsla(258, 90%, 66%, 0.3)' },
  wikipedia: { icon: '🌐', label: 'Reference Overview', bg: 'hsla(220, 15%, 60%, 0.14)', color: 'var(--text-secondary)', border: 'hsla(220, 15%, 60%, 0.3)' },
};

const SPRINT_SIZE = 10;

export default function Recommendations({ user, career, onSkillUpdated, onNavigateToGraph, onAskMentorAboutLesson }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [completedLibrary, setCompletedLibrary] = useState([]);
  const [feedSubTab, setFeedSubTab] = useState('sprint'); // 'sprint' | 'completed'
  const [sprintNumber, setSprintNumber] = useState(1);
  const [expandedLessons, setExpandedLessons] = useState(() => new Set());
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState(null);
  const loadMoreSentinelRef = useRef(null);
  const loadingMoreRef = useRef(false);
  const [activeQuizLesson, setActiveQuizLesson] = useState(null);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [quizResult, setQuizResult] = useState(null);
  const [passedLessons, setPassedLessons] = useState(() => new Set());

  // Fetch initial 10-lesson sprint on mount
  useEffect(() => {
    let isMounted = true;

    async function fetchFeed() {
      if (!user?.id) return;
      setLoading(true);
      setError(null);
      try {
        const res = await getRecommendations(user.id, SPRINT_SIZE);
        if (isMounted) {
          const items = res.recommendations || [];
          const serverLibrary = res.completed_library || [];
          const activeItems = items.filter((it) => !it.has_passed);
          const alreadyPassed = [...serverLibrary, ...items.filter((it) => it.has_passed)];
          setRecommendations(activeItems.length > 0 ? activeItems : items);
          setCompletedLibrary((prev) => {
            const existingIds = new Set(prev.map((p) => p.id));
            const merged = [...prev];
            for (const p of alreadyPassed) {
              if (p?.id && !existingIds.has(p.id)) {
                existingIds.add(p.id);
                merged.push(p);
              }
            }
            return merged;
          });
          setPassedLessons((prev) => new Set([...prev, ...alreadyPassed.map((p) => p.id)]));
          setHasMore(items.length >= 4);
          setLoadMoreError(null);
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

  const loadMoreRecommendations = useCallback(async () => {
    if (!user?.id || loadingMoreRef.current) return;
    loadingMoreRef.current = true;
    setLoadingMore(true);
    setLoadMoreError(null);
    try {
      const seenIds = [
        ...recommendations.map((lesson) => lesson.id),
        ...completedLibrary.map((lesson) => lesson.id),
      ];
      const res = await getRecommendations(user.id, SPRINT_SIZE, 0, seenIds);
      const nextItems = res.recommendations || [];
      if (nextItems.length > 0) {
        setRecommendations((current) => {
          const knownIds = new Set(current.map((lesson) => lesson.id));
          return [...current, ...nextItems.filter((lesson) => !knownIds.has(lesson.id))];
        });
        setSprintNumber((n) => n + 1);
      }
      setHasMore(nextItems.length >= 4);
    } catch (err) {
      console.error('Failed to load more recommendations:', err);
      setLoadMoreError('Could not load more lessons. Please try again.');
    } finally {
      loadingMoreRef.current = false;
      setLoadingMore(false);
    }
  }, [user?.id, recommendations, completedLibrary]);

  const toggleExpandLesson = (lesson) => {
    const isNowExpanded = !expandedLessons.has(lesson.id);
    setExpandedLessons((prev) => {
      const next = new Set(prev);
      if (next.has(lesson.id)) next.delete(lesson.id);
      else next.add(lesson.id);
      return next;
    });
    if (isNowExpanded && user?.id) {
      recordContentOpen(user.id, lesson.id).catch(() => {});
      setRecommendations((prev) =>
        prev.map((it) =>
          it.id === lesson.id && !it.has_passed
            ? { ...it, opened: true, lifecycle_state: 'in_progress_opened' }
            : it
        )
      );
    }
  };

  // Open Quiz Modal
  const handleStartQuiz = (lesson) => {
    setActiveQuizLesson(lesson);
    setQuizAnswers({});
    setQuizResult(null);
  };

  // Select an option for a question
  const handleSelectOption = (qIdx, option) => {
    if (quizResult) return;
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
        const passedLessonObj = { ...activeQuizLesson, has_passed: true, lifecycle_state: 'completed_passed' };
        setPassedLessons((prev) => new Set([...prev, activeQuizLesson.id]));
        setCompletedLibrary((prev) => {
          const exists = prev.some((p) => p.id === activeQuizLesson.id);
          return exists ? prev : [passedLessonObj, ...prev];
        });
        // Update in-place in active sprint so user sees ✓ Passed badge, or remove on next refresh
        setRecommendations((prev) =>
          prev.map((it) => (it.id === activeQuizLesson.id ? passedLessonObj : it))
        );

        if (onSkillUpdated && activeQuizLesson.associated_skill_id && res.new_proficiency != null) {
          onSkillUpdated({
            skillId: activeQuizLesson.associated_skill_id,
            newProficiency: res.new_proficiency,
            skillMastered: res.skill_mastered,
          });
        }
      } else {
        setRecommendations((prev) =>
          prev.map((it) =>
            it.id === activeQuizLesson.id ? { ...it, completed: true, lifecycle_state: 'retry_needed' } : it
          )
        );
      }
    } catch (err) {
      alert(`Quiz submission error: ${err.message}`);
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const getDifficultyMeta = (level) => {
    switch (level) {
      case 1: return { label: 'Level 1: Beginner (Cap 50%)', color: 'hsl(142, 70%, 50%)' };
      case 2: return { label: 'Level 2: Elementary (Cap 70%)', color: 'hsl(174, 72%, 56%)' };
      case 3: return { label: 'Level 3: Intermediate (Cap 85%)', color: 'hsl(38, 92%, 55%)' };
      case 4: return { label: 'Level 4: Advanced (Cap 95%)', color: 'hsl(280, 85%, 65%)' };
      case 5: return { label: 'Level 5: Expert (Cap 100%)', color: 'hsl(0, 80%, 60%)' };
      default: return { label: `Level ${level}`, color: 'var(--accent-light)' };
    }
  };

  const getSourceBadge = (lesson) => {
    const adapter = lesson.source_adapter || 'structured_tutorial';
    const meta = SOURCE_BADGE_META[adapter] || SOURCE_BADGE_META.structured_tutorial;
    const displayLabel = lesson.source_name || meta.label;
    return { ...meta, displayLabel };
  };

  const sprintCompletedCount = recommendations.filter((r) => passedLessons.has(r.id) || r.has_passed).length;
  const displayedItems = feedSubTab === 'completed' ? completedLibrary : recommendations;

  return (
    <div style={{ maxWidth: '860px', margin: '0 auto', textAlign: 'left' }}>
      {/* Feed Hero Header */}
      <div
        className="card"
        style={{
          marginBottom: '20px',
          background: 'linear-gradient(135deg, hsla(258,90%,66%,0.08) 0%, hsla(174,72%,56%,0.05) 100%), var(--bg-surface)',
          borderColor: 'var(--accent-border)',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', flexWrap: 'wrap' }}>
              <span className="badge badge--accent" style={{ fontSize: '0.75rem', letterSpacing: '0.04em' }}>
                SPRINT #{sprintNumber} • MULTI-SOURCE MIXED FEED
              </span>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                Target: <strong style={{ color: 'var(--text-primary)' }}>{career?.title || 'Selected Path'}</strong>
              </span>
            </div>
            <h2 style={{ fontSize: '1.6rem', marginBottom: '8px' }}>
              Your Personalized <span className="gradient-text">Learning Frontier</span>
            </h2>
            <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', maxWidth: '580px' }}>
              Curated 10-lesson sprints drawn from structured tutorials, open textbooks, YouTube lectures, and clinical/academic repositories. Read the in-app lesson and pass the 5-question checkpoint to advance your skill proficiency.
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

        {/* Sprint Progress Bar */}
        {recommendations.length > 0 && (
          <div style={{ marginTop: '18px', paddingTop: '14px', borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <span>Active Sprint Completion</span>
              <strong>{sprintCompletedCount} / {recommendations.length} lessons passed</strong>
            </div>
            <div className="progress-bar" style={{ height: '7px' }}>
              <div
                className="progress-bar__fill"
                style={{ width: `${Math.min(100, Math.round((sprintCompletedCount / Math.max(1, recommendations.length)) * 100))}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Sub-navigation: Active Sprint vs Completed & Reviewed Library */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '10px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={`btn btn--sm ${feedSubTab === 'sprint' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setFeedSubTab('sprint')}
          >
            🔥 Active Learning Sprint ({recommendations.length})
          </button>
          <button
            type="button"
            className={`btn btn--sm ${feedSubTab === 'completed' ? 'btn--primary' : 'btn--ghost'}`}
            onClick={() => setFeedSubTab('completed')}
          >
            ✓ Completed &amp; Reviewed ({completedLibrary.length})
          </button>
        </div>

        {feedSubTab === 'sprint' && sprintCompletedCount > 0 && (
          <button
            type="button"
            className="btn btn--ghost btn--sm"
            onClick={() => {
              setRecommendations((prev) => prev.filter((it) => !passedLessons.has(it.id) && !it.has_passed));
            }}
            style={{ fontSize: '0.78rem', color: 'var(--teal)' }}
          >
            Clear {sprintCompletedCount} passed lesson{sprintCompletedCount !== 1 ? 's' : ''} to Library →
          </button>
        )}
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
            Running pgvector coarse filter &amp; multi-source feed mixer...
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
      {!loading && !error && displayedItems.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '60px 20px' }}>
          {feedSubTab === 'completed' ? (
            <>
              <h3 style={{ marginBottom: '8px' }}>No completed lessons yet</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '480px', margin: '0 auto 20px' }}>
                Pass a 5-question lesson checkpoint in your Active Learning Sprint and it will be archived here for anytime review.
              </p>
              <button type="button" className="btn btn--primary btn--sm" onClick={() => setFeedSubTab('sprint')}>
                Go to Active Sprint
              </button>
            </>
          ) : (
            <>
              <h3 style={{ marginBottom: '8px' }}>Sprint complete or no lessons queued</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '480px', margin: '0 auto 20px' }}>
                Generate your next 10-lesson sprint or review your skill graph.
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center' }}>
                <button type="button" className="btn btn--primary btn--sm" onClick={loadMoreRecommendations} disabled={loadingMore}>
                  {loadingMore ? 'Generating Sprint…' : 'Generate Next 10-Lesson Sprint ↻'}
                </button>
                <button type="button" className="btn btn--ghost btn--sm" onClick={onNavigateToGraph}>
                  Review Skill Graph
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {/* Recommendation Feed Items */}
      {!loading && !error && displayedItems.length > 0 && (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {displayedItems.map((lesson, idx) => {
              const diffMeta = getDifficultyMeta(lesson.difficulty_level);
              const srcBadge = getSourceBadge(lesson);
              const isPassed = passedLessons.has(lesson.id) || lesson.has_passed;
              const isExpanded = expandedLessons.has(lesson.id);

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

                      {/* Source Adapter Badge */}
                      <span
                        style={{
                          fontSize: '0.74rem',
                          fontWeight: 700,
                          padding: '3px 9px',
                          borderRadius: 'var(--r-full)',
                          background: srcBadge.bg,
                          color: srcBadge.color,
                          border: `1px solid ${srcBadge.border}`,
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '4px',
                        }}
                      >
                        <span>{srcBadge.icon}</span>
                        <span>{srcBadge.displayLabel}</span>
                      </span>

                      <span className="badge badge--secondary" style={{ fontSize: '0.75rem' }}>
                        {lesson.skill_name}
                      </span>

                      <span style={{ fontSize: '0.75rem', fontWeight: 600, color: diffMeta.color }}>
                        {diffMeta.label}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {isPassed ? (
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
                      ) : lesson.lifecycle_state === 'retry_needed' ? (
                        <span
                          style={{
                            fontSize: '0.74rem',
                            fontWeight: 700,
                            color: 'hsl(38, 92%, 60%)',
                            background: 'hsla(38, 92%, 55%, 0.14)',
                            padding: '2px 8px',
                            borderRadius: 'var(--r-full)',
                          }}
                        >
                          🔄 Retry Checkpoint
                        </span>
                      ) : (lesson.opened || lesson.lifecycle_state === 'in_progress_opened') ? (
                        <span
                          style={{
                            fontSize: '0.74rem',
                            fontWeight: 700,
                            color: 'hsl(210, 85%, 68%)',
                            background: 'hsla(210, 85%, 60%, 0.14)',
                            padding: '2px 8px',
                            borderRadius: 'var(--r-full)',
                          }}
                        >
                          📖 In Progress • Ready for Quiz
                        </span>
                      ) : null}
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
                      marginBottom: '14px',
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

                  {/* Expandable Self-Contained In-App Lesson & Video Embed */}
                  {isExpanded && (
                    <div
                      style={{
                        background: 'rgba(0, 201, 167, 0.04)',
                        border: '1px solid rgba(0, 201, 167, 0.25)',
                        borderRadius: 'var(--r-md)',
                        padding: '16px 18px',
                        marginBottom: '16px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '14px',
                      }}
                    >
                      {lesson.video_id && (
                        <div style={{ position: 'relative', paddingBottom: '56.25%', height: 0, overflow: 'hidden', borderRadius: 'var(--r-sm)', border: '1px solid var(--border)' }}>
                          <iframe
                            src={`https://www.youtube.com/embed/${lesson.video_id}`}
                            title={lesson.title}
                            style={{ position: 'absolute', top: 0, left: 0, width: '100%', height: '100%', border: 0 }}
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                          />
                        </div>
                      )}

                      {lesson.concept_overview ? (
                        <div>
                          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--teal)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
                            📘 In-App Concept Guide
                          </div>
                          <p style={{ fontSize: '0.9rem', lineHeight: 1.6, color: 'var(--text-primary)', whiteSpace: 'pre-line' }}>
                            {lesson.concept_overview}
                          </p>
                        </div>
                      ) : (
                        <div>
                          <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--teal)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '6px' }}>
                            📘 Study Guide
                          </div>
                          <p style={{ fontSize: '0.88rem', lineHeight: 1.55, color: 'var(--text-secondary)' }}>
                            Review the core technical takeaways above and explore the linked primary source material before taking the 5-question checkpoint.
                          </p>
                        </div>
                      )}

                      {lesson.practice_scenario && (
                        <div style={{ padding: '12px 14px', background: 'var(--bg-surface)', borderRadius: 'var(--r-sm)', borderLeft: '3px solid var(--accent-light)' }}>
                          <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--accent-light)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: '4px' }}>
                            💼 Real-World Application ({career?.title || 'On the Job'})
                          </div>
                          <p style={{ fontSize: '0.86rem', lineHeight: 1.5, color: 'var(--text-secondary)' }}>
                            {lesson.practice_scenario}
                          </p>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Bottom Action Footer */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
                      <button
                        type="button"
                        className="btn btn--ghost btn--sm"
                        onClick={() => toggleExpandLesson(lesson)}
                        style={{ fontSize: '0.82rem', padding: '5px 10px', color: 'var(--teal)', borderColor: 'rgba(0, 201, 167, 0.3)' }}
                      >
                        {isExpanded ? '▲ Hide Lesson Guide' : '📖 Read Full In-App Lesson'}
                      </button>

                      {lesson.source_url && (
                        <a
                          href={lesson.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          onClick={() => { recordContentOpen(user.id, lesson.id).catch(() => {}); }}
                          style={{ fontSize: '0.82rem', color: 'var(--accent-light)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                        >
                          Read full source material ↗
                        </a>
                      )}
                    </div>

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

          <div ref={loadMoreSentinelRef} aria-hidden="true" style={{ height: '1px' }} />
          {feedSubTab === 'sprint' && (
            <div style={{ textAlign: 'center', padding: '24px 18px' }}>
              {loadingMore && <p role="status" style={{ color: 'var(--text-secondary)' }}>Synthesizing &amp; mixing next 10-lesson sprint…</p>}
              {loadMoreError && <p role="alert" style={{ color: 'hsl(0, 80%, 65%)', marginBottom: '10px' }}>{loadMoreError}</p>}
              {!loadingMore && (
                <button
                  type="button"
                  className="btn btn--secondary btn--sm"
                  onClick={loadMoreRecommendations}
                  style={{ padding: '10px 20px', fontWeight: 600 }}
                >
                  {loadMoreError ? 'Try loading more' : 'Load Next 10-Lesson Sprint ↻'}
                </button>
              )}
            </div>
          )}
        </>
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
                  Answer all {activeQuizLesson.quizzes?.length || 0} questions. A passing score of 60% advances your skill proficiency (gated by lesson difficulty tier).
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

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {(q.options || []).map((option, oIdx) => {
                        const isSelected = selectedOption === option;
                        let optionBorder = isSelected ? 'var(--accent)' : 'var(--border)';
                        let optionBg = isSelected ? 'hsla(258, 90%, 66%, 0.14)' : 'var(--bg-surface)';
                        let optionColor = 'var(--text-primary)';

                        if (feedbackItem) {
                          if (option === feedbackItem.correct_answer) {
                            optionBorder = 'var(--teal)';
                            optionBg = 'hsla(174, 72%, 56%, 0.15)';
                            optionColor = 'var(--teal)';
                          } else if (isSelected && !feedbackItem.is_correct) {
                            optionBorder = 'hsl(0, 80%, 60%)';
                            optionBg = 'hsla(0, 80%, 60%, 0.12)';
                            optionColor = 'hsl(0, 80%, 65%)';
                          }
                        }

                        return (
                          <button
                            key={oIdx}
                            type="button"
                            onClick={() => handleSelectOption(qIdx, option)}
                            disabled={Boolean(quizResult)}
                            style={{
                              textAlign: 'left',
                              padding: '10px 14px',
                              borderRadius: 'var(--r-sm)',
                              border: `1px solid ${optionBorder}`,
                              background: optionBg,
                              color: optionColor,
                              fontSize: '0.88rem',
                              cursor: quizResult ? 'default' : 'pointer',
                              transition: 'all 0.15s var(--ease)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '8px',
                            }}
                          >
                            <span>{option}</span>
                            {feedbackItem && option === feedbackItem.correct_answer && (
                              <span style={{ fontWeight: 700 }}>✓</span>
                            )}
                            {feedbackItem && isSelected && !feedbackItem.is_correct && (
                              <span style={{ fontWeight: 700 }}>✕</span>
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {/* Per-question explanation after submission */}
                    {feedbackItem && feedbackItem.explanation && (
                      <div
                        style={{
                          marginTop: '12px',
                          padding: '10px 12px',
                          borderRadius: 'var(--r-sm)',
                          background: 'hsla(220, 20%, 10%, 0.6)',
                          borderLeft: `3px solid ${feedbackItem.is_correct ? 'var(--teal)' : 'hsl(0, 80%, 60%)'}`,
                          fontSize: '0.82rem',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        <strong style={{ color: feedbackItem.is_correct ? 'var(--teal)' : 'hsl(0, 80%, 65%)' }}>
                          {feedbackItem.is_correct ? 'Correct: ' : 'Explanation: '}
                        </strong>
                        {feedbackItem.explanation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Result Banner after Submit */}
            {quizResult && (
              <div
                style={{
                  padding: '16px',
                  borderRadius: 'var(--r-md)',
                  marginBottom: '20px',
                  border: `1px solid ${quizResult.passed ? 'hsla(174, 72%, 56%, 0.4)' : 'hsla(0, 80%, 60%, 0.4)'}`,
                  background: quizResult.passed ? 'hsla(174, 72%, 56%, 0.08)' : 'hsla(0, 80%, 60%, 0.08)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                  <div>
                    <h4 style={{ color: quizResult.passed ? 'var(--teal)' : 'hsl(0, 80%, 65%)', marginBottom: '4px' }}>
                      {quizResult.passed ? '🎉 Checkpoint Passed!' : 'Keep Practicing — Score Below 60%'}
                    </h4>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      You scored <strong>{quizResult.score} / {quizResult.total}</strong> ({quizResult.percentage}%).
                      {quizResult.passed && quizResult.proficiency_increment > 0 && (
                        <> Your <strong>{activeQuizLesson.skill_name}</strong> proficiency increased by <strong>+{quizResult.proficiency_increment}%</strong> to <strong>{quizResult.new_proficiency}%</strong>!</>
                      )}
                      {quizResult.passed && quizResult.already_completed && (
                        <> (Already completed previously — proficiency remains at {quizResult.new_proficiency}%.)</>
                      )}
                    </p>
                  </div>

                  {quizResult.ask_mentor_suggested && onAskMentorAboutLesson && (
                    <button
                      type="button"
                      className="btn btn--ghost btn--sm"
                      style={{ borderColor: 'var(--teal)', color: 'var(--teal)' }}
                      onClick={() => {
                        const targetLesson = activeQuizLesson;
                        setActiveQuizLesson(null);
                        onAskMentorAboutLesson({
                          skill_tag: targetLesson.skill_name || 'General Career',
                          title: `Clarification on ${targetLesson.skill_name}: ${targetLesson.title}`,
                          body: `I just took the micro-learning checkpoint on "${targetLesson.title}" and would appreciate a mentor's practical explanation of the core trade-offs and edge cases.`,
                          source_lesson_title: targetLesson.title,
                        });
                      }}
                    >
                      💡 Ask a Mentor About This Topic →
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* Modal Footer */}
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
                    disabled={
                      submittingQuiz ||
                      Object.keys(quizAnswers).length < (activeQuizLesson.quizzes?.length || 1)
                    }
                  >
                    {submittingQuiz ? 'Evaluating Answers...' : 'Submit Answers'}
                  </button>
                </>
              ) : (
                <>
                  {!quizResult.passed && (
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
                      onClick={() => {
                        setQuizAnswers({});
                        setQuizResult(null);
                      }}
                    >
                      Try Again
                    </button>
                  )}
                  <button
                    type="button"
                    className="btn btn--primary btn--sm"
                    onClick={() => setActiveQuizLesson(null)}
                  >
                    Done
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
