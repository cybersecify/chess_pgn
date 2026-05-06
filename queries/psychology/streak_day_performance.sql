-- Consecutive day streak performance (rapid)
-- Does sustained daily play build momentum or accumulate fatigue?
WITH unique_days AS (
  SELECT DISTINCT strftime(to_timestamp(end_time), '%Y-%m-%d')::DATE AS play_date
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND end_time IS NOT NULL
),
with_prev AS (
  SELECT play_date,
         LAG(play_date) OVER (ORDER BY play_date) AS prev_date
  FROM unique_days
),
with_streak_id AS (
  SELECT play_date,
         SUM(CASE WHEN prev_date IS NULL OR (play_date - prev_date) > 1 THEN 1 ELSE 0 END)
           OVER (ORDER BY play_date) AS streak_id
  FROM with_prev
),
with_day_num AS (
  SELECT play_date,
         ROW_NUMBER() OVER (PARTITION BY streak_id ORDER BY play_date) AS day_in_streak
  FROM with_streak_id
),
bucketed AS (
  SELECT g.user_result,
         CASE WHEN d.day_in_streak >= 5 THEN 5 ELSE d.day_in_streak END AS bucket
  FROM games g
  JOIN with_day_num d
    ON strftime(to_timestamp(g.end_time), '%Y-%m-%d')::DATE = d.play_date
  WHERE (g.white = $USERNAME OR g.black = $USERNAME)
    AND g.time_class = $TIME_CLASS AND g.user_result IS NOT NULL
)
SELECT
  CASE bucket WHEN 5 THEN 'Day 5+ (long streak)' ELSE 'Day ' || CAST(bucket AS VARCHAR) END AS day_in_streak,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM bucketed
GROUP BY bucket
ORDER BY bucket
