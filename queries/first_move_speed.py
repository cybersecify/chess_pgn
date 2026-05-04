"""First move response time vs win rate — impulsive openers vs deliberate ones.
Run: .venv/bin/python queries/first_move_speed.py
"""
import re
import duckdb
from collections import defaultdict

DB = "data/rathnakaragn.duckdb"
USERNAME = "rathnakaragn"

CLK_RE = re.compile(r'\[%clk (\d+):(\d{2}):(\d{2}(?:\.\d+)?)\]')

def clk_to_secs(h, m, s):
    return int(h) * 3600 + int(m) * 60 + float(s)

conn = duckdb.connect(DB, read_only=True)
rows = conn.execute("""
    SELECT pgn, color, user_result, time_control
    FROM games
    WHERE (white = ? OR black = ?)
      AND time_class = 'rapid' AND color IS NOT NULL
      AND user_result IS NOT NULL AND pgn IS NOT NULL
      AND time_control NOT LIKE '%/%'
""", [USERNAME, USERNAME]).fetchall()
conn.close()

buckets = defaultdict(lambda: {"win": 0, "lose": 0, "draw": 0, "total": 0})

for pgn, color, result, tc in rows:
    m = re.match(r'^(\d+)', tc or '')
    if not m:
        continue
    initial = int(m.group(1))

    clocks = [(clk_to_secs(h, mi, s)) for h, mi, s in CLK_RE.findall(pgn)]
    if not clocks:
        continue

    # First clock for this player
    first_clk = clocks[0] if color == 'white' else (clocks[1] if len(clocks) > 1 else None)
    if first_clk is None:
        continue

    secs_spent = max(0.0, initial - first_clk)

    if secs_spent < 2:
        bucket = "< 2s  (instant)"
    elif secs_spent < 5:
        bucket = "2-5s  (quick)"
    elif secs_spent < 15:
        bucket = "5-15s (considered)"
    elif secs_spent < 30:
        bucket = "15-30s (slow start)"
    else:
        bucket = "30s+  (very slow)"

    buckets[bucket]["total"] += 1
    buckets[bucket][result if result in ("win", "lose", "draw") else "draw"] += 1

order = ["< 2s  (instant)", "2-5s  (quick)", "5-15s (considered)", "15-30s (slow start)", "30s+  (very slow)"]

print(f"\n{'First move time':<22}  {'Games':>6}  {'Wins':>6}  {'Win%':>6}")
print("-" * 50)
for b in order:
    if b not in buckets:
        continue
    d = buckets[b]
    pct = d["win"] / d["total"] * 100 if d["total"] else 0
    print(f"{b:<22}  {d['total']:>6}  {d['win']:>6}  {pct:>5.1f}%")
