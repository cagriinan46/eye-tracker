"""Gaze-keyboard text state and Turkish word suggestions.

Independent of camera, GUI and OS APIs: keys arrive as identifiers and the result
is plain text held in memory. Only completed words and their counts enter the optional personal dictionary.
"""

import os
import sqlite3
from bisect import bisect_left
from contextlib import closing
from heapq import nlargest
from pathlib import Path

WORDS_PATH = Path(__file__).parent / "data" / "tr_words.txt"
# Turkish Q layout, including Q, W and X.
LETTER_ROWS = ("qwertyuıopğü", "asdfghjklşi", "zxcvbnmöç")
SYMBOL_ROWS = ("1234567890-_", "@()'\"/+=%&*", ",?!:;#<>₺")
SUGGESTION_SLOTS = 4
SENTENCE_END = ".!?"
CLOSING_PUNCTUATION = ".,!?:;"
TARGET_TEXT = "Bugün hava çok güzel."
# Row/column identifiers stay the same on both pages, so gaze regions do too.
CHARACTER_KEYS = tuple(
    f"r{row}c{column}" for row, letters in enumerate(LETTER_ROWS) for column in range(len(letters))
)
SUGGESTION_KEYS = tuple(f"sug{slot}" for slot in range(SUGGESTION_SLOTS))
CONTROL_KEYS = ("backspace", "page", "shift", "space", "period", "delete_word")
KEY_IDS = frozenset(CHARACTER_KEYS + SUGGESTION_KEYS + CONTROL_KEYS)
_LOWER = str.maketrans("Iİ", "ıi")
_UPPER = str.maketrans("ıi", "Iİ")


def turkish_lower(text):
    return text.translate(_LOWER).lower()


def turkish_upper(text):
    return text.translate(_UPPER).upper()


def is_word_character(character):
    return character.isalpha() or character == "'"


class Suggester:
    """Rank prefix completions by personal usage, then corpus frequency."""

    def __init__(self, entries, personal_path=None):
        best = {}
        for word, count in entries:
            word = turkish_lower(word)
            best[word] = max(count, best.get(word, 0))
        self.words = sorted(best)
        self.counts = best
        self.common = nlargest(SUGGESTION_SLOTS, best, key=lambda w: (best[w], w))

        self.personal_path = personal_path
        self.personal = {}
        if personal_path is not None and personal_path.is_file():
            try:
                with closing(sqlite3.connect(personal_path)) as db:
                    self.personal = dict(db.execute("SELECT word, uses FROM vocabulary"))
            except sqlite3.Error:
                pass

    def remember(self, word):
        word = turkish_lower(word)
        if self.personal_path is None or not (1 <= len(word) <= 64):
            return
        if not all(part.isalpha() for part in word.split("'")):
            return
        try:
            self.personal_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.close(os.open(self.personal_path, os.O_CREAT | os.O_WRONLY, 0o600))
            with closing(sqlite3.connect(self.personal_path, timeout=0.1)) as db, db:
                db.execute(
                    "CREATE TABLE IF NOT EXISTS vocabulary "
                    "(word TEXT PRIMARY KEY, uses INTEGER NOT NULL)"
                )
                db.execute(
                    "INSERT INTO vocabulary VALUES (?, 1) ON CONFLICT(word) "
                    "DO UPDATE SET uses = uses + 1",
                    (word,),
                )
                db.execute(
                    "DELETE FROM vocabulary WHERE word IN (SELECT word FROM vocabulary "
                    "ORDER BY uses DESC, rowid DESC LIMIT -1 OFFSET 1024)"
                )
                counts = dict(db.execute("SELECT word, uses FROM vocabulary"))
            self.personal = counts
        except (OSError, sqlite3.Error):
            # An unavailable dictionary must never interrupt text entry.
            pass

    @classmethod
    def from_file(cls, path=WORDS_PATH, personal_path=None):
        entries = []
        for line in path.read_text(encoding="utf-8").splitlines():
            word, _, count = line.partition(" ")
            if word and count.isdigit():
                entries.append((word, int(count)))
        return cls(entries, personal_path)

    def suggest(self, prefix, limit=SUGGESTION_SLOTS):
        prefix = turkish_lower(prefix)
        personal = self.personal
        learned = [w for w in personal if w.startswith(prefix) and w != prefix]
        favorites = nlargest(limit, learned, key=lambda w: (personal[w], self.counts.get(w, 0), w))
        if len(favorites) == limit:
            return favorites
        if not prefix:
            return (favorites + [w for w in self.common if w not in personal])[:limit]
        start = bisect_left(self.words, prefix)
        end = bisect_left(self.words, prefix + "\U0010ffff")
        matches = [w for w in self.words[start:end] if w != prefix and w not in personal]
        return favorites + nlargest(
            limit - len(favorites), matches, key=lambda w: (self.counts[w], w)
        )


