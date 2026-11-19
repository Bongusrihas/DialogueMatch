import html
import re
import unicodedata

STOP = set(
    'a an the is are was were be been being am do does did doing have has had having '
    'i me my myself we our ours you your yours he him his she her hers it its they them their theirs '
    'of to in on at for from with without into onto upon by as about after before while during through between under over '
    'and or but if so than then too very just only also even still really quite maybe perhaps probably '
    'that this these those what when where who whom whose which how why '
    'can could would should may might must will shall '
    'some any much many more most other another such own same '
    'scene scenes movie movies film films guy man woman person people someone somebody something anything everything nothing '
    'watching watches watch watched see sees saw seen look looks looking '
    'find finding show shows showing tell tells telling remember remembered recall '
    'trying try tried know knows knew think thinks thought'.split()
)

# Contraction map aligned across raw SRT subtitles, exported V3 chunks, and user queries.
CONTRACTIONS = {
    "can't": "cannot",
    "won't": "will not",
    "shan't": "shall not",
    "i'm": "i am",
    "i've": "i have",
    "i'll": "i will",
    "i'd": "i would",
    "it's": "it is",
    "that's": "that is",
    "there's": "there is",
    "here's": "here is",
    "what's": "what is",
    "who's": "who is",
    "where's": "where is",
    "how's": "how is",
    "when's": "when is",
    "he's": "he is",
    "he'd": "he would",
    "he'll": "he will",
    "she's": "she is",
    "she'd": "she would",
    "she'll": "she will",
    "you're": "you are",
    "you've": "you have",
    "you'll": "you will",
    "you'd": "you would",
    "we're": "we are",
    "we've": "we have",
    "we'll": "we will",
    "we'd": "we would",
    "they're": "they are",
    "they've": "they have",
    "they'll": "they will",
    "they'd": "they would",
    "let's": "let us",
}

_RE_TAGS = re.compile(r'<[^>]*>|\{[^}]*\}')
_RE_CONTRACTIONS = re.compile(
    r'\b(' + '|'.join(sorted((re.escape(k) for k in CONTRACTIONS), key=len, reverse=True)) + r')\b'
)
_RE_NT = re.compile(r"n't\b")
_RE_WORDS = re.compile(r'\w+')

# Colon / dash lead-ins introducing the actual remembered scene after meta commentary.
_RE_LEADIN_PREFIX = re.compile(
    r'^(?:[^:]{0,160}\b(?:'
    r'here is (?:what|the (?:specific )?part)|'
    r'goes like this|'
    r'is this one|'
    r'stayed with me|'
    r'part (?:that )?i remember|'
    r'sequence (?:that )?i remember|'
    r'what i (?:can )?(?:still )?(?:picture|remember|recall)|'
    r'all i remember(?: about it)? is(?: that)?|'
    r'from this description'
    r')[^:]{0,40}:\s*)',
    re.IGNORECASE,
)

# Inline question prefixes like "What's the name of the movie where a boy..."
_RE_INLINE_QUESTION_PREFIX = re.compile(
    r'^(?:hey\s+)?(?:do you (?:recall|remember|know)|does anyone (?:recall|remember|know)|'
    r'(?:what(?:\'s|’s|\s+is|\s+was)|which\s+(?:is|was)) (?:the (?:name|title) of )?(?:the|this|that|a|an) (?:[a-z-]+\s+){0,3}?(?:movie|film|scene)'
    r'(?:\s+that came out[^,.!?]{0,35})?)\s+(?:where|about|in which|when)\s+',
    re.IGNORECASE,
)

