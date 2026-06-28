-- signal_ic.sql — factor forward-return IC harness (signal-quality diagnostic)
--
-- WHY: backtest returns were a day-low fill artifact (look-ahead). At the honest
-- recommended price (band-mid = reference_close), the signal delivers ~zero alpha
-- (10d/20d forward = NIFTY drift). This harness measures whether ANY ranking factor
-- has real forward predictive power (Spearman IC), overall + by regime, so the
-- ranking can be reweighted toward what actually predicts.
--
-- USAGE (on the VPS db, or any pi-pm db with ranking_* + market_data populated):
--   ssh pipm-vps "docker exec -i pipm-db-1 psql -U pipm -d pipm" < scripts/signal_ic.sql
-- Tunables: FWD horizon = OFFSET below (9 = 10 trading days); rank<=200 = candidate
-- pool; as_of_date floor; min stocks/day = 30.
--
-- IC reading: per-day Spearman(factor_rank, fwd_return_rank), averaged over days.
--   |IC| ~0.03-0.05 = usable factor; ~0 = no edge; negative = anti-predictive.

\timing on

-- ============ (1) PER-FACTOR IC (overall) ============
WITH cand AS (
  SELECT res.ranking_run_id, res.stock_id, rr.as_of_date
  FROM ranking_results res JOIN ranking_runs rr ON rr.id = res.ranking_run_id
  WHERE res.rank <= 200 AND rr.as_of_date >= '2019-01-01'
),
fwd AS (
  SELECT c.ranking_run_id, c.stock_id, c.as_of_date, (f.close/cur.close - 1) AS fwd_ret
  FROM cand c
  JOIN market_data cur ON cur.stock_id = c.stock_id AND cur.date = c.as_of_date
  JOIN LATERAL (SELECT close FROM market_data m
                WHERE m.stock_id = c.stock_id AND m.date > c.as_of_date
                ORDER BY m.date OFFSET 9 LIMIT 1) f ON true       -- 10-day forward
),
fac AS (
  SELECT fwd.as_of_date, fwd.fwd_ret, fc.factor_name, fc.normalized_factor_value AS nfv
  FROM fwd JOIN ranking_factor_contributions fc
    ON fc.ranking_run_id = fwd.ranking_run_id AND fc.stock_id = fwd.stock_id
  WHERE fc.normalized_factor_value IS NOT NULL
),
ranked AS (
  SELECT as_of_date, factor_name,
    rank() OVER (PARTITION BY as_of_date, factor_name ORDER BY nfv)      AS rf,
    rank() OVER (PARTITION BY as_of_date, factor_name ORDER BY fwd_ret)  AS rr
  FROM fac
),
dic AS (
  SELECT as_of_date, factor_name, corr(rf::float, rr::float) AS ic
  FROM ranked GROUP BY 1,2 HAVING count(*) >= 30
)
SELECT factor_name,
       round(avg(ic)::numeric, 4) AS mean_ic_10d,
       round((avg(ic)/NULLIF(stddev(ic),0))::numeric, 3) AS ir,
       count(*) AS days
FROM dic GROUP BY 1 ORDER BY 2 DESC;

-- ============ (2) FACTOR INFLUENCE (avg |weighted| — how heavily used) ============
SELECT fc.factor_name,
       round(avg(abs(fc.weighted_factor_value))::numeric, 4) AS avg_abs_weight,
       count(distinct fc.ranking_run_id) AS runs
FROM ranking_factor_contributions fc
JOIN ranking_runs rr ON rr.id = fc.ranking_run_id AND rr.as_of_date >= '2021-01-01'
WHERE fc.weighted_factor_value IS NOT NULL
GROUP BY 1 ORDER BY 2 DESC;

-- ============ (3) PER-FACTOR IC BY REGIME ============
WITH cand AS (
  SELECT res.ranking_run_id, res.stock_id, rr.as_of_date
  FROM ranking_results res JOIN ranking_runs rr ON rr.id = res.ranking_run_id
  WHERE res.rank <= 200 AND rr.as_of_date >= '2019-01-01'
),
fwd AS (
  SELECT c.ranking_run_id, c.stock_id, c.as_of_date, (f.close/cur.close - 1) AS fwd_ret
  FROM cand c
  JOIN market_data cur ON cur.stock_id = c.stock_id AND cur.date = c.as_of_date
  JOIN LATERAL (SELECT close FROM market_data m
                WHERE m.stock_id = c.stock_id AND m.date > c.as_of_date
                ORDER BY m.date OFFSET 9 LIMIT 1) f ON true
),
fac AS (
  SELECT fwd.as_of_date, fwd.fwd_ret, fc.factor_name, fc.normalized_factor_value AS nfv
  FROM fwd JOIN ranking_factor_contributions fc
    ON fc.ranking_run_id = fwd.ranking_run_id AND fc.stock_id = fwd.stock_id
  WHERE fc.normalized_factor_value IS NOT NULL
),
ranked AS (
  SELECT as_of_date, factor_name,
    rank() OVER (PARTITION BY as_of_date, factor_name ORDER BY nfv)     AS rf,
    rank() OVER (PARTITION BY as_of_date, factor_name ORDER BY fwd_ret) AS rr
  FROM fac
),
dic AS (SELECT as_of_date, factor_name, corr(rf::float, rr::float) AS ic
        FROM ranked GROUP BY 1,2 HAVING count(*) >= 30),
dicr AS (
  SELECT d.factor_name, COALESCE(rh.regime_label,'?') AS reg, d.ic
  FROM dic d LEFT JOIN regime_history rh
    ON rh.as_of_date = d.as_of_date AND rh.benchmark_symbol = '^NSEI'
)
SELECT factor_name,
  round(avg(ic) FILTER (WHERE reg='BULL_LOW_VOL')::numeric,3)  AS bull_lo,
  round(avg(ic) FILTER (WHERE reg='BULL_HIGH_VOL')::numeric,3) AS bull_hi,
  round(avg(ic) FILTER (WHERE reg='BEAR_LOW_VOL')::numeric,3)  AS bear_lo,
  round(avg(ic) FILTER (WHERE reg='BEAR_HIGH_VOL')::numeric,3) AS bear_hi
FROM dicr GROUP BY 1 ORDER BY (avg(ic)) DESC;
