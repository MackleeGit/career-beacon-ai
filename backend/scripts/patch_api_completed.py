with open("frontend/src/lib/api.js", "r", encoding="utf-8") as f:
    code = f.read()

target = "export async function rerollDailyDrop() {"
repl = """export async function getCompletedLibrary() {
  return request('/api/recommendations/library/completed');
}

export async function rerollDailyDrop() {"""

if target in code and "getCompletedLibrary" not in code:
    code = code.replace(target, repl, 1)
    with open("frontend/src/lib/api.js", "w", encoding="utf-8") as f:
        f.write(code)
    print("frontend/src/lib/api.js updated with getCompletedLibrary")
else:
    print("target not found or already patched")
