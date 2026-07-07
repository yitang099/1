#!/usr/bin/env python3
"""Entry: GUI or --frida-worker subprocess (PyInstaller exe)."""
import sys


def _maybe_worker() -> bool:
    if len(sys.argv) >= 2 and sys.argv[1] == "--frida-worker":
        from qq_bind_client.frida_worker import main as worker_main

        raise SystemExit(worker_main(sys.argv[2:]))
    return False


if __name__ == "__main__":
    if _maybe_worker():
        pass
    from qq_bind_client.app import main

    raise SystemExit(main())
