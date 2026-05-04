-- Draw rate vs opponent strength band (rapid)
-- High draw_pct vs stronger opponents = solid defense; vs weaker = missed wins
SELECT
  CASE
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) < -100 THEN '1. Much weaker  (<-100)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) <= 100  THEN '2. Similar      (±100)'
    ELSE                                                                             '3. Stronger     (>+100)'
  END AS band,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) AS draws,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'draw' THEN 1 ELSE 0 END) / COUNT(*), 1) AS draw_pct,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = 'rathnakaragn' OR black = 'rathnakaragn')
  AND time_class = 'rapid' AND color IS NOT NULL AND user_result IS NOT NULL
  AND white_elo IS NOT NULL AND black_elo IS NOT NULL
GROUP BY band
ORDER BY band
