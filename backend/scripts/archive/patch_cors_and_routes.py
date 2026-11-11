# Update CORS in backend/app/main.py
with open("backend/app/main.py", "r", encoding="utf-8") as f:
    main_code = f.read()

cors_target = "allow_credentials=True,"
cors_repl = 'allow_origin_regex=r"https://.*\\.netlify\\.app",\n    allow_credentials=True,'

if cors_target in main_code and "allow_origin_regex" not in main_code:
    main_code = main_code.replace(cors_target, cors_repl, 1)
    with open("backend/app/main.py", "w", encoding="utf-8") as f:
        f.write(main_code)
    print("backend/app/main.py updated with allow_origin_regex")

# Add /library/completed route in backend/app/routers/recommendations.py
with open("backend/app/routers/recommendations.py", "r", encoding="utf-8") as f:
    rec_code = f.read()

rec_target = '@router.get("/{user_id}")'
rec_addition = '''@router.get("/library/completed")
async def get_user_completed_library(http_req: Request):
    caller_id = get_verified_user_id(http_req)
    try:
        completed = await recommendation_service.get_completed_library_for_user(caller_id)
        return {"status": "success", "completed_library": completed}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load completed library: {str(e)}")


@router.get("/{user_id}")'''

if rec_target in rec_code and "/library/completed" not in rec_code:
    rec_code = rec_code.replace(rec_target, rec_addition, 1)
    with open("backend/app/routers/recommendations.py", "w", encoding="utf-8") as f:
        f.write(rec_code)
    print("backend/app/routers/recommendations.py updated with /library/completed route")

