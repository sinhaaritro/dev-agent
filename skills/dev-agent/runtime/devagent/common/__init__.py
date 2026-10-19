"""Shared helpers used across the devagent engines.

Every module here is dependency-free and side-effect-free so an engine can
import only what it needs. This is the de-duplication seam: ``find_root``,
``sanitize_ascii``, front-matter parsing, and friends live here once instead
of being copy-pasted into each engine.
"""
