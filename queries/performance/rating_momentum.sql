-- Rolling 10-game win rate over time (rapid) — shows hot and cold streaks
WITH ordered AS (
  SELECT
    strftime(to_timestamp(end_time), '%Y-%m-%d') AS date,
    user_result,
    CASE WHEN color = 'white' THEN white_elo ELSE black_elo END AS my_elo,
    ROW_NUMBER() OVER (ORDER BY end_time) AS rn
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = 'rapid' AND user_result IS NOT NULL AND end_time IS NOT NULL
)
SELECT
  date,
  my_elo,
  ROUND(
    100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END)
            OVER (ORDER BY rn ROWS BETWEEN 9 PRECEDING AND CURRENT ROW)
    / 10.0, 0
  ) AS rolling_10_win_pct
FROM ordered
ORDER BY rn DESC
LIMIT 50