class Keyboard:
    def __init__(self, suggester=None, target=TARGET_TEXT):
        self.suggester = suggester
        self.target = target
        self.suggestions_on = True  # Set from the application settings, not by a key.
        self.reset()

    def reset(self):
        self.text = ""
        self.page = "letters"
        self.shift = True  # A new text starts with a capital letter.
        self.auto_space = False
        self.started = self.last_key = self.completed_s = None
        self.counts = dict(gaze=0, manual=0, backspace=0, delete_word=0, suggestion=0)

    @property
    def rows(self):
        rows = LETTER_ROWS if self.page == "letters" else SYMBOL_ROWS
        if self.page == "letters" and self.shift:
            return [[turkish_upper(c) for c in row] for row in rows]
        return [list(row) for row in rows]

    @property
    def current_word(self):
        end = len(self.text)
        start = end
        while start and is_word_character(self.text[start - 1]):
            start -= 1
        return self.text[start:end]

    @property
    def suggestions(self):
        if not self.suggestions_on or self.suggester is None:
            return []
        word = self.current_word
        found = self.suggester.suggest(word)
        if word[:1] != turkish_lower(word[:1]) or (not word and self.shift):
            found = [turkish_upper(w[0]) + w[1:] for w in found]
        return found

    def press(self, key, now, modality="gaze"):
        """Apply one key. Returns False for an unknown or currently empty key."""
        if key not in KEY_IDS or modality not in ("gaze", "manual"):
            return False
        if key in SUGGESTION_KEYS:
            options = self.suggestions
            slot = SUGGESTION_KEYS.index(key)
            if slot >= len(options):
                return False
            self.text = self.text[: len(self.text) - len(self.current_word)] + options[slot] + " "
            self.suggester.remember(options[slot])
            self.auto_space = True
            self.counts["suggestion"] += 1
        elif key in CHARACTER_KEYS:
            row, column = int(key[1]), int(key[3:])
            if column >= len(self.rows[row]):
                return False
            self._insert(self.rows[row][column])
        elif key == "period":
            self._insert(".")
        elif key == "space":
            self._insert(" ")
        elif key == "backspace":
            self.text = self.text[:-1]
            self.auto_space = False
            self.counts["backspace"] += 1
        elif key == "delete_word":
            kept = self.text.rstrip(" ")
            self.text = kept[: len(kept) - len(Keyboard._last_word(kept))]
            self.auto_space = False
            self.counts["delete_word"] += 1
        elif key == "page":
            self.page = "symbols" if self.page == "letters" else "letters"
        elif key == "shift":
            self.shift = not self.shift
        self.counts[modality] += 1
        if key not in ("shift", "page"):
            self.shift = not self.text or self.text.rstrip(" ")[-1:] in SENTENCE_END
            if self.text and self.started is None:
                self.started = now
            self.last_key = now
        if self.completed_s is None and self.started is not None and self.text == self.target:
            self.completed_s = now - self.started
        return True

    @staticmethod
    def _last_word(text):
        start = len(text)
        while start and not text[start - 1].isspace():
            start -= 1
        return text[start:]

    def _insert(self, character):
        if not is_word_character(character) and self.suggestions_on and self.suggester:
            self.suggester.remember(self.current_word)
        # A space added by a suggestion gives way to closing punctuation.
        if self.auto_space and character in CLOSING_PUNCTUATION and self.text.endswith(" "):
            self.text = self.text[:-1]
        self.auto_space = False
        self.text += character

    def stats(self):
        """Counts and timing only; the typed text is never part of a record.

        Time runs from the first character to the latest text key, or to the
        moment the target sentence was completed.
        """
        elapsed = self.completed_s
        if elapsed is None and self.started is not None:
            elapsed = self.last_key - self.started
        return dict(
            self.counts,
            characters=len(self.text),
            elapsed_s=elapsed,
            # Five characters per word; no rate until a second of typing exists.
            words_per_minute=len(self.text) / 5 / (elapsed / 60)
            if elapsed is not None and elapsed >= 1
            else None,
            target_completed_s=self.completed_s,
            target_characters=len(self.target),
            suggestions_on=self.suggestions_on,
        )

    def snapshot(self):
        options = self.suggestions
        return dict(
            text=self.text,
            rows=self.rows,
            page=self.page,
            shift=self.shift,
            suggestions_on=self.suggestions_on,
            suggestions=options + [""] * (SUGGESTION_SLOTS - len(options)),
            target=self.target,
            stats=self.stats(),
        )
