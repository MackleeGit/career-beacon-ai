import os

recom_path = os.path.join(os.path.dirname(__file__), "..", "app", "routers", "recommendations.py")

with open(recom_path, "r", encoding="utf-8") as f:
    code = f.read()

# We want the entire feedback endpoint definition:
feedback_block = """class RecommendationFeedbackPayload(BaseModel):
    lesson_id: str
    feedback: str  # 'like' | 'dislike' | 'irrelevant'
    lesson_title: Optional[str] = None
    reason: Optional[str] = None


@router.post("/feedback")
async def submit_lesson_feedback(payload: RecommendationFeedbackPayload, http_req: Request):
    user_id = get_verified_user_id(http_req)

    # If flagged as irrelevant or disliked with a reason, route directly to Admin Moderation Desk
    if payload.feedback == "irrelevant" or (payload.feedback == "dislike" and payload.reason):
        try:
            from app.routers.admin import _FLAGGED_ITEMS
            _FLAGGED_ITEMS.insert(0, {
                "id": f"flag-recom-{uuid.uuid4().hex[:8]}",
                "item_type": "recommendation",
                "sender_name": f"Learner ({user_id[:8]}...)",
                "target_context": f"Learning Sprint ({payload.lesson_title or payload.lesson_id})",
                "content_snippet": f"Lesson: {payload.lesson_title or payload.lesson_id}",
                "reason": payload.reason or "Learner reported this recommendation as irrelevant to their career roadmap.",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "pending_review",
            })
        except Exception as e:
            print(f"[recommendation-feedback] Moderation queue forward notice: {e}")

    return {
        "status": "success",
        "lesson_id": payload.lesson_id,
        "feedback": payload.feedback,
        "message": "Feedback recorded. Thank you for tuning the recommendation engine.",
    }"""

# Remove from bottom
if feedback_block in code:
    code = code.replace(feedback_block, "")
else:
    print("feedback_block not found exactly!")

# Place before @router.get("/{user_id}")
target_anchor = '@router.get("/{user_id}")'
if target_anchor in code:
    code = code.replace(target_anchor, feedback_block + "\n\n\n" + target_anchor, 1)
    with open(recom_path, "w", encoding="utf-8") as f:
        f.write(code)
    print("SUCCESS: reordered feedback endpoint above /{user_id}!")
else:
    print("target_anchor not found!")

