import os
import pytest


def pytest_collection_modifyitems(config, items):
    if os.getenv("RUN_LIVE_SUPABASE_TESTS") == "1":
        return
    skip_live = pytest.mark.skip(reason="Set RUN_LIVE_SUPABASE_TESTS=1 to run against the configured Supabase project")
    for item in items:
        if "live_supabase" in item.keywords:
            item.add_marker(skip_live)
