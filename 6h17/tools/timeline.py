"""Ancrage du montage sur les horodatages de la voix (words.json)."""
import json, re, unicodedata


def norm(w):
    w = w.lower().replace("’", "'")
    return re.sub(r"[^\w' -]", "", w).strip()


class Words:
    def __init__(self, path):
        self.words = json.load(open(path, encoding="utf-8"))
        self.n = [norm(x["w"]) for x in self.words]

    def at(self, word, occ=1, end=False):
        """Début (ou fin) de la n-ième occurrence d'un mot."""
        k = 0
        for i, w in enumerate(self.n):
            if w == norm(word):
                k += 1
                if k == occ:
                    return self.words[i]["e" if end else "s"]
        raise KeyError(f"mot introuvable: {word} #{occ}")

    @property
    def end(self):
        return self.words[-1]["e"]
