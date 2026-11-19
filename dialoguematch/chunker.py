import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from functools import lru_cache

# ─────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────

MIN_WORDS_KEEP = 3  # chunks below this word count are discarded
SILENCE_THRESHOLD = 5.0  # seconds gap  → hard scene boundary
SOFT_GAP_THRESHOLD = 2.0  # seconds gap  → split only if also over soft word limit
MAX_CHUNK_SEC = 100.0  # hard ceiling → force split even mid-scene
MIN_CHUNK_SEC = 20.0  # floor        → merge tiny chunks upward
WORD_HARD_LIMIT = 145  # always split here regardless of gap
WORD_SOFT_LIMIT = 110  # split here only if gap >= SOFT_GAP_THRESHOLD
OVERLAP_WORDS = 15  # perfect, keep

# ─────────────────────────────────────────────────────────────
# DATA STRUCTURES
# ─────────────────────────────────────────────────────────────


@dataclass
class RawSubtitle:
    """One parsed SRT block."""

    index: int
    start: float  # seconds
    end: float  # seconds
    raw_text: str
    is_music: bool = False  # FIX #9: flag music/sfx lines before text cleaning


@dataclass
class SceneChunk:
    """One processed scene chunk — ready for enrichment & embedding."""

    chunk_id: str
    movie_id: str
    start_time: float
    end_time: float
    duration: float
    text: str  # cleaned, normalized
    word_count: int
    line_count: int
    split_reason: str
    overlap_text: str = ""  # last N words of previous chunk
    raw_text: str = ""
    subtitle_lines: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        dictd = asdict(self)
        dictd["_id"] = dictd.pop("chunk_id")

        return dictd


# ─────────────────────────────────────────────────────────────
# TIMESTAMP PARSER
# ─────────────────────────────────────────────────────────────


def _ts_to_sec(ts: str) -> float:
    """'01:23:45,678'  →  float seconds."""
    ts = ts.strip().replace(",", ".").replace("\u066b", ".")
    parts = ts.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(ts)


# ─────────────────────────────────────────────────────────────
# SRT PARSER  (fixes #1, #2, #3, #9)
# ─────────────────────────────────────────────────────────────

# FIX #9: detect music/sfx BEFORE any cleaning
_RE_IS_MUSIC = re.compile(r"[♪♫]|^\s*\[[^\]]{1,40}\]\s*$|^\s*\([^)]{1,40}\)\s*$")


def _line_is_music(text: str) -> bool:
    return bool(_RE_IS_MUSIC.search(text))