# Standalone meta-request / memory-disclaimer sentences that carry zero scene content.
_BOILERPLATE_FULL = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"(?:ok(?:ay)?[,.!\s]+)?i (?:cannot|can't|do not|don't) remember (?:the|its) (?:title|name)(?: or who directed it)?[.!?…]*",
        r"(?:which|what) (?:movie|film)(?: and scene)? (?:was|is) (?:that|this)[?!.…]*",
        r"does anyone know (?:the (?:name|title) of )?(?:this|that) (?:movie|film)[?!.…]*",
        r"can you (?:find the moment and tell me the movie|locate the scene(?: from this description)?|help me(?: find (?:this|it))?)[?!.…]*",
        r"(?:please|pls)?\s*help(?:\s+me)?(?:\s+remember(?:\s+the\s+name\s+of\s+this\s+(?:movie|film))?)?[!?.…]*",
        r"(?:any ideas|anyone|thanks|thank you)[!?.…]*",
        r"i(?:'m| am)?\s*(?:cannot|can't)\s+remember\s+to\s+save\s+my\s+life[!?.…]*",
        r"(?:my [a-z]+ and i are |i am )?dying trying to remember[.!?…]*",
        r"i (?:have been|have|am|was) trying to (?:remember|find|track down) (?:this|a|the) (?:movie|film)(?: (?:for (?:a while|years|months)|from a conversation i remember))?(?:\s+and i only remember one part clearly)?[.!?…]*",
        r"i (?:do not|don't|cannot|can't) remember (?:the title|its name)(?: or who directed it)?[.!?…]*",
        r"(?:some )?small details (?:could|might|may) be wrong,?\s+and i (?:cannot|can't) give you the year or the name of the (?:lead )?actor[.!?…]*",
        r"i (?:cannot|can't) place the title,?\s+and i would rather not guess an actor or a year because i (?:may|might) be mixing those up with another (?:film|movie)[.!?…]*",
        r"i remember the (?:events|situation)(?: and the people arguing)? much better than the (?:actors' names|exact wording)[.!?…]*",
        r"the images are much clearer in my head than the names of the people[.!?…]*",
        r"this has been stuck in my head and my previous searches have not helped[.!?…]*",
        r"i searched a few times without finding it,?\s+and i would appreciate a match based on the events i describe[.!?…]*",
        r"i (?:cannot|can't) give an exact line of dialogue,?\s+but here is the specific part that has stayed with me[.!?…]*",
        r"i watched (?:it|this(?: movie| film)?) (?:at home )?(?:a (?:long time|few years|couple of years) ago|years ago|on (?:netflix|hbo|tv|television)(?:[^.!?]{0,25})?)(?:,?\s+so i am unsure about the release year,?\s+the actors,?\s+and whether i saw the whole thing)?[.!?…]*",
        r"i (?:might|may) have seen this on (?:television|tv),?\s+but i am not confident about when[.!?…]*",
        r"i(?:'m| am) not sure (?:if it was a movie or (?:t\.?v\.?|television) show|that(?:'s| is) when the movie came out)[.!?…]*",
        r"i would have seen this within the last (?:few|five|ten|\d+) years[.!?…]*",
        r"i remember seeing it on (?:hbo|netflix|tv|television),?\s+not much else[.!?…]*",
        r"it was in (?:color|english),?\s+and (?:was )?(?:in )?(?:english|color)[.!?…]*",
        r"(?:[\.…\s]*)?(?:and )?that(?:'s| is) (?:really )?all i (?:can remember(?: of it)?|have to go on)[.!?…]*",
        r"that is not the entire premise of the (?:movie|film|movie/show)[,\s]+just the part (?:that )?i (?:can )?remember[.!?…]*",
        r"i only remember the trailer not the movie so there may be more to it(?: of course)?[.!?…]*",
        r"(?:ok(?:ay)?[,\s]+(?:so )?)?i remember nothing useful (?:about|bout) this (?:movie|film)(?: at all)? aside from this scene[.!?…]*",
        r"sorry for the little amount i could tell you(?: but thank you to those who can figure it out)?[.!?…]*",
        r"a friend is asking me,?\s+but it(?:'s| is) not my genre[.!?…]*",
        r"i want that exact scene,?\s+not another conversation(?: about [a-z]+)?[.!?…]*",
        r"i watched this years ago and (?:cannot|can't) remember its name[.!?…]*",
    ]
]


def normalize(text):
    text = html.unescape(unicodedata.normalize('NFKC', str(text))).casefold()
    text = text.replace('’', "'").replace('‘', "'")
    text = _RE_TAGS.sub(' ', text)
    text = _RE_CONTRACTIONS.sub(lambda m: CONTRACTIONS[m.group(0)], text)
    text = _RE_NT.sub(' not', text)
    return ' '.join(_RE_WORDS.findall(text))


def terms(text):
    return list(dict.fromkeys(w for w in normalize(text).split() if w not in STOP))


def _is_meta_sentence(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return True
    # Never strip a sentence containing an explicit 4-digit year or literal quotation.
    if re.search(r'\b(?:19\d{2}|20\d{2})\b', s):
        return False
    if re.search(r'["“][^"”]{4,}["”]', s):
        return False
    folded = s.replace('’', "'").replace('‘', "'").strip()
    return any(pattern.fullmatch(folded) for pattern in _BOILERPLATE_FULL)


def search_content(text):
    """Remove standalone search-request preambles and meta-commentary while retaining all scene clues."""
    raw = str(text).strip()
    if not raw:
        return raw
    sentences = re.split(r'(?<=[.!?])\s+', raw)
    kept = []
    for sentence in sentences:
        cleaned = _RE_LEADIN_PREFIX.sub('', sentence).strip()
        if not cleaned or _is_meta_sentence(cleaned):
            continue
        cleaned = _RE_INLINE_QUESTION_PREFIX.sub('', cleaned).strip()
        if cleaned and not _is_meta_sentence(cleaned):
            kept.append(cleaned)
    return ' '.join(kept) if kept else raw


def timestamp(seconds):
    seconds = max(0, int(seconds))
    return f'{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}'
