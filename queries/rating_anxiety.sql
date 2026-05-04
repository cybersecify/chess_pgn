-- Rating anxiety: win rate near rating milestones (every 50 points) vs away from them
-- Players often choke within 10 points of a round number (700, 750, 800 etc)
WITH my_elo AS (
  SELECT end_time, user_result,
         CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS elo
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = 'rapid' AND user_result IS NOT NULL
    AND white_elo IS NOT NULL AND black_elo IS NOT NULL AND color IS NOT NULL
),
with_zone AS (
  SELECT user_result, elo,
         elo % 50 AS mod50,
         (elo / 50) * 50 AS nearest_milestone
  FROM my_elo
)
SELECT
  CASE
    WHEN mod50 >= 40 THEN 'Near milestone (40-49: approaching)'
    WHEN mod50 <= 10 THEN 'Near milestone (0-10: just crossed)'
    ELSE                  'Away from milestone (11-39)'
  END AS zone,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM with_zone
GROUP BY zone
ORDER BY zone
