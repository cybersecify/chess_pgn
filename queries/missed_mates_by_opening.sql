-- Which openings produce the most missed mates?
SELECT opening,
       SUM(CASE WHEN mate_in = 1 THEN 1 ELSE 0 END) AS missed_m1,
       SUM(CASE WHEN mate_in = 2 THEN 1 ELSE 0 END) AS missed_m2,
       COUNT(*) AS total
FROM missed_mates
WHERE opening IS NOT NULL
GROUP BY opening
ORDER BY total DESC
LIMIT 15
