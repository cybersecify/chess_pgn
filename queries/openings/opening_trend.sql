-- Win rate trend for your top 8 openings by 6-month period (rapid)
-- Shows whether you are improving, declining, or plateauing in each opening
WITH half_years AS (
  SELECT opening, user_result,
         CAST(strftime(to_timestamp(end_time), '%Y') AS INTEGER) * 10 +
           CASE WHEN CAST(strftime(to_timestamp(end_time), '%m') AS INTEGER) <= 6 THEN 1 ELSE 2 END AS half
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND opening IS NOT NULL AND user_result IS NOT NULL
),
top_openings AS (
  SELECT opening
  FROM games
  WHERE (white = $USERNAME OR black = $USERNAME)
    AND time_class = $TIME_CLASS AND opening IS NOT NULL
  GROUP BY opening
  HAVING COUNT(*) >= 10
  ORDER BY COUNT(*) DESC
  LIMIT 8
),
trend AS (
  SELECT h.opening,
         h.half,
         COUNT(*) AS games,
         ROUND(100.0 * SUM(CASE WHEN h.user_result = 'win' THEN 1 ELSE 0 END) / COUNT(*), 1) AS win_pct
  FROM half_years h
  INNER JOIN top_openings t ON h.opening = t.opening
  GROUP BY h.opening, h.half
  HAVING COUNT(*) >= 3
)
SELECT opening,
       CAST(half / 10 AS VARCHAR) || '-H' || CAST(half % 10 AS VARCHAR) AS period,
       games,
       win_pct
FROM trend
ORDER BY opening, half
