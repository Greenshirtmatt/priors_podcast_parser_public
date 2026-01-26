import re


def slugify(value: str, max_length: int = 80) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    if not value:
        return "untitled"
    return value[:max_length].strip("-")
