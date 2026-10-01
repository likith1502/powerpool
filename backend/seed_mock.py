"""Seeds a MOCK database so Member B can work before Member A's real data lands.
Run:  python -m backend.seed_mock
Member A's generator later overwrites these tables with real data (same columns).
"""
import math, random
from .db import get_conn, init_db
from .config import FEEDER_CAPACITY_KW, SLOTS_PER_DAY

# Note: random.seed() is called inside seed() so repeated calls are deterministic.
NAMES = ["Sharma", "Reddy", "Khan", "Rao", "Iyer", "Naidu", "Das", "Patel", "Goud", "Verma"]
LANGS = ["en", "hi", "te"]
FLEX = [  # name, kW, duration slots, earliest, latest, usual (evening peak)
    ("Washing machine", 0.5, 4, 36, 68, 78),
    ("Water pump", 0.75, 2, 24, 64, 76),
    ("Inverter charging", 0.3, 8, 36, 64, 80),
    ("Geyser", 2.0, 2, 20, 60, 74),
    ("Iron", 1.0, 2, 36, 68, 80),
    ("E-rickshaw charging", 1.5, 12, 36, 68, 76),
]


def demand_curve():
    out = []
    for s in range(SLOTS_PER_DAY):
        h = s / 4
        base = 75 + 25 * math.exp(-((h - 8) ** 2) / 4) + 121 * math.exp(-((h - 20) ** 2) / 3)
        out.append(base)
    return out


def solar_curve(peak=90):
    return [max(0.0, peak * math.sin(math.pi * (s / 4 - 6) / 12)) if 24 <= s <= 72 else 0.0
            for s in range(SLOTS_PER_DAY)]


def seed(n_households=80, date="2026-10-01"):
    random.seed(42)   # always produce the same households regardless of call order
    init_db()
    with get_conn() as c:
        for t in ("households", "appliances", "forecast", "nudges"):
            c.execute(f"DELETE FROM {t}")
        aid = 1
        for i in range(1, n_households + 1):
            hh_id = f"HH{i:03d}"
            htype = random.choices(["low", "mid", "shop"], [0.5, 0.4, 0.1])[0]
            c.execute("INSERT INTO households VALUES (?,?,?,?,?,0)",
                      (hh_id, f"{random.choice(NAMES)} #{i}", htype,
                       f"Block {chr(65 + i % 4)}", random.choice(LANGS)))
            for a in random.sample(FLEX, k=3 if htype == "low" else 4):
                usual = a[5] + random.randint(-2, 2)
                c.execute("INSERT INTO appliances VALUES (?,?,?,?,?,1,?,?,?)",
                          (aid, hh_id, a[0], a[1], a[2], a[3], a[4], usual))
                aid += 1
        d, sol = demand_curve(), solar_curve()
        for s in range(SLOTS_PER_DAY):
            ts = f"{date}T{s // 4:02d}:{(s % 4) * 15:02d}:00"
            gap = d[s] - sol[s] - FEEDER_CAPACITY_KW
            c.execute("INSERT INTO forecast VALUES (?,?,?,?,?,?)",
                      (ts, round(d[s], 2), round(sol[s], 2), FEEDER_CAPACITY_KW,
                       round(gap, 2), int(gap > 0)))
    print(f"Seeded {n_households} households, {aid - 1} appliances, 96 forecast slots")


if __name__ == "__main__":
    seed()
