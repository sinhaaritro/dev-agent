"""A tolerant YAML-ish front-matter parser shared by the engines.

This is deliberately not a YAML parser: it handles only the shapes the
framework's SKILL.md / topic-doc front matter uses (scalars, inline lists,
dash lists, and one level of nested ``key: value`` maps).
"""

import re


def parse_front_matter(text: str) -> dict:
    """Parse a YAML-ish front-matter block (--- delimited). Returns {} if absent."""
    match = re.match(r"^\ufeff?---\r?\n(.*?)\r?\n---\r?\n", text, re.DOTALL)
    if not match:
        return {}
    fields: dict = {}
    lines = match.group(1).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" not in line:
            i += 1
            continue
        key, _, value = line.partition(":")
        key = key.strip().lower()
        value = value.strip()
        if not key:
            i += 1
            continue
        if line[0].isspace() and value == "" and i + 1 < len(lines):
            continue  # blank nested line: handled by the block case below
        if value == "":
            # Block form: dash items -> list, indented "key: value" -> nested dict.
            j = i + 1
            items: list[str] = []
            sub: dict = {}
            while j < len(lines):
                nline = lines[j]
                if nline.strip() == "":
                    j += 1
                    continue
                if not nline[0].isspace():
                    break
                body = nline.strip()
                if body.startswith("-"):
                    items.append(body[1:].strip().strip("\"'"))
                    j += 1
                elif ":" in body:
                    skey, _, sval = body.partition(":")
                    if sval.strip() == "":
                        break  # two-level nesting unsupported; stop the block
                    sub[skey.strip().lower()] = sval.strip()
                    j += 1
                else:
                    break
            if sub:
                fields[key] = sub
            elif items:
                fields[key] = items
            # Resume at the first line *after* the block. Using ``j - 1``
            # re-read the last nested line as a top-level key, so a nested
            # ``metadata.tags: a, b`` also landed at top level as a string.
            i = j
            continue
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("\"'") for v in value[1:-1].split(",")]
            fields[key] = [x for x in items if x]
        elif value.startswith('"') and value.endswith('"'):
            fields[key] = value[1:-1]
        else:
            fields[key] = value
        i += 1
    return fields