def parse_srt(path: str | Path) -> list[RawSubtitle]:
    path = Path(path)

    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            content = path.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"Cannot decode file: {path}")

    content = content.replace("\r\n", "\n").replace("\r", "\n")

    # FIX #2: do NOT strip [brackets] from raw content here — they carry
    # subtitle text like [Man laughing]. Only strip file-level metadata headers
    # that appear at the very top before any timecode (e.g. [INFORMATION] blocks).
    content = re.sub(
        r"^\s*\[[A-Z ]{3,}\]\s*\n(?:[^\n]*\n)*?\n", "", content, flags=re.MULTILINE
    )

    lines = [l.strip() for l in content.split("\n") if l.strip()]

    subtitles: list[RawSubtitle] = []
    idx = 1

    TIME_STD = re.compile(
        r"(\d{1,2}:\d{2}:\d{2}[,.\u066b]\d{1,3})"
        r"(?:\s*-->\s*|\s*,\s*)"
        r"(\d{1,2}:\d{2}:\d{2}[,.\u066b]\d{1,3})"
    )
    # FIX #1: removed unused TIME_ASS — ASS handled entirely by Dialogue: branch below

    i = 0
    while i < len(lines):
        line = lines[i]

        # ── CASE 0: SMI / SAMI ─────────────────────────
        if "<SYNC" in line.upper():
            match = re.search(r"Start\s*=\s*(\d+)", line, re.I)
            if match:
                start = int(match.group(1)) / 1000.0
                text_match = re.search(r"<P[^>]*>(.*)", line, re.I)
                text = text_match.group(1) if text_match else ""
                text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
                text = re.sub(r"<[^>]+>", "", text).strip()

                end = start + 2.0
                j = i + 1
                while j < len(lines):
                    nm = re.search(r"<SYNC[^>]*Start\s*=\s*(\d+)", lines[j], re.I)
                    if nm:
                        end = int(nm.group(1)) / 1000.0
                        break
                    j += 1

                if text:
                    subtitles.append(
                        RawSubtitle(
                            index=idx,
                            start=start,
                            end=end,
                            raw_text=text,
                            is_music=_line_is_music(text),
                        )
                    )
                    idx += 1
            i += 1
            continue

        # ── CASE 1: ASS / SSA ──────────────────────────
        if line.startswith("Dialogue:"):
            parts = line.split(",")
            if len(parts) >= 3:
                try:
                    start = _ts_to_sec(parts[1])
                    end = _ts_to_sec(parts[2])
                except (ValueError, IndexError):
                    i += 1
                    continue
                text = ",".join(parts[9:]) if len(parts) > 9 else parts[-1]
                text = text.strip()
                if text:
                    subtitles.append(
                        RawSubtitle(
                            index=idx,
                            start=start,
                            end=end,
                            raw_text=text,
                            is_music=_line_is_music(text),
                        )
                    )
                    idx += 1
            i += 1
            continue

        # ── CASE 2: SRT / BROKEN / COMMA ───────────────
        match = TIME_STD.search(line)
        if match:
            start = _ts_to_sec(match.group(1))
            end = _ts_to_sec(match.group(2))
            i += 1
            text_lines = []

            while i < len(lines):
                next_line = lines[i]
                # FIX #3: skip pure index number lines
                if next_line.isdigit() and i + 1 < len(lines) and TIME_STD.search(lines[i + 1]):
                    i += 1
                    break
                if TIME_STD.search(next_line) or next_line.startswith("Dialogue:"):
                    break
                text_lines.append(next_line)
                i += 1

            text = "\n".join(text_lines).strip()
            if text:
                subtitles.append(
                    RawSubtitle(
                        index=idx,
                        start=start,
                        end=end,
                        raw_text=text,
                        is_music=_line_is_music(text),
                    )
                )
                idx += 1
            continue

        i += 1

    subtitles = [s for s in subtitles if 0 <= s.start < s.end]
    subtitles.sort(key=lambda s: s.start)
    return subtitles


# ─────────────────────────────────────────────────────────────
# TEXT CLEANING  (fix #10: removed double-wipe of [brackets])
# ─────────────────────────────────────────────────────────────

_RE_HTML = re.compile(r"<[^>]+>")
_RE_SSA = re.compile(r"\{[^}]+\}")
_RE_MUSIC_BLOCK = re.compile(r"♪[^♪]*♪|♫[^♫]*♫")
_RE_MUSIC_NOTE = re.compile(r"[♪♫🎵🎶]")
_RE_BRACKET_SFX = re.compile(r"\[[^\]]{1,40}\]")
_RE_PAREN_SFX = re.compile(r"\([^)]{1,40}\)")
_RE_SPEAKER = re.compile(r"^[A-Z][A-Z\s'\.]{1,25}:\s*")
_RE_NARRATOR = re.compile(r"^\[?NARRATOR\]?:?\s*", re.I)
_RE_DASH_LINE = re.compile(r"^[-–—]\s*")
_RE_ELLIPSIS = re.compile(r"\.{2,}")
_RE_MULTI_SPACE = re.compile(r" {2,}")
_RE_MULTI_PUNCT = re.compile(r"([!?]){2,}")

CONTRACTION_MAP = {
    "won't": "will not",
    "can't": "cannot",
    "n't": " not",
    "I'm": "I am",
    "I've": "I have",
    "I'll": "I will",
    "I'd": "I would",
    "you're": "you are",
    "you've": "you have",
    "you'll": "you will",
    "he's": "he is",
    "she's": "she is",
    "it's": "it is",
    "we're": "we are",
    "we've": "we have",
    "they're": "they are",
    "they've": "they have",
    "that's": "that is",
    "there's": "there is",
    "what's": "what is",
    "who's": "who is",
    "let's": "let us",
    "here's": "here is",
}


def _expand_contractions(text: str) -> str:
    for k, v in CONTRACTION_MAP.items():
        text = re.sub(re.escape(k), v, text, flags=re.IGNORECASE)
    return text


