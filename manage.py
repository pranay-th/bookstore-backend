#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env into os.environ BEFORE anything else runs.
# This must be at module level (not inside main()) so the Django autoreloader
# child process also gets the variables when it re-imports this file.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv as _load
    _load(Path(__file__).resolve().parent / '.env', override=False)
except Exception:
    pass  # CI injects vars directly — missing .env is fine


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Make sure it's installed and available "
            "on your PYTHONPATH environment variable."
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
