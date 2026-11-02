import sys
import os

sys.path.insert(0, os.path.abspath("backend"))

from app.main import app

def print_routes():
    print("Registered routes on FastAPI app:")
    for r in app.routes:
        methods = getattr(r, "methods", None)
        path = getattr(r, "path", None)
        if "recommendation" in str(path):
            print(f"  {methods} -> {path}")

if __name__ == "__main__":
    print_routes()