@lru_cache(maxsize=32768)
def clean_text(raw: str, expand_contractions: bool = True) -> str:
    text = unicodedata.normalize("NFC", raw)
    text = _RE_HTML.sub(" ", text)
    text = _RE_SSA.sub(" ", text)
    text = _RE_MUSIC_BLOCK.sub(" ", text)
    text = _RE_MUSIC_NOTE.sub(" ", text)
    text = _RE_BRACKET_SFX.sub(
        " ", text
    )  # FIX #10: safe here — raw file already parsed
    text = _RE_PAREN_SFX.sub(" ", text)

    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        line = _RE_NARRATOR.sub("", line)
        line = _RE_SPEAKER.sub("", line)
        line = _RE_DASH_LINE.sub("", line)
        line = line.strip()
        if line:
            cleaned_lines.append(line)

    text = " ".join(cleaned_lines)
    if expand_contractions:
        text = _expand_contractions(text)
    text = _RE_ELLIPSIS.sub(".", text)
    text = _RE_MULTI_PUNCT.sub(r"\1", text)
    text = _RE_MULTI_SPACE.sub(" ", text)
    return text.strip()


def repair_sentences(text: str) -> str:
    text = re.sub(r"([^.!?])\s*\n\s*([a-z])", r"\1 \2", text)
    text = re.sub(r"([.!?])([A-Z])", r"\1 \2", text)
    text = re.sub(r"\s+([.,!?;:])", r"\1", text)
    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
    return text


def process_chunk_text(raw_lines: list[str]) -> str:
    cleaned = [c for line in raw_lines if (c := clean_text(line))]
    joined = " ".join(cleaned)
    repaired = repair_sentences(joined)
    return _RE_MULTI_SPACE.sub(" ", repaired).strip()


# ─────────────────────────────────────────────────────────────
# CHUNK BUILDER
# ─────────────────────────────────────────────────────────────


def _get_overlap_text(text: str, n_words: int = OVERLAP_WORDS) -> str:
    words = text.split()
    return " ".join(words[-n_words:]) if len(words) > n_words else text


def _make_chunk(
    subs: list[RawSubtitle],
    movie_id: str,
    chunk_idx: int,
    split_reason: str,
    prev_text: str = "",
) -> SceneChunk | None:
    if not subs:
        return None

    raw_lines = [s.raw_text for s in subs if s.raw_text]
    text = process_chunk_text(raw_lines)

    if not text:
        return None

    words = text.split()

    start_time = subs[0].start
    end_time = subs[-1].end
    duration = end_time - start_time

    # FIX #7 + #8: actually compute and store overlap
    overlap = _get_overlap_text(prev_text) if prev_text else ""

    return SceneChunk(
        chunk_id=f"{movie_id}_{chunk_idx}",
        movie_id=movie_id,
        start_time=round(start_time, 3),
        end_time=round(end_time, 3),
        duration=round(duration, 3),
        text=text,
        word_count=len(words),
        line_count=len(subs),
        split_reason=split_reason,
        overlap_text=overlap,
        raw_text="\n".join(raw_lines),
        subtitle_lines=[asdict(s) for s in subs],
    )


# ─────────────────────────────────────────────────────────────
# HYBRID CHUNKER  (fixes #4, #5, #6, #9)
# ─────────────────────────────────────────────────────────────


def should_split_on_natural_break(
    current: list[RawSubtitle], next_sub: RawSubtitle
) -> bool:
    """Prefer splitting at sentence end or speaker change when near soft limits."""
    if not current:
        return False
    text_so_far = process_chunk_text([s.raw_text for s in current])
    words = len(text_so_far.split())

    if words < WORD_SOFT_LIMIT - 20:  # still plenty of room
        return False

    last_line = current[-1].raw_text.strip()
    # End of sentence or speaker change
    if re.search(r"[.!?]$", last_line) or re.search(r"^[-–—]", next_sub.raw_text):
        return True
    return False


