def body_match_offsets(text, term):
    """Case-insensitive offsets of term in text, skipping the first (title) line."""
    if not term:
        return []
    low = text.lower()
    t = term.lower()
    nl = low.find('\n')
    start = nl + 1 if nl != -1 else len(low)
    offsets = []
    i = low.find(t, start)
    while i != -1:
        offsets.append(i)
        i = low.find(t, i + len(t))
    return offsets
