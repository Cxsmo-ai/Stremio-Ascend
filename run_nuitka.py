
try:
    from src.gui.app import run_app
    if __name__ == '__main__':
        run_app()
except ImportError as e:
    import sys
    print(f"Import Error: {e}", file=sys.stderr)
    print(f"sys.path: {sys.path}", file=sys.stderr)
    input("Press Enter to exit...")
except Exception as e:
    import sys
    import traceback
    traceback.print_exc()
    input("Press Enter to exit...")
