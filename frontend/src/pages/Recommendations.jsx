// src/pages/Recommendations.jsx
import { useState, useEffect, useRef, useCallback } from 'react';
import {
  getCurrentDailyDrop,
  rerollDailyDrop,
  recordContentOpen,
  submitQuiz,
  submitLessonFeedback,
} from '../lib/api';
import Toast from '../components/Toast';
import { FeedCardSkeleton } from '../components/Skeleton';
import {
  Video,
  Code2,
  BookOpen,
  Stethoscope,
  FileText,
  GraduationCap,
  Globe,
  Clock,
  Bookmark,
  CheckCircle2,
  Check,
  RotateCcw,
  Play,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  ArrowLeft,
  Briefcase,
  Compass,
  HelpCircle,
  X,
  AlertCircle,
  ThumbsUp,
  ThumbsDown,
  Flag,
  Flame,
  Shuffle,
  Sparkles,
  Calendar,
} from '../components/Icons';

const SOURCE_BADGE_META = {
  youtube: {
    Icon: Video,
    label: 'YouTube Lecture',
    bg: 'var(--status-danger-bg)',
    color: 'var(--status-danger)',
    border: 'var(--status-danger-bd)',
  },
  structured_tutorial: {
    Icon: Code2,
    label: 'Interactive Tutorial',
    bg: 'var(--accent-soft)',
    color: 'var(--accent)',
    border: 'var(--accent-border)',
  },
  open_textbook: {
    Icon: BookOpen,
    label: 'Open Textbook',
    bg: 'var(--status-info-bg)',
    color: 'var(--status-info)',
    border: 'var(--status-info-bd)',
  },
  clinical_science: {
    Icon: Stethoscope,
    label: 'NCBI / Europe PMC',
    bg: 'var(--status-success-bg)',
    color: 'var(--status-success)',
    border: 'var(--status-success-bd)',
  },
  mdn: {
    Icon: FileText,
    label: 'MDN Web Docs',
    bg: 'var(--status-warning-bg)',
    color: 'var(--status-warning)',
    border: 'var(--status-warning-bd)',
  },
  openalex: {
    Icon: GraduationCap,
    label: 'OpenAlex Academic',
    bg: 'var(--accent-soft)',
    color: 'var(--accent)',
    border: 'var(--accent-border)',
  },
  wikipedia: {
    Icon: Globe,
    label: 'Reference Overview',
    bg: 'var(--surface-elevated)',
    color: 'var(--text-secondary)',
    border: 'var(--border)',
  },
};


function extractDomain(url) {
  if (!url) return 'careerbeacon.edu';
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, '');
  } catch {
    return 'careerbeacon.edu';
  }
}

function estimateLessonDuration(lesson) {
  if (lesson?.video_id) {
    return '12 min video · 5 Qs';
  }
  const charCount =
    (lesson?.concept_overview || '').length +
    (lesson?.summary_bullets || '').length +
    (lesson?.practice_scenario || '').length;
  const minutes = Math.max(5, Math.min(18, Math.ceil(charCount / 380) + 3));
  return `${minutes} min read · 5 Qs`;
}

