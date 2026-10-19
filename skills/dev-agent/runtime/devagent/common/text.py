"""ASCII text helpers shared by the map and routing engines."""

ASCII_MAP = {
    "\u2014": "-",  # em dash
    "\u2013": "-",  # en dash
    "\u2018": "'",  # left single quote
    "\u2019": "'",  # right single quote
    "\u201c": '"',  # left double quote
    "\u201d": '"',  # right double quote
    "\u2026": "...",  # ellipsis
    "\u2192": "->",  # right arrow
}


def normalize_marker(value: str) -> str:
    """Strip a Verify/Expect field's surrounding backticks or quotes.

    The plan template accepts ``Expect: "OK"``, ``Expect: `OK```, and a bare
    ``Expect: OK``. Both engines (compile's approval fingerprints and the
    verifier's lookups) must normalize the same way or a pre-approved command
    is refused at run time (audit finding: backtick Expect mismatch).
    """
    v = (value or "").strip()
    for _ in range(2):
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "`\"'":
            v = v[1:-1].strip()
    return v


def sanitize_ascii(text: str) -> str:
    """Map common Unicode punctuation to ASCII and drop everything non-ASCII.

    Keeps generated markdown (MAP.md, the topics index) clean in viewers that
    default to a legacy codepage.
    """
    for src, dst in ASCII_MAP.items():
        text = text.replace(src, dst)
    return "".join(ch for ch in text if ord(ch) < 128)
