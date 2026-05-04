-- Session fatigue: win rate by game number within a sitting (rapid)
-- A new session starts when gap between games > 60 minutes
-- Declining win_pct = fatigue; stable = good stamina
WITH with_gaps AS (
  SELECT end_time, user_result,
         LAG(end_time) OVER (ORDER BY end_time) AS prev_time
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = 'rapid' AND user_result IS NOT NULL AND end_time IS NOT NULL
),
with_sessions AS (
  SELECT end_time, user_result,
         SUM(CASE WHEN prev_time IS NULL OR end_time - prev_time > 3600 THEN 1 ELSE 0 END)
           OVER (ORDER BY end_time) AS session_id
  FROM with_gaps
),
with_game_num AS (
  SELECT user_result,
         ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY end_time) AS game_num
  FROM with_sessions
),
bucketed AS (
  SELECT user_result,
         CASE WHEN game_num >= 5 THEN 5 ELSE game_num END AS bucket
  FROM with_game_num
)
SELECT
  CASE bucket WHEN 5 THEN '5+ (deep session)' ELSE 'Game ' || CAST(bucket AS VARCHAR) END AS game_in_session,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM bucketed
GROUP BY bucket
ORDER BY bucket
