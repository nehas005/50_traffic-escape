import json
import os
from datetime import datetime

MAX_ENTRIES = 5
DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "highscores.json")


class HighScores:
    """Top-5 table persisted to JSON so it survives between sessions."""

    def __init__(self, path=DEFAULT_PATH):
        self.path = path
        self.entries = self.load()

    def load(self):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            good = [e for e in data if isinstance(e, dict) and isinstance(e.get("score"), int)]
            return sorted(good, key=lambda e: -e["score"])[:MAX_ENTRIES]
        except (OSError, ValueError, TypeError):
            return []  # missing or corrupt file -> start fresh, never crash

    def save(self):
        try:
            tmp = self.path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.entries, f, indent=2)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def qualifies(self, score):
        return score > 0 and (len(self.entries) < MAX_ENTRIES or score > self.entries[-1]["score"])

    def add(self, score, result):
        """Insert a score. Returns its 0-based rank, or None if it didn't make the top 5."""
        if not self.qualifies(score):
            return None
        entry = {"score": int(score), "result": result,
                 "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
        rank = sum(1 for e in self.entries if e["score"] >= score)  # ties: older entry ranks higher
        self.entries.insert(rank, entry)
        self.entries = self.entries[:MAX_ENTRIES]
        self.save()
        return rank
