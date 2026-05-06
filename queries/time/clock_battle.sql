-- Clock battle: did you use more or less time than your opponent? (rapid)
-- clock_ratio > 1 = you used more time; < 1 = opponent used more
-- Win rate by who controlled the clock reveals time management style
WITH clock AS (
  SELECT user_result, color,
    CASE WHEN color = 'white'
      THEN ROUND(1.0 * white_time_used_secs / NULLIF(black_time_used_secs, 0), 2)
      ELSE ROUND(1.0 * black_time_used_secs / NULLIF(white_time_used_secs, 0), 2)
    END AS clock_ratio
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS
    AND user_result IS NOT NULL
    AND white_time_used_secs > 30 AND black_time_used_secs > 30
),
bucketed AS (
  SELECT user_result,
    CASE
      WHEN clock_ratio < 0.5  THEN '1. You used much less (<0.5x)'
      WHEN clock_ratio < 0.8  THEN '2. You used less (0.5–0.8x)'
      WHEN clock_ratio < 1.2  THEN '3. Even (0.8–1.2x)'
      WHEN clock_ratio < 2.0  THEN '4. You used more (1.2–2.0x)'
      ELSE                         '5. You used much more (>2.0x)'
    END AS bucket
  FROM clock
  WHERE clock_ratio IS NOT NULL
)
SELECT bucket,
       COUNT(*) AS games,
       SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
       SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
       ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM bucketed
GROUP BY bucket
ORDER BY bucket
