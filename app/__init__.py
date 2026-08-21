import os
import sys
import types

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

if "paper_signs_backend" not in sys.modules:
    try:
        import paper_signs_backend  # noqa
    except ImportError:
        pkg = types.ModuleType("paper_signs_backend")
        pkg.__path__ = [current_dir]
        sys.modules["paper_signs_backend"] = pkg
