import re

with open("frontend/src/pages/Recommendations.jsx", "r", encoding="utf-8") as f:
    text = f.read()

# Match emoji unicode ranges
emoji_pattern = re.compile(
    r"[\U0001F600-\U0001F64F"  # emoticons
    r"\U0001F300-\U0001F5FF"  # symbols & pictographs
    r"\U0001F680-\U0001F6FF"  # transport & map
    r"\U0001F1E0-\U0001F1FF"  # flags (iOS)
    r"\U00002702-\U000027B0"
    r"\U000024C2-\U0001F251"
    r"\U0001f926-\U0001f937"
    r"\U00010000-\U0010ffff"
    r"]+",
    flags=re.UNICODE,
)

matches = emoji_pattern.findall(text)
print(f"Total emojis found in Recommendations.jsx: {len(matches)}")
if matches:
    print(f"Sample matches: {set(matches)}")

