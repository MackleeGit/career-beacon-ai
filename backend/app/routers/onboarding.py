# app/routers/onboarding.py
"""
Backwards-compatibility shim.
All core learner onboarding logic has been moved to `app.routers.learner_onboarding`.
Re-exports all public and internal helpers, as well as router and module-level singletons.
"""
import sys
import app.routers.learner_onboarding as _mod

sys.modules[__name__] = _mod