export default function Recommendations({
  user,
  career,
  onSkillUpdated,
  onNavigateToGraph,
  onAskMentorAboutLesson,
  initialSubTab = 'daily',
}) {
  const [dailyDrop, setDailyDrop] = useState(null);
  const [loadingDailyDrop, setLoadingDailyDrop] = useState(true);
  const [dailyDropError, setDailyDropError] = useState(null);
  const [rerollingDrop, setRerollingDrop] = useState(false);

  const [completedLibrary, setCompletedLibrary] = useState([]);
  const [loadingCompleted, setLoadingCompleted] = useState(false);
  const [completedError, setCompletedError] = useState(null);

  const [feedSubTab, setFeedSubTab] = useState(initialSubTab && initialSubTab !== 'sprint' ? initialSubTab : 'daily');
  const [expandedLessons, setExpandedLessons] = useState(() => new Set());
  const [activeQuizLesson, setActiveQuizLesson] = useState(null);
  const [quizAnswers, setQuizAnswers] = useState({});
  const [submittingQuiz, setSubmittingQuiz] = useState(false);
  const [quizResult, setQuizResult] = useState(null);
  const [passedLessons, setPassedLessons] = useState(() => new Set());
  const [imgErrors, setImgErrors] = useState({});
  const [pipelinePhase, setPipelinePhase] = useState(0);
  const activeRequestIdRef = useRef(0);
  const abortControllerRef = useRef(null);

  const savedStorageKey = user?.id ? `cb_saved_lessons_${user.id}` : 'cb_saved_lessons_guest';
  const [savedLessons, setSavedLessons] = useState(() => {
    try {
      const raw = window.localStorage.getItem(savedStorageKey);
      return raw ? JSON.parse(raw) : [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    if (initialSubTab) {
      setFeedSubTab(initialSubTab === 'sprint' ? 'daily' : initialSubTab);
    }
  }, [initialSubTab]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(savedStorageKey);
      setSavedLessons(raw ? JSON.parse(raw) : []);
    } catch {
      setSavedLessons([]);
    }
  }, [savedStorageKey]);

  const toggleSaveLesson = (lesson) => {
    setSavedLessons((prev) => {
      const exists = prev.some((item) => item.id === lesson.id);
      const next = exists ? prev.filter((item) => item.id !== lesson.id) : [lesson, ...prev];
      try {
        window.localStorage.setItem(savedStorageKey, JSON.stringify(next));
      } catch {
        // Ignore storage quota errors
      }
      return next;
    });
  };

  const [feedbackMap, setFeedbackMap] = useState(() => {
    try {
      const raw = localStorage.getItem(`cb_lesson_feedback_${user?.id}`);
      return raw ? JSON.parse(raw) : {};
    } catch {
      return {};
    }
  });
  const [feedbackToast, setFeedbackToast] = useState(null);

  const handleLessonFeedback = async (lesson, type) => {
    const current = feedbackMap[lesson.id];
    const newFeedback = current === type ? null : type;
    setFeedbackMap((prev) => {
      const next = { ...prev };
      if (newFeedback) next[lesson.id] = newFeedback;
      else delete next[lesson.id];
      try {
        localStorage.setItem(`cb_lesson_feedback_${user?.id}`, JSON.stringify(next));
      } catch {}
      return next;
    });

    if (newFeedback) {
      try {
        await submitLessonFeedback(
          lesson.id,
          newFeedback,
          lesson.title,
          newFeedback === 'irrelevant' ? 'Learner flagged recommendation as irrelevant to their career roadmap.' : null
        );
        if (newFeedback === 'irrelevant') {
          setFeedbackToast('Lesson flagged as irrelevant. Forwarded to curriculum moderation.');
        } else if (newFeedback === 'like') {
          setFeedbackToast('Helpful rating recorded.');
        } else {
          setFeedbackToast('Rating recorded.');
        }
      } catch {
        // silent fallback
      }
    }
  };

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Progressive Pipeline Stages for Educational Curation
  const PIPELINE_STEPS = [
    {
      phase: 1,
      title: 'Analyzing Skill Graph & Priority Deficits',
      subtitle: `Prioritizing highest-yield competency gap for ${career?.title || 'your career path'}...`,
      badge: 'Phase 1/3'
    },
    {
      phase: 2,
      title: 'Querying Verified Educational Repositories',
      subtitle: 'Filtering domain literature across Europe PMC, MDN Web Docs & Open Courseware...',
      badge: 'Phase 2/3'
    },
    {
      phase: 3,
      title: 'Synthesizing Self-Contained Micro-Lessons',
      subtitle: 'Calibrating 3 focused instructional modules and 5-question verified checkpoints...',
      badge: 'Phase 3/3'
    }
  ];

  useEffect(() => {
    if (!loadingDailyDrop) return;
    const timer = setInterval(() => {
      setPipelinePhase((prev) => (prev + 1) % 3);
    }, 2200);
    return () => clearInterval(timer);
  }, [loadingDailyDrop]);

  const fetchDailyDrop = useCallback(async () => {
    if (!user?.id) return;
    setLoadingDailyDrop(true);
    setDailyDropError(null);
    try {
      const res = await getCurrentDailyDrop();
      if (res?.drop) {
        setDailyDrop(res.drop);
      }
    } catch (err) {
      console.error('Failed to load daily drop:', err);
      setDailyDropError(err.message || 'Could not load daily drop');
    } finally {
      setLoadingDailyDrop(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchDailyDrop();
  }, [fetchDailyDrop]);

  const fetchCompleted = useCallback(async () => {
    if (!user?.id) return;
    setLoadingCompleted(true);
    setCompletedError(null);
    try {
      const res = await getCompletedLibrary();
      setCompletedLibrary(res.completed_library || []);
    } catch (err) {
      console.error('Failed to load completed library:', err);
      setCompletedError(err.message || 'Could not load completed library');
    } finally {
      setLoadingCompleted(false);
    }
  }, [user?.id]);

  useEffect(() => {
    if (feedSubTab === 'completed') {
      fetchCompleted();
    }
  }, [feedSubTab, fetchCompleted]);

  const handleRerollDailyDrop = async () => {
    if (rerollingDrop) return;
    setRerollingDrop(true);
    try {
      const res = await rerollDailyDrop();
      if (res?.drop) {
        setDailyDrop(res.drop);
        setFeedbackToast('Daily drop shuffled to secondary deficit.');
      }
    } catch (err) {
      setFeedbackToast(err.message || 'Could not shuffle drop.');
    } finally {
      setRerollingDrop(false);
    }
  };

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

  const handleStartQuiz = (lesson) => {
    setActiveQuizLesson(lesson);
    setQuizAnswers({});
    setQuizResult(null);
  };

  const handleSelectOption = (qIdx, option) => {
    if (quizResult) return;
    setQuizAnswers((prev) => ({
      ...prev,
      [qIdx]: option,
    }));
  };

  const handleSubmitQuiz = async () => {
    if (!activeQuizLesson || submittingQuiz) return;
    setSubmittingQuiz(true);
    try {
      const res = await submitQuiz(user.id, activeQuizLesson.id, quizAnswers);
      setQuizResult(res);

      if (res.passed) {
        const passedLessonObj = { ...activeQuizLesson, has_passed: true, lifecycle_state: 'completed_passed' };
        setPassedLessons((prev) => new Set([...prev, activeQuizLesson.id]));
        if (dailyDrop?.lessons?.some((l) => l.id === activeQuizLesson.id)) {
          setDailyDrop((prev) => {
            if (!prev) return prev;
            const passedCount = (prev.passed_count || 0) + 1;
            const isComplete = passedCount >= (prev.total_count || 3);
            const streak = isComplete
              ? { ...prev.streak, current_streak: (prev.streak?.current_streak || 0) + 1, completed_today: true }
              : prev.streak;
            return {
              ...prev,
              passed_count: passedCount,
              is_completed: isComplete,
              streak,
              lessons: prev.lessons.map((l) =>
                l.id === activeQuizLesson.id ? { ...l, has_passed: true } : l
              ),
            };
          });
        }
        setCompletedLibrary((prev) => {
          const exists = prev.some((p) => p.id === activeQuizLesson.id);
          return exists ? prev : [passedLessonObj, ...prev];
        });


        if (onSkillUpdated && activeQuizLesson.associated_skill_id && res.new_proficiency != null) {
          onSkillUpdated({
            skillId: activeQuizLesson.associated_skill_id,
            newProficiency: res.new_proficiency,
            skillMastered: res.skill_mastered,
          });
        }
      } else {
        setDailyDrop((prev) => {
          if (!prev || !prev.lessons) return prev;
          return {
            ...prev,
            lessons: prev.lessons.map((it) =>
              it.id === activeQuizLesson.id ? { ...it, completed: true, lifecycle_state: 'retry_needed' } : it
            )
          };
        });
      }
    } catch (err) {
      alert(`Quiz submission error: ${err.message}`);
    } finally {
      setSubmittingQuiz(false);
    }
  };

  const getDifficultyMeta = (level) => {
    switch (level) {
      case 1:
        return { label: 'Level 1 · Cap 50%', color: 'var(--text-secondary)' };
      case 2:
        return { label: 'Level 2 · Cap 70%', color: 'var(--text-secondary)' };
      case 3:
        return { label: 'Level 3 · Cap 85%', color: 'var(--text-secondary)' };
      case 4:
        return { label: 'Level 4 · Cap 95%', color: 'var(--text-secondary)' };
      case 5:
        return { label: 'Level 5 · Cap 100%', color: 'var(--text-secondary)' };
      default:
        return { label: `Level ${level}`, color: 'var(--text-secondary)' };
    }
  };

  const getSourceBadge = (lesson) => {
    const adapter = lesson.source_adapter || 'structured_tutorial';
    const meta = SOURCE_BADGE_META[adapter] || SOURCE_BADGE_META.structured_tutorial;
    const displayLabel = lesson.source_name || meta.label;
    return { ...meta, displayLabel };
  };

  const savedIds = new Set(savedLessons.map((s) => s.id));

  const isCurrentTabLoading = feedSubTab === 'daily' ? loadingDailyDrop : (feedSubTab === 'completed' ? loadingCompleted : false);
  const isCurrentTabError = feedSubTab === 'daily' ? dailyDropError : (feedSubTab === 'completed' ? completedError : null);

  let displayedItems = dailyDrop?.lessons || [];
  if (feedSubTab === 'completed') displayedItems = completedLibrary;
  if (feedSubTab === 'saved') displayedItems = savedLessons;

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', textAlign: 'left' }}>
      {/* Clean Page Header */}
      <div
        className="card"
        style={{
          marginBottom: '18px',
          padding: '20px 24px',
        }}
      >
        {/* Habit Streak and Date Header Pill */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: 'var(--r-full)',
              background: 'rgba(235, 94, 40, 0.12)',
              border: '1px solid rgba(235, 94, 40, 0.3)',
              color: '#EB5E28',
              fontSize: '0.78rem',
              fontWeight: 700,
            }}
          >
            <Flame size={14} color="#EB5E28" />
            <span>{dailyDrop?.streak?.current_streak || 0}-Day Streak</span>
          </div>

          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 10px',
              borderRadius: 'var(--r-full)',
              background: 'var(--surface-sunken)',
              border: '1px solid var(--border-subtle)',
              color: 'var(--text-secondary)',
              fontSize: '0.78rem',
            }}
          >
            <Calendar size={13} />
            <span>{dailyDrop?.sprint_date || 'Today'} · Target: <strong style={{ color: 'var(--text-primary)' }}>{career?.title || 'Selected Path'}</strong></span>
          </div>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.35rem', marginBottom: '6px' }}>
              {feedSubTab === 'daily'
                ? `Daily Focus: ${dailyDrop?.target_skill_name || 'Assessed Priority Gap'}`
                : feedSubTab === 'completed'
                ? 'Completed & Reviewed Library'
                : 'Saved Lessons'}
            </h2>
            <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', maxWidth: '620px', lineHeight: 1.55 }}>
              {feedSubTab === 'daily'
                ? "Three verified modules calibrated to today's priority competency. Complete each 5-question checkpoint (60% to pass) to extend your daily streak."
                : feedSubTab === 'completed'
                ? 'Archived micro-learning modules where you passed the 5-question checkpoint. Review concepts and re-take quizzes anytime.'
                : 'Bookmarked lessons saved for reference during your study sessions.'}
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            {feedSubTab === 'daily' && dailyDrop?.can_reroll && (
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={handleRerollDailyDrop}
                disabled={rerollingDrop}
                title="Shuffle sprint to secondary deficit (1 per day)"
              >
                <Shuffle size={13} />
                <span>{rerollingDrop ? 'Shuffling...' : 'Shuffle Drop (1 left today)'}</span>
              </button>
            )}

            {feedSubTab === 'daily' && !dailyDrop?.can_reroll && (
              <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', background: 'var(--surface-sunken)', padding: '6px 12px', borderRadius: 'var(--r-sm)', border: '1px solid var(--border-subtle)' }}>
                {dailyDrop?.is_completed ? 'Daily sprint completed' : 'Daily shuffle used'}
              </span>
            )}

            {onNavigateToGraph && (
              <button
                type="button"
                className="btn btn--secondary btn--sm"
                onClick={onNavigateToGraph}
              >
                <ArrowLeft size={14} /> Skill Graph
              </button>
            )}
          </div>
        </div>

        {feedSubTab === 'daily' && dailyDrop && (
          <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.78rem', color: 'var(--text-secondary)', marginBottom: '6px' }}>
              <span>Daily Drop Progress</span>
              <strong className="mono" style={{ color: 'var(--text-primary)' }}>
                {dailyDrop.passed_count} / {dailyDrop.total_count} passed
              </strong>
            </div>
            <div className="progress-bar" style={{ height: '5px' }}>
              <div
                className="progress-bar__fill"
                style={{ width: `${Math.min(100, Math.round((dailyDrop.passed_count / Math.max(1, dailyDrop.total_count)) * 100))}%` }}
              />
            </div>
          </div>
        )}


      </div>

      {/* Sub-navigation */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '18px', flexWrap: 'wrap' }}>
        <div className="segmented-tabs" role="tablist" aria-label="Learning feed views">
          <button
            type="button"
            role="tab"
            aria-selected={feedSubTab === 'daily'}
            className={`segmented-tab ${feedSubTab === 'daily' ? 'segmented-tab--active' : ''}`}
            onClick={() => setFeedSubTab('daily')}
          >
            <Sparkles size={14} />
            <span>Daily Drop</span>
            <span className="segmented-tab__count">{dailyDrop?.lessons?.length || 3}</span>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={feedSubTab === 'completed'}
            className={`segmented-tab ${feedSubTab === 'completed' ? 'segmented-tab--active' : ''}`}
            onClick={() => setFeedSubTab('completed')}
          >
            <CheckCircle2 size={14} />
            <span>Completed</span>
            <span className="segmented-tab__count">{completedLibrary.length}</span>
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={feedSubTab === 'saved'}
            className={`segmented-tab ${feedSubTab === 'saved' ? 'segmented-tab--active' : ''}`}
            onClick={() => setFeedSubTab('saved')}
          >
            <Bookmark size={14} />
            <span>Saved</span>
            <span className="segmented-tab__count">{savedLessons.length}</span>
          </button>
        </div>


      </div>

      {/* Loading State with Progressive Generation Pipeline */}
      {isCurrentTabLoading && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }} aria-busy="true" aria-label="Curating daily focus drop">
          <div
            className="card"
            style={{
              padding: '24px',
              border: '1px solid var(--accent-border)',
              background: 'var(--surface)',
              position: 'relative',
              overflow: 'hidden',
              borderRadius: 'var(--r-lg)',
            }}
          >
            <div
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                height: '3px',
                background: 'linear-gradient(90deg, var(--accent) 0%, var(--status-info) 50%, var(--accent) 100%)',
                backgroundSize: '200% 100%',
                animation: 'pulse 1.8s ease-in-out infinite',
              }}
            />

            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
                <div
                  style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: 'var(--r-md)',
                    background: 'var(--accent-soft)',
                    color: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                  }}
                >
                  <Compass size={22} className="spinning" />
                </div>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '3px' }}>
                    <span className="badge badge--accent" style={{ fontSize: '0.72rem', padding: '2px 8px' }}>
                      {PIPELINE_STEPS[pipelinePhase].badge}
                    </span>
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>Curating 3-Lesson Daily Drop</span>
                  </div>
                  <h4 style={{ margin: 0, fontSize: '1.02rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {PIPELINE_STEPS[pipelinePhase].title}
                  </h4>
                </div>
              </div>

              {/* Stage Progress Pills */}
              <div style={{ display: 'flex', gap: '6px', alignItems: 'center', background: 'var(--surface-sunken)', padding: '5px 10px', borderRadius: 'var(--r-full)', border: '1px solid var(--border-subtle)' }}>
                {PIPELINE_STEPS.map((step, idx) => (
                  <div
                    key={idx}
                    style={{
                      width: idx === pipelinePhase ? '24px' : '8px',
                      height: '8px',
                      borderRadius: 'var(--r-full)',
                      background: idx <= pipelinePhase ? 'var(--accent)' : 'var(--border-strong)',
                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    }}
                    title={step.title}
                  />
                ))}
              </div>
            </div>

            <p style={{ margin: '0 0 16px', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              {PIPELINE_STEPS[pipelinePhase].subtitle}
            </p>

            <div className="progress-bar" style={{ height: '4px' }}>
              <div
                className="progress-bar__fill"
                style={{
                  width: `${((pipelinePhase + 1) / 3) * 100}%`,
                  transition: 'width 0.4s ease',
                  background: 'var(--accent)',
                }}
              />
            </div>
          </div>

          <FeedCardSkeleton count={3} />
        </div>
      )}

      {/* Error State */}
      {isCurrentTabError && !isCurrentTabLoading && (
        <div className="card" style={{ borderColor: 'var(--status-danger-bd)', textAlign: 'center', padding: '36px 24px' }}>
          <div style={{ display: 'inline-flex', padding: '10px', borderRadius: 'var(--r-full)', background: 'var(--status-danger-bg)', color: 'var(--status-danger)', marginBottom: '10px' }}>
            <AlertCircle size={20} />
          </div>
          <h3 style={{ fontSize: '1rem', marginBottom: '6px' }}>Unable to load daily drop</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.86rem', marginBottom: '16px' }}>{isCurrentTabError}</p>
          <button
            type="button"
            className="btn btn--secondary btn--sm"
            onClick={feedSubTab === 'daily' ? fetchDailyDrop : fetchFeed}
          >
            <RotateCcw size={14} /> Try again
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isCurrentTabLoading && !isCurrentTabError && displayedItems.length === 0 && (
        <div className="card" style={{ textAlign: 'center', padding: '48px 24px' }}>
          {feedSubTab === 'completed' ? (
            <>
              <h3 style={{ fontSize: '1.08rem', marginBottom: '6px' }}>No completed lessons yet</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 18px' }}>
                Pass a 5-question checkpoint in your Daily Drop and it will be saved here for review.
              </p>
              <button type="button" className="btn btn--primary btn--sm" onClick={() => setFeedSubTab('daily')}>
                Open Daily Drop
              </button>
            </>
          ) : feedSubTab === 'saved' ? (
            <>
              <h3 style={{ fontSize: '1.08rem', marginBottom: '6px' }}>No saved lessons</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 18px' }}>
                Use the Save button on any lesson card to bookmark it for later study.
              </p>
              <button type="button" className="btn btn--primary btn--sm" onClick={() => setFeedSubTab('daily')}>
                Return to Daily Drop
              </button>
            </>
          ) : dailyDrop?.is_completed && (dailyDrop?.passed_count || 0) > 0 && (dailyDrop?.passed_count || 0) >= (dailyDrop?.total_count || 0) ? (
            <>
              <h3 style={{ fontSize: '1.08rem', marginBottom: '6px' }}>Daily Drop Completed</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 18px' }}>
                You have passed all modules in today&apos;s daily drop. Your daily streak is active and locked in!
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn--primary btn--sm" onClick={() => setFeedSubTab('completed')}>
                  Review Completed Library
                </button>
                {onNavigateToGraph && (
                  <button type="button" className="btn btn--secondary btn--sm" onClick={onNavigateToGraph}>
                    Review Skill Graph
                  </button>
                )}
              </div>
            </>
          ) : !career || (!dailyDrop?.target_skill_id && dailyDrop?.target_skill_name === 'General Career Foundations') ? (
            <>
              <h3 style={{ fontSize: '1.08rem', marginBottom: '6px' }}>Welcome to Career Beacon</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 18px' }}>
                Select your target career to calibrate your skill graph and unlock your daily 3-lesson learning drops.
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                {onNavigateToGraph && (
                  <button type="button" className="btn btn--primary btn--sm" onClick={onNavigateToGraph}>
                    Calibrate Career &amp; Skills
                  </button>
                )}
              </div>
            </>
          ) : (
            <>
              <h3 style={{ fontSize: '1.08rem', marginBottom: '6px' }}>Preparing Your Daily Drop</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.88rem', maxWidth: '440px', margin: '0 auto 18px' }}>
                We are curating authentic instructional modules for your assessed skill frontier in {career?.title || 'your target career'}.
              </p>
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn--primary btn--sm" onClick={fetchDailyDrop}>
                  <RotateCcw size={14} /> Refresh Daily Drop
                </button>
                {onNavigateToGraph && (
                  <button type="button" className="btn btn--secondary btn--sm" onClick={onNavigateToGraph}>
                    Review Skill Graph
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* Recommendation Feed Items */}
      {!isCurrentTabLoading && !isCurrentTabError && displayedItems.length > 0 && (
        <>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {displayedItems.map((lesson) => {
              const diffMeta = getDifficultyMeta(lesson.difficulty_level);
              const srcBadge = getSourceBadge(lesson);
              const SourceIcon = srcBadge.Icon || BookOpen;
              const isPassed = passedLessons.has(lesson.id) || lesson.has_passed;
              const isExpanded = expandedLessons.has(lesson.id);
              const isSaved = savedIds.has(lesson.id);
              const domainLabel = extractDomain(lesson.source_url);
              const durationLabel = estimateLessonDuration(lesson);
              const showVideoThumb = Boolean(lesson.video_id && !imgErrors[lesson.id]);

              const bulletList = (lesson.summary_bullets || '')
                .split('\n')
                .map((b) => b.trim())
                .filter((b) => b.length > 0);

              return (
                <article
                  key={lesson.id}
                  className={`lesson-card ${isPassed ? 'lesson-card--passed' : ''}`}
                >
                  <div className="lesson-card__grid">
                    {/* Left Visual Panel (3-Tier Strategy: Video Thumbnail -> Source Branded Panel) */}
                    <div
                      className="lesson-card__thumb"
                      onClick={() => toggleExpandLesson(lesson)}
                      style={{ cursor: 'pointer' }}
                      title={isExpanded ? 'Hide lesson guide' : 'Open lesson guide'}
                    >
                      {showVideoThumb ? (
                        <>
                          <img
                            src={`https://i.ytimg.com/vi/${lesson.video_id}/hqdefault.jpg`}
                            alt={lesson.title}
                            className="lesson-card__thumb-img"
                            loading="lazy"
                            onError={() =>
                              setImgErrors((prev) => ({ ...prev, [lesson.id]: true }))
                            }
                          />
                          <div className="lesson-card__thumb-overlay" />
                          <div
                            style={{
                              position: 'relative',
                              zIndex: 2,
                              width: '38px',
                              height: '38px',
                              borderRadius: '50%',
                              background: 'rgba(18, 23, 20, 0.85)',
                              color: '#FFFFFF',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              border: '1px solid rgba(255,255,255,0.25)',
                            }}
                          >
                            <Play size={16} />
                          </div>
                          <span
                            style={{
                              position: 'absolute',
                              bottom: '10px',
                              left: '10px',
                              zIndex: 2,
                              fontSize: '0.68rem',
                              fontWeight: 600,
                              padding: '2px 7px',
                              borderRadius: 'var(--r-xs)',
                              background: 'rgba(18, 23, 20, 0.84)',
                              color: '#FFFFFF',
                            }}
                          >
                            Video Lecture
                          </span>
                        </>
                      ) : (
                        <div className="lesson-card__thumb-fallback">
                          <div
                            style={{
                              width: '36px',
                              height: '36px',
                              borderRadius: 'var(--r-sm)',
                              background: srcBadge.bg,
                              color: srcBadge.color,
                              border: `1px solid ${srcBadge.border}`,
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                            }}
                          >
                            <SourceIcon size={18} />
                          </div>

                          <div style={{ marginTop: 'auto' }}>
                            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                              {srcBadge.displayLabel}
                            </div>
                            <div className="mono" style={{ fontSize: '0.69rem', color: 'var(--text-muted)', marginTop: '2px' }}>
                              {domainLabel}
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {/* Right Content Column */}
                    <div className="lesson-card__body">
                      {/* Single Quiet Metadata Bar */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                          <span className="badge badge--accent">
                            {lesson.skill_name}
                          </span>
                          <span>{diffMeta.label}</span>
                          <span>·</span>
                          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                            <Clock size={12} /> {durationLabel}
                          </span>
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          {isPassed ? (
                            <span className="badge badge--success">
                              <Check size={11} /> Passed
                            </span>
                          ) : lesson.lifecycle_state === 'retry_needed' ? (
                            <span className="badge badge--warning">
                              Retry quiz
                            </span>
                          ) : lesson.opened || lesson.lifecycle_state === 'in_progress_opened' ? (
                            <span className="badge badge--info">
                              In progress
                            </span>
                          ) : null}

                          <button
                            type="button"
                            className="btn btn--ghost btn--xs"
                            onClick={() => toggleSaveLesson(lesson)}
                            aria-pressed={isSaved}
                            title={isSaved ? 'Remove from saved' : 'Save for later'}
                            style={{
                              color: isSaved ? 'var(--accent)' : 'var(--text-muted)',
                              background: isSaved ? 'var(--accent-soft)' : 'transparent',
                            }}
                          >
                            <Bookmark size={13} />
                            <span>{isSaved ? 'Saved' : 'Save'}</span>
                          </button>

                          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '2px', borderLeft: '1px solid var(--border-subtle)', paddingLeft: '6px' }}>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs"
                              onClick={() => handleLessonFeedback(lesson, 'like')}
                              title="Helpful recommendation"
                              style={{
                                padding: '3px 6px',
                                color: feedbackMap[lesson.id] === 'like' ? 'var(--status-success)' : 'var(--text-muted)',
                                background: feedbackMap[lesson.id] === 'like' ? 'var(--status-success-bg)' : 'transparent',
                              }}
                            >
                              <ThumbsUp size={12} />
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs"
                              onClick={() => handleLessonFeedback(lesson, 'dislike')}
                              title="Not helpful"
                              style={{
                                padding: '3px 6px',
                                color: feedbackMap[lesson.id] === 'dislike' ? 'var(--status-warning)' : 'var(--text-muted)',
                                background: feedbackMap[lesson.id] === 'dislike' ? 'var(--status-warning-bg)' : 'transparent',
                              }}
                            >
                              <ThumbsDown size={12} />
                            </button>
                            <button
                              type="button"
                              className="btn btn--ghost btn--xs"
                              onClick={() => handleLessonFeedback(lesson, 'irrelevant')}
                              title="Report recommendation as irrelevant (flags for admin review)"
                              style={{
                                padding: '3px 6px',
                                color: feedbackMap[lesson.id] === 'irrelevant' ? 'var(--status-danger)' : 'var(--text-muted)',
                                background: feedbackMap[lesson.id] === 'irrelevant' ? 'var(--status-danger-bg)' : 'transparent',
                              }}
                            >
                              <Flag size={12} />
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Title */}
                      <h3 style={{ fontSize: '1.08rem', lineHeight: 1.35 }}>
                        {lesson.title}
                      </h3>

                      {/* Key Takeaways (Clean Editorial List) */}
                      {bulletList.length > 0 && (
                        <ul
                          style={{
                            listStyle: 'none',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '5px',
                            paddingLeft: '12px',
                            borderLeft: '2px solid var(--border)',
                          }}
                        >
                          {bulletList.map((bullet, bIdx) => {
                            const cleanBullet = bullet.replace(/^[•*-]\s*/, '');
                            return (
                              <li key={bIdx} style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', lineHeight: 1.48 }}>
                                {cleanBullet}
                              </li>
                            );
                          })}
                        </ul>
                      )}

                      {/* Expandable Self-Contained In-App Lesson & Video Embed */}
                      {isExpanded && (
                        <div
                          style={{
                            background: 'var(--surface-subtle)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--r-md)',
                            padding: '16px 18px',
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
                              <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>
                                Concept overview
                              </div>
                              <p style={{ fontSize: '0.86rem', lineHeight: 1.62, color: 'var(--text-primary)', whiteSpace: 'pre-line' }}>
                                {lesson.concept_overview}
                              </p>
                            </div>
                          ) : (
                            <div>
                              <div style={{ fontSize: '0.74rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>
                                Study notes
                              </div>
                              <p style={{ fontSize: '0.85rem', lineHeight: 1.55, color: 'var(--text-secondary)' }}>
                                Review the key takeaways above and explore the linked primary source before taking the 5-question checkpoint.
                              </p>
                            </div>
                          )}

                          {lesson.practice_scenario && (
                            <div style={{ padding: '11px 14px', background: 'var(--surface)', borderRadius: 'var(--r-sm)', borderLeft: '3px solid var(--accent)' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '3px' }}>
                                <Briefcase size={13} /> On the job ({career?.title || 'Applied scenario'})
                              </div>
                              <p style={{ fontSize: '0.84rem', lineHeight: 1.52, color: 'var(--text-secondary)' }}>
                                {lesson.practice_scenario}
                              </p>
                            </div>
                          )}
                        </div>
                      )}

                      {/* Bottom Action Footer */}
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '10px', paddingTop: '4px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                          <button
                            type="button"
                            className="btn btn--secondary btn--sm"
                            onClick={() => toggleExpandLesson(lesson)}
                          >
                            {isExpanded ? (
                              <>
                                <ChevronUp size={14} /> Hide Lesson Guide
                              </>
                            ) : (
                              <>
                                <ChevronDown size={14} /> Read In-App Lesson
                              </>
                            )}
                          </button>

                          {lesson.source_url && (
                            <a
                              href={lesson.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              onClick={() => {
                                if (user?.id) recordContentOpen(user.id, lesson.id).catch(() => {});
                              }}
                              style={{
                                fontSize: '0.8rem',
                                fontWeight: 500,
                                color: 'var(--text-secondary)',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: '4px',
                              }}
                            >
                              <span>Source ({domainLabel})</span>
                              <ExternalLink size={12} />
                            </a>
                          )}
                        </div>

                        <button
                          type="button"
                          className={`btn ${isPassed ? 'btn--secondary' : 'btn--primary'} btn--sm`}
                          onClick={() => handleStartQuiz(lesson)}
                        >
                          {isPassed
                            ? `Retake Quiz (${lesson.quizzes?.length || 0} questions)`
                            : `Take Quiz (${lesson.quizzes?.length || 0} questions)`}
                        </button>
                      </div>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>


        </>
      )}

      {/* Active Quiz Modal Overlay */}
      {activeQuizLesson && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !submittingQuiz) setActiveQuizLesson(null);
          }}
        >
          <div className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="quiz-modal-title">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '18px', gap: '12px' }}>
              <div>
                <div style={{ fontSize: '0.76rem', fontWeight: 600, color: 'var(--accent)', marginBottom: '4px' }}>
                  {activeQuizLesson.skill_name} · Mastery checkpoint
                </div>
                <h3 id="quiz-modal-title" style={{ fontSize: '1.15rem', lineHeight: 1.3 }}>
                  {activeQuizLesson.title}
                </h3>
                <p style={{ fontSize: '0.81rem', color: 'var(--text-secondary)', marginTop: '4px' }}>
                  Answer all {activeQuizLesson.quizzes?.length || 0} questions. Score 60% or higher to advance your skill proficiency.
                </p>
              </div>

              <button
                type="button"
                className="btn btn--ghost btn--sm"
                onClick={() => setActiveQuizLesson(null)}
                disabled={submittingQuiz}
                aria-label="Close quiz modal"
                style={{ padding: '6px' }}
              >
                <X size={17} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '22px' }}>
              {(activeQuizLesson.quizzes || []).map((q, qIdx) => {
                const selectedOption = quizAnswers[qIdx];
                const feedbackItem = quizResult?.feedback?.[qIdx];

                return (
                  <div
                    key={qIdx}
                    style={{
                      background: 'var(--surface-subtle)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--r-md)',
                      padding: '15px',
                    }}
                  >
                    <p style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '10px', color: 'var(--text-primary)' }}>
                      {qIdx + 1}. {q.question}
                    </p>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
                      {(q.options || []).map((option, oIdx) => {
                        const isSelected = selectedOption === option;
                        let optionBorder = isSelected ? 'var(--accent)' : 'var(--border)';
                        let optionBg = isSelected ? 'var(--accent-soft)' : 'var(--surface)';
                        let optionColor = 'var(--text-primary)';

                        if (feedbackItem) {
                          if (option === feedbackItem.correct_answer) {
                            optionBorder = 'var(--status-success)';
                            optionBg = 'var(--status-success-bg)';
                            optionColor = 'var(--status-success)';
                          } else if (isSelected && !feedbackItem.is_correct) {
                            optionBorder = 'var(--status-danger)';
                            optionBg = 'var(--status-danger-bg)';
                            optionColor = 'var(--status-danger)';
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
                              padding: '9px 13px',
                              borderRadius: 'var(--r-sm)',
                              border: `1px solid ${optionBorder}`,
                              background: optionBg,
                              color: optionColor,
                              fontSize: '0.85rem',
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
                              <Check size={14} />
                            )}
                            {feedbackItem && isSelected && !feedbackItem.is_correct && (
                              <X size={14} />
                            )}
                          </button>
                        );
                      })}
                    </div>

                    {feedbackItem && feedbackItem.explanation && (
                      <div
                        style={{
                          marginTop: '10px',
                          padding: '9px 12px',
                          borderRadius: 'var(--r-sm)',
                          background: 'var(--surface)',
                          borderLeft: `3px solid ${feedbackItem.is_correct ? 'var(--status-success)' : 'var(--status-danger)'}`,
                          fontSize: '0.81rem',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        <strong style={{ color: feedbackItem.is_correct ? 'var(--status-success)' : 'var(--status-danger)' }}>
                          {feedbackItem.is_correct ? 'Correct: ' : 'Explanation: '}
                        </strong>
                        {feedbackItem.explanation}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {quizResult && (
              <div
                style={{
                  padding: '14px 16px',
                  borderRadius: 'var(--r-md)',
                  marginBottom: '18px',
                  border: `1px solid ${quizResult.passed ? 'var(--status-success-bd)' : 'var(--status-danger-bd)'}`,
                  background: quizResult.passed ? 'var(--status-success-bg)' : 'var(--status-danger-bg)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                  <div>
                    <h4 style={{ color: quizResult.passed ? 'var(--status-success)' : 'var(--status-danger)', marginBottom: '3px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      {quizResult.passed ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
                      <span>{quizResult.passed ? 'Checkpoint Passed' : 'Score Below 60% Threshold'}</span>
                    </h4>
                    <p style={{ fontSize: '0.84rem', color: 'var(--text-primary)' }}>
                      You scored <strong>{quizResult.score} / {quizResult.total}</strong> ({quizResult.percentage}%).
                      {quizResult.passed && quizResult.proficiency_increment > 0 && (
                        <> Your <strong>{activeQuizLesson.skill_name}</strong> proficiency increased by <strong>+{quizResult.proficiency_increment}%</strong> to <strong>{quizResult.new_proficiency}%</strong>.</>
                      )}
                      {quizResult.passed && quizResult.already_completed && (
                        <> (Previously completed — proficiency remains at {quizResult.new_proficiency}%.)</>
                      )}
                    </p>
                  </div>

                  {quizResult.ask_mentor_suggested && onAskMentorAboutLesson && (
                    <button
                      type="button"
                      className="btn btn--secondary btn--sm"
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
                      <HelpCircle size={14} /> Ask a Mentor About This Topic
                    </button>
                  )}
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
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
                      <RotateCcw size={14} /> Try Again
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

      {feedbackToast && (
        <Toast
          message={feedbackToast}
          onClose={() => setFeedbackToast(null)}
          type="info"
        />
      )}
    </div>
  );
}
