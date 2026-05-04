-- Performance vs opponent rating bands (rapid)
SELECT
  CASE
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) < -200 THEN '1. Much weaker   (<-200)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) < -100 THEN '2. Weaker      (-200 to -100)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) <= 100 THEN '3. Similar     (-100 to +100)'
    WHEN (CASE WHEN color = 'white' THEN black_elo ELSE white_elo END) -
         (CASE WHEN color = 'white' THEN white_elo ELSE black_elo END) <= 200 THEN '4. Stronger    (+100 to +200)'
    ELSE                                                                            '5. Much stronger  (>+200)'
  END AS band,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) AS wins,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM games
WHERE (white = $USERNAME OR black = $USERNAME)
  AND time_class = 'rapid' AND color IS NOT NULL
  AND white_elo IS NOT NULL AND black_elo IS NOT NULL
GROUP BY band
ORDER BY band
