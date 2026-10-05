"""Métricas por técnica. Todas las técnicas se miden igual.

Dos correcciones de sesgo:
  - "T. penal.": tiempo medio sobre TODAS las corridas, contando cada fallo como EPISODE_TIMEOUT.
    "T. alcance" solo promedia los éxitos y favorece a técnicas que solo resuelven casos fáciles.
  - Comparación por pares: en el laboratorio cada objetivo lo corren todas las técnicas, así que
    se puede contar en cuántos objetivos A llega antes que B (mismas condiciones exactas).
"""
from dataclasses import dataclass

from .config import EPISODE_TIMEOUT

HEADERS = ["Técnica", "Corridas", "Alcanza %", "T. alcance (s)", "T. penal. (s)", "Pasos", "Nodos/dec", "ms/dec"]


@dataclass
class TechniqueStats:
    episodes: int = 0
    captures: int = 0
    capture_time: float = 0.0
    penal_time: float = 0.0
    capture_steps: int = 0
    decisions: int = 0
    expanded: int = 0
    cpu_ms: float = 0.0

    def row(self, name):
        cap, ep = self.captures, self.episodes
        return [
            name,
            str(ep),
            f"{100 * cap / ep:.0f}%" if ep else "-",
            f"{self.capture_time / cap:.2f}" if cap else "-",
            f"{self.penal_time / ep:.2f}" if ep else "-",
            f"{self.capture_steps / cap:.1f}" if cap else "-",
            f"{self.expanded / self.decisions:.1f}" if self.decisions else "-",
            f"{self.cpu_ms / self.decisions:.3f}" if self.decisions else "-",
        ]


class Metrics:
    def __init__(self, names):
        self.names = list(names)
        self.stats = {n: TechniqueStats() for n in names}
        self.by_target = {}          # índice de objetivo -> {técnica: tiempo penalizado}

    def record_decision(self, name, decision):
        s = self.stats[name]
        s.decisions += 1
        s.expanded += decision.expanded
        s.cpu_ms += decision.cpu_ms

    def record_episode(self, name, captured, t, steps, target=None):
        s = self.stats[name]
        s.episodes += 1
        s.penal_time += t if captured else EPISODE_TIMEOUT
        if captured:
            s.captures += 1
            s.capture_time += t
            s.capture_steps += steps
        if target is not None:
            self.by_target.setdefault(target, {})[name] = t if captured else EPISODE_TIMEOUT

    def rows(self):
        return [s.row(n) for n, s in self.stats.items()]

    # ---------- comparación por pares ----------
    def pairwise(self):
        """win[a][b] = % de objetivos compartidos donde a llega estrictamente antes que b.

        Un fallo cuenta como EPISODE_TIMEOUT, así que si ambos fallan es empate.
        Devuelve (win, n) con n[a][b] = objetivos que ambas técnicas corrieron.
        """
        win = {a: {} for a in self.names}
        n = {a: {} for a in self.names}
        for a in self.names:
            for b in self.names:
                shared = [r for r in self.by_target.values() if a in r and b in r]
                n[a][b] = len(shared)
                if a != b and shared:
                    win[a][b] = 100 * sum(r[a] < r[b] - 1e-9 for r in shared) / len(shared)
        return win, n

    def as_text(self):
        return _table([HEADERS] + self.rows())

    def pairwise_text(self):
        win, n = self.pairwise()
        head = ["A gana a B (%)"] + self.names
        rows = [[a] + ["—" if a == b else (f"{win[a][b]:.0f}%" if b in win[a] else "-") for b in self.names]
                for a in self.names]
        shared = min((n[a][b] for a in self.names for b in self.names if a != b), default=0)
        return _table([head] + rows) + f"\n(objetivos compartidos por par: {shared}; fallo = {EPISODE_TIMEOUT:.0f} s)"


def _table(rows):
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    fmt = lambda r: "| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    return "\n".join([fmt(rows[0]), sep] + [fmt(r) for r in rows[1:]])
