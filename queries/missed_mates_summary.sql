-- Missed mates summary: how many M1 and M2 per month (rapid)
SELECT strftime(to_timestamp(end_time), '%Y-%m') AS month,
       SUM(CASE WHEN mate_in = 1 THEN 1 ELSE 0 END) AS missed_m1,
       SUM(CASE WHEN mate_in = 2 THEN 1 ELSE 0 END) AS missed_m2,
       COUNT(*) AS total_missed
FROM missed_mates
GROUP BY month
ORDER BY month DESC
LIMIT 24
