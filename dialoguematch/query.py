"""Structured query understanding for hybrid dialogue and scene retrieval."""
from dataclasses import dataclass, field
import re

from .text import normalize, search_content, terms

# Minimal function-word filter for quote-mode spelling recovery so genuine
# dialogue words like 'watch', 'man', 'remember', or 'show' stay intact.
QUOTE_FUNCTION_WORDS = set(
    'a an the is are was were be been am i me my we us our you your he him his she her it its they them their '
    'of to in on at for with by and or but if as that this'.split()
)

_RE_QUOTED = re.compile(r'["“]([^"”]{3,400})["”]')
_RE_META_QUOTE = re.compile(
    r'^\s*(?:hey\s+)?(?:do you (?:recall|remember|know)|does anyone|what (?:movie|film)|which (?:movie|film)|anyone\b)',
    re.IGNORECASE,
)
_RE_SPEECH_CLAUSE = re.compile(
    r'\b(?:says?|said|asks?|asked|tells?|told|whispers?|whispered|shouts?|shouted|yells?|yelled|'
    r'orders?|ordered|demands?|demanded|warns?|warned|repeats?|repeated|announces?|announced|'
    r'admits?|admitted|confesses?|confessed|replies|replied|answers?|answered|'
    r'telling (?:him|her|them|someone)|talk(?:s|ing)? about)\s+'
    r'(?:(?:him|her|them|everyone|someone|somebody|the [a-z]+)\s+)?'
    r'(?:to\s+|that\s+|about\s+|whether\s+|if\s+|why\s+|how\s+)?'
    r'([^.!?;,]{3,90})',
    re.IGNORECASE,
)
_RE_NUMBER_UNIT = re.compile(
    r'\b\d+\s+(?:years?|days?|months?|weeks?|hours?|minutes?|seconds?|miles?|feet|dollars?|percent|times?|heads?)\b'
)


@dataclass(frozen=True)
class QueryPlan:
    raw: str
    mode: str
    normalized: str
    retrieval_query: str
    all_tokens: list[str]
    tokens: list[str]
    quote_tokens: list[str]
    embedded_quotes: list[str] = field(default_factory=list)
    has_external_context: bool = False
    speech_terms: list[str] = field(default_factory=list)
    number_anchors: list[str] = field(default_factory=list)


def analyze_query(query: str, mode: str = 'auto') -> QueryPlan:
    normalized = normalize(query)
    embedded_quotes: list[str] = []
    unquoted = query

    if mode != 'scene':
        for match in _RE_QUOTED.finditer(query):
            candidate = match.group(1).strip()
            if _RE_META_QUOTE.search(candidate):
                continue
            words = normalize(candidate).split()
            if 3 <= len(words) <= 60:
                embedded_quotes.append(candidate)
                unquoted = unquoted.replace(match.group(0), ' ')

    outside_terms = terms(search_content(unquoted)) if embedded_quotes else []
    has_external_context = len(outside_terms) >= 2

    cleaned = search_content(query) if mode != 'quote' else query
    all_tokens = terms(cleaned) or normalized.split()
    tokens = all_tokens[:45]

    quote_words = normalized.split()
    quote_tokens = list(dict.fromkeys(w for w in quote_words if w not in QUOTE_FUNCTION_WORDS)) or quote_words

    speech_terms: list[str] = []
    if mode != 'quote':
        for match in _RE_SPEECH_CLAUSE.finditer(cleaned):
            for tok in terms(match.group(1)):
                if tok not in speech_terms:
                    speech_terms.append(tok)

    number_tokens = [t for t in all_tokens if any(c.isdigit() for c in t)]
    number_phrases = _RE_NUMBER_UNIT.findall(normalize(cleaned))
    number_anchors = list(dict.fromkeys(number_phrases + number_tokens))

    return QueryPlan(
        raw=query,
        mode=mode,
        normalized=normalized,
        retrieval_query=cleaned,
        all_tokens=all_tokens,
        tokens=tokens,
        quote_tokens=quote_tokens[:12],
        embedded_quotes=embedded_quotes,
        has_external_context=has_external_context,
        speech_terms=speech_terms[:16],
        number_anchors=number_anchors[:12],
    )
