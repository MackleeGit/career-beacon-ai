with open("backend/app/routers/recommendations.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove the bottom daily-drop block
target_bottom = """@router.get("/daily-drop/current")
async def get_current_daily_drop(http_req: Request):
    caller_id = get_verified_user_id(http_req)
    try:
        drop = await daily_drop_service.get_or_create_daily_drop(caller_id)
        return {"status": "success", "drop": drop}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load daily drop: {str(e)}")


@router.post("/daily-drop/reroll")
async def reroll_daily_drop(http_req: Request):
    caller_id = get_verified_user_id(http_req)
    try:
        drop = await daily_drop_service.reroll_daily_drop(caller_id)
        return {"status": "success", "drop": drop, "message": "Daily drop shuffled to secondary deficit."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reroll daily drop: {str(e)}")"""

content = content.replace(target_bottom, "").strip()

# Insert before @router.get("/{user_id}")
target_user_id = '@router.get("/{user_id}")'
replacement = target_bottom + "\n\n\n" + target_user_id
content = content.replace(target_user_id, replacement)

with open("backend/app/routers/recommendations.py", "w", encoding="utf-8") as f:
    f.write(content + "\n")

print("Successfully rearranged recommendations router routes!")

