"""Helpers for user-supplied search text."""


def contains_pattern(value: str) -> str:
    """Escape LIKE wildcards so the search is a literal substring."""
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
