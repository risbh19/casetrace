import re

STOP_WORDS = set(
    "a about an and are as at be by can did do does for from how i in is it may of on or should "
    "tell than that the their this to under use was what when where which who will with would you".split()
)


def normalize(text: str) -> str:
    return " ".join(word for word in re.findall(r"[a-z0-9]+", text.lower()) if word not in STOP_WORDS)


def score(question: str, keywords: list[str]) -> int:
    normalized = normalize(question)
    query_words = set(normalized.split()) - STOP_WORDS
    best = 0
    for phrase in keywords:
        phrase = normalize(phrase)
        words = set(phrase.split()) - STOP_WORDS
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            best = max(best, 16 + len(words) * 4)
        elif len(query_words & words) >= 2:
            best = max(best, 2 * len(query_words & words))
    return best


def requested_sections(question: str) -> set[tuple[str, str]]:
    found = set()
    for act in ("BNSS", "BNS", "BSA", "IT Act"):
        name = re.escape(act)
        reference = r"\d{2}[a-z]\b" if act == "IT Act" else r"\d{2,3}\b(?:\s*\([0-9a-z]+\))*"
        pattern = rf"\b{name}\s+(?:section\s+)?({reference})|\bsection\s+({reference})\s+(?:of\s+)?(?:the\s+)?{name}\b"
        for match in re.finditer(pattern, question, re.IGNORECASE):
            found.add((act, re.sub(r"\s+", "", match[1] or match[2]).casefold()))
    return found
