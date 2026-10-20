"""Normalize third-party skill frontmatter into the framework's internal shape.

Third-party skills ship in whatever shape their author chose: a top-level
``tags:`` list, an inline ``[a, b]``, a comma- or whitespace-separated string,
a ``trigger_tags:``/``keywords:`` alias, or the same fields nested under
``metadata:``. Rather than chase every format at each call site, the engines
funnel frontmatter through this one documented normalizer.

The framework's own shipped skills stay canonical (top-level ``tags:`` as a
list); this module only accommodates edge formats. Extend the field lists when a
new format appears - never add per-skill special cases.
"""

import re

# Tag fields, in priority order. Extend this list when a new format appears.
TAG_FIELDS = ("tags", "trigger_tags", "triggers", "keywords", "topics")
# Nested containers a field may live under (checked after top level).
NESTED_CONTAINERS = ("metadata", "meta", "frontmatter")
# Scope fields, in priority order (top level first, then nested containers).
SCOPE_FIELDS = ("scope", "activation", "activation_scope")

_SPLIT_RE = re.compile(r"[,\s]+")


def _raw_values(fields: dict, name: str) -> list:
    """Every raw value for ``name``: top level first, then nested containers."""
    values = []
    if name in fields:
        values.append(fields[name])
    for container in NESTED_CONTAINERS:
        nested = fields.get(container)
        if isinstance(nested, dict) and name in nested:
            values.append(nested[name])
    return values


def _first(fields: dict, names: tuple[str, ...]):
    """The first non-empty raw value across ``names`` (priority order)."""
    for name in names:
        for value in _raw_values(fields, name):
            if value not in (None, "", [], {}):
                return value
    return None


def _split(value) -> list[str]:
    """A tag value in any accepted shape -> a flat list of strings."""
    if isinstance(value, (list, tuple, set)):
        out: list[str] = []
        for item in value:
            out.extend(_split(item))
        return out
    if not isinstance(value, str):
        return []
    text = value.strip()
    if text.startswith("[") and text.endswith("]"):
        text = text[1:-1]
    return [part for part in _SPLIT_RE.split(text) if part]


def normalize_tags(fields: dict) -> list[str]:
    """The first matching tag field, normalized.

    Accepts a list, an inline ``[a, b]``, ``a, b``, or ``a b``. Tags are
    lowercased, trimmed, stripped of empties, and de-duplicated with order
    preserved. A skill that declares no tag field returns ``[]`` - no tags are
    ever invented.
    """
    raw = _first(fields, TAG_FIELDS)
    if raw is None:
        return []
    seen: set[str] = set()
    tags: list[str] = []
    for value in _split(raw):
        tag = value.strip().strip("\"'").strip().lower()
        if tag and tag not in seen:
            seen.add(tag)
            tags.append(tag)
    return tags


def normalize_scope(fields: dict, default: str = "on-demand") -> str:
    """The first matching scope field (normalized to lowercase), else ``default``."""
    raw = _first(fields, SCOPE_FIELDS)
    if raw is None:
        return default
    if isinstance(raw, (list, tuple, set)):
        raw = next((item for item in raw if item), "")
    if not isinstance(raw, str):
        return default
    scope = raw.strip().strip("\"'").strip().lower()
    return scope or default
