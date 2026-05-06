-- Revenge spiral: win rate in games 1-5 after a loss (rapid)
-- Shows how many games it takes to mentally recover
WITH ordered AS (
  SELECT end_time, user_result,
         ROW_NUMBER() OVER (ORDER BY end_time) AS rn
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND user_result IS NOT NULL AND end_time IS NOT NULL
),
loss_positions AS (
  SELECT rn AS loss_rn FROM ordered WHERE user_result = 'lose'
),
recovery AS (
  SELECT o.user_result,
         (o.rn - l.loss_rn) AS games_after_loss
  FROM ordered o
  JOIN loss_positions l ON o.rn > l.loss_rn AND o.rn <= l.loss_rn + 5
)
SELECT
  'Game +' || CAST(games_after_loss AS VARCHAR) AS after_loss,
  COUNT(*) AS games,
  SUM(CASE WHEN user_result = 'win'  THEN 1 ELSE 0 END) AS wins,
  SUM(CASE WHEN user_result = 'lose' THEN 1 ELSE 0 END) AS losses,
  ROUND(100.0 * SUM(CASE WHEN user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
FROM recovery
GROUP BY games_after_loss
ORDER BY games_after_loss
