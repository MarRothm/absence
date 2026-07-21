"""Entry point for PyInstaller — runs absence_dashboard.app as __main__.

A PyInstaller-frozen script's own directory is what ends up on sys.path (mirroring
`python <script>` behavior), so the entry point must live at the repo root — not inside
absence_dashboard/ — for `from absence_dashboard import ...` to resolve.
"""
import runpy

runpy.run_module("absence_dashboard.app", run_name="__main__")