def hybrid_chunk(
    subtitles: list[RawSubtitle],
    movie_id: str,
    silence_threshold: float = SILENCE_THRESHOLD,
    soft_gap_threshold: float = SOFT_GAP_THRESHOLD,
    max_chunk_sec: float = MAX_CHUNK_SEC,
    min_chunk_sec: float = MIN_CHUNK_SEC,
    word_hard_limit: int = WORD_HARD_LIMIT,
    word_soft_limit: int = WORD_SOFT_LIMIT,
) -> list[SceneChunk]:

    if not subtitles:
        return []

    groups: list[tuple[list[RawSubtitle], str]] = []
    current: list[RawSubtitle] = [subtitles[0]]

    for i in range(1, len(subtitles)):
        prev = subtitles[i - 1]
        curr = subtitles[i]

        gap = curr.start - prev.end
        chunk_dur = curr.end - current[0].start

        # FIX #4: count words from CLEANED text, not raw
        current_text = process_chunk_text([s.raw_text for s in current if s.raw_text])
        word_count = len(current_text.split())

        # FIX #9: music/sfx line acts as a scene boundary signal
        music_break = curr.is_music and gap >= 2.0

        # ── FIX #5: 3-tier gap model with strict priority order ──
        #
        # Priority 1: hard word cap — always split
        next_words = len(process_chunk_text([curr.raw_text]).split())
        if word_count + next_words > word_hard_limit:
            groups.append((current, "word_hard"))
            current = [curr]

        elif chunk_dur >= max_chunk_sec:  # ← move UP
            groups.append((current, "cap"))
            current = [curr]

        elif gap >= silence_threshold:
            groups.append((current, "silence"))
            current = [curr]

        elif word_count >= word_soft_limit and gap >= soft_gap_threshold:
            groups.append((current, "word_soft"))
            current = [curr]
        # Priority 4: music/sfx boundary signal
        elif music_break:
            groups.append((current, "music_boundary"))
            current = [curr]

        elif should_split_on_natural_break(current, curr):
            groups.append((current, "natural_break"))
            current = [curr]

        # Otherwise: keep merging
        else:
            current.append(curr)

    groups.append((current, "eof"))

    # ── Merge short chunks  (FIX #6: merge forward if no prev exists) ──
    merged: list[tuple[list[RawSubtitle], str]] = []

    def can_merge(left, right):
        return (
            right[0].start - left[-1].end < silence_threshold
            and right[-1].end - left[0].start <= max_chunk_sec
            and len(process_chunk_text([s.raw_text for s in left + right]).split()) <= word_hard_limit
            and not (right[0].is_music and right[0].start - left[-1].end >= 2.0)
        )

    for j, (subs, reason) in enumerate(groups):
        if not subs:
            continue
        dur = subs[-1].end - subs[0].start

        if dur < min_chunk_sec:
            if merged and can_merge(merged[-1][0], subs):
                # merge into previous
                prev_subs, prev_reason = merged[-1]
                merged[-1] = (prev_subs + subs, prev_reason + "+merge")
            elif not merged and j + 1 < len(groups) and can_merge(subs, groups[j + 1][0]):
                # FIX #6: no previous — merge into next instead
                next_subs, next_reason = groups[j + 1]
                groups[j + 1] = (subs + next_subs, "merge_fwd+" + next_reason)
            else:
                merged.append((subs, reason))  # only chunk, keep it
        else:
            merged.append((subs, reason))

    # ── Build SceneChunk objects ────────────────────────────
    chunks: list[SceneChunk] = []
    prev_text = ""

    for idx, (subs, reason) in enumerate(merged):
        chunk = _make_chunk(
            subs=subs,
            movie_id=movie_id,
            chunk_idx=idx,
            split_reason=reason,
            prev_text=prev_text,  # FIX #7 + #8: pass prev text for overlap
        )
        if chunk:
            chunks.append(chunk)
            prev_text = chunk.text  # update for next iteration

    return chunks


# ─────────────────────────────────────────────────────────────
# PIPELINE ENTRY POINT
# ─────────────────────────────────────────────────────────────


def process_srt(
    srt_path: str | Path,
    movie_id: str | None = None,
    **kwargs,
) -> list[SceneChunk]:
    path = Path(srt_path)
    if not path.exists():
        raise FileNotFoundError(f"SRT file not found: {path}")

    name = movie_id or path.stem.replace("_", " ").replace(".", " ").title()
    subtitles = parse_srt(path)

    if not subtitles:
        raise ValueError(f"No valid subtitle intervals found in {path}")

    return hybrid_chunk(subtitles, movie_id=name, **kwargs)


# ─────────────────────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────────────────────


def chunks_to_json(chunks: list[SceneChunk], path: str | Path) -> None:
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [c.to_dict() for c in chunks]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(chunks)} chunks → {path}")
