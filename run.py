"""Entry point for PyInstaller.

Must be a real `import` (not a runtime string, e.g. via runpy) so PyInstaller's static
analyzer can trace it and actually bundle the absence_dashboard package's code — a dynamic
`runpy.run_module("absence_dashboard.app")` is invisible to that analysis and silently
leaves the package out of the frozen build (see specs/003-sharepoint-direct-connection
implementation notes). Also must live at the repo root, not inside absence_dashboard/, so
that package's own internal `from absence_dashboard import ...` imports resolve correctly.
"""
from absence_dashboard.app import main

if __name__ == "__main__":
    main()
