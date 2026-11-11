import re

file_path = "frontend/src/pages/Recommendations.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Update imports from ../lib/api to include getCompletedLibrary and clean getRecommendations
old_api_import = """import {
  getRecommendations,
  submitQuiz,
  recordContentOpen,
  submitLessonFeedback,
  getCurrentDailyDrop,
  rerollDailyDrop,
} from '../lib/api';"""

new_api_import = """import {
  getCompletedLibrary,
  submitQuiz,
  recordContentOpen,
  submitLessonFeedback,
  getCurrentDailyDrop,
  rerollDailyDrop,
} from '../lib/api';"""

if old_api_import in code:
    code = code.replace(old_api_import, new_api_import, 1)

# Remove SPRINT_SIZE declaration
code = re.sub(r'const SPRINT_SIZE = 5;\r?\n', '', code)
code = re.sub(r'// SPRINT_SIZE legacy removed\r?\n', '', code)

# 2. Update state declarations inside Recommendations function
old_state_block = """  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendations, setRecommendations] = useState([]);
  const [completedLibrary, setCompletedLibrary] = useState([]);
  const [feedSubTab, setFeedSubTab] = useState(initialSubTab && initialSubTab !== 'sprint' ? initialSubTab : 'daily');
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
  const [imgErrors, setImgErrors] = useState({});
  const [dailyDrop, setDailyDrop] = useState(null);
  const [loadingDailyDrop, setLoadingDailyDrop] = useState(true);
  const [dailyDropError, setDailyDropError] = useState(null);
  const [rerollingDrop, setRerollingDrop] = useState(false);
  const activeRequestIdRef = useRef(0);
  const abortControllerRef = useRef(null);"""

new_state_block = """  const [dailyDrop, setDailyDrop] = useState(null);
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
  const abortControllerRef = useRef(null);"""

# Normalize line endings
if old_state_block.replace('\r\n', '\n') in code.replace('\r\n', '\n'):
    code = code.replace(old_state_block.replace('\n', '\r\n'), new_state_block.replace('\n', '\r\n'))
    if old_state_block in code:
        code = code.replace(old_state_block, new_state_block)

# 3. Replace fetchFeed and loadMoreRecommendations with clean fetchCompleted and progressive pipeline timer
old_fetch_block = """  const fetchFeed = useCallback(async () => {
    if (!user?.id) return;
    const reqId = ++activeRequestIdRef.current;
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    // Only show full-screen skeleton if no lessons are loaded yet
    setLoading((prevLoading) => {
      return recommendations.length === 0 ? true : prevLoading;
    });
    if (recommendations.length === 0) {
      setError(null);
    }
    try {
      const res = await getRecommendations(user.id, SPRINT_SIZE, 0, [], { signal: abortController.signal });
      if (reqId !== activeRequestIdRef.current) return;
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
      setError(null);
      setLoadMoreError(null);
    } catch (err) {
      if (err?.name === 'AbortError' || reqId !== activeRequestIdRef.current) {
        return;
      }
      console.error('Failed to load recommendations:', err);
      if (recommendations.length > 0) {
        // Soft error notice if lessons are already rendered
        setLoadMoreError('Unable to refresh recommendations. Showing current sprint.');
      } else {
        setError(err.message || 'Could not load recommendations');
      }
    } finally {
      if (reqId === activeRequestIdRef.current) {
        setLoading(false);
      }
    }
  }, [user?.id, recommendations.length]);

  useEffect(() => {
    fetchFeed();
  }, [fetchFeed]);

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
      setFeedbackToast(err.message || 'Could not shuffle sprint.');
    } finally {
      setRerollingDrop(false);
    }
  };

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
  }, [user?.id, recommendations, completedLibrary]);"""

new_fetch_block = """  // Progressive Pipeline Stages for Educational Curation
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
  };"""

# Replace fetch block with line ending tolerance
code_norm = code.replace('\r\n', '\n')
old_norm = old_fetch_block.replace('\r\n', '\n')
new_norm = new_fetch_block.replace('\r\n', '\n')

assert old_norm in code_norm, "Old fetch block not found!"
code_norm = code_norm.replace(old_norm, new_norm, 1)

# Replace lines around isCurrentTabLoading
old_loading_calc = """  const isCurrentTabLoading = feedSubTab === 'daily' ? loadingDailyDrop : loading;
  const isCurrentTabError = feedSubTab === 'daily' ? dailyDropError : error;

  let displayedItems = dailyDrop?.lessons || [];
  if (feedSubTab === 'completed') displayedItems = completedLibrary;
  if (feedSubTab === 'saved') displayedItems = savedLessons;"""

new_loading_calc = """  const isCurrentTabLoading = feedSubTab === 'daily' ? loadingDailyDrop : (feedSubTab === 'completed' ? loadingCompleted : false);
  const isCurrentTabError = feedSubTab === 'daily' ? dailyDropError : (feedSubTab === 'completed' ? completedError : null);

  let displayedItems = dailyDrop?.lessons || [];
  if (feedSubTab === 'completed') displayedItems = completedLibrary;
  if (feedSubTab === 'saved') displayedItems = savedLessons;"""

code_norm = code_norm.replace(old_loading_calc.replace('\r\n', '\n'), new_loading_calc.replace('\r\n', '\n'), 1)

# Remove unused sprintCompletedCount
code_norm = re.sub(r'  const sprintCompletedCount = [^\n]+\n', '', code_norm)

# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(code_norm)

print("Recommendations.jsx successfully cleaned of legacy sprint code and wired with progressive pipeline timer!")

