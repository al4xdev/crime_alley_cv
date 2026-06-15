import sys
from pathlib import Path

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    __package__ = "harvey_guy"

from .harvey_guy import Harvey

def main():
    Harvey.setup()\
        .setup_paths()\
        .check_dependencies()\
        .ingest_documents()\
        .print_session_id()

if __name__ == "__main__":
    main()
