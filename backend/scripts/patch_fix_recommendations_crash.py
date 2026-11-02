file_path = "frontend/src/pages/Recommendations.jsx"
with open(file_path, "r", encoding="utf-8") as f:
    code = f.read()

# 1. Fix line 801: !loading && !error -> !isCurrentTabLoading && !isCurrentTabError
target_render = "{!loading && !error && displayedItems.length > 0 && ("
repl_render = "{!isCurrentTabLoading && !isCurrentTabError && displayedItems.length > 0 && ("
assert target_render in code, "target_render not found in Recommendations.jsx"
code = code.replace(target_render, repl_render, 1)

# 2. Fix toggleExpandLesson: remove setRecommendations
old_toggle_part = """      if (isNowExpanded && user?.id) {
        recordContentOpen(user.id, lesson.id).catch(() => {});
        setRecommendations((prev) =>
          prev.map((it) =>
            it.id === lesson.id && !it.has_passed
              ? { ...it, lifecycle_state: 'in_progress' }
              : it
          )
        );
      }"""

new_toggle_part = """      if (isNowExpanded && user?.id) {
        recordContentOpen(user.id, lesson.id).catch(() => {});
        setDailyDrop((prev) => {
          if (!prev || !prev.lessons) return prev;
          return {
            ...prev,
            lessons: prev.lessons.map((it) =>
              it.id === lesson.id && !it.has_passed ? { ...it, lifecycle_state: 'in_progress' } : it
            )
          };
        });
      }"""

# Line ending tolerance
code_norm = code.replace('\r\n', '\n')
old_toggle_norm = old_toggle_part.replace('\r\n', '\n')
new_toggle_norm = new_toggle_part.replace('\r\n', '\n')

if old_toggle_norm in code_norm:
    code_norm = code_norm.replace(old_toggle_norm, new_toggle_norm, 1)

# 3. Fix handleQuizAnswerSubmit: remove setRecommendations calls
old_quiz_pass = """        setRecommendations((prev) =>
          prev.map((it) => (it.id === activeQuizLesson.id ? passedLessonObj : it))
        );"""
code_norm = code_norm.replace(old_quiz_pass.replace('\r\n', '\n'), "")

old_quiz_retry = """        setRecommendations((prev) =>
          prev.map((it) =>
            it.id === activeQuizLesson.id ? { ...it, completed: true, lifecycle_state: 'retry_needed' } : it
          )
        );"""

new_quiz_retry = """        setDailyDrop((prev) => {
          if (!prev || !prev.lessons) return prev;
          return {
            ...prev,
            lessons: prev.lessons.map((it) =>
              it.id === activeQuizLesson.id ? { ...it, completed: true, lifecycle_state: 'retry_needed' } : it
            )
          };
        });"""

if old_quiz_retry.replace('\r\n', '\n') in code_norm:
    code_norm = code_norm.replace(old_quiz_retry.replace('\r\n', '\n'), new_quiz_retry.replace('\r\n', '\n'), 1)

# 4. Remove unused getRecommendations from import if present
code_norm = code_norm.replace("  getRecommendations,\n", "")

with open(file_path, "w", encoding="utf-8") as f:
    f.write(code_norm)

print("Recommendations.jsx successfully fixed of all legacy loading/setRecommendations references!")
