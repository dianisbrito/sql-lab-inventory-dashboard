-- ============================================================
-- Example SQL queries — Biological Inventory Demo
-- SQLite dialect. Run against data/inventory.db
--
-- These queries demonstrate intermediate SQL: joins, aggregation,
-- window functions, CTEs, and views — applied to a lab inventory
-- and stock-movement use case.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Basic aggregation: stock by category
-- ------------------------------------------------------------
SELECT
    category,
    COUNT(*)        AS n_items,
    SUM(stock)      AS total_stock,
    ROUND(AVG(stock), 1) AS avg_stock_per_item
FROM items
GROUP BY category
ORDER BY total_stock DESC;


-- ------------------------------------------------------------
-- 2) INNER JOIN: movement history with item details
-- ------------------------------------------------------------
SELECT
    m.movement_date,
    m.movement_type,
    i.collection_code,
    i.taxon,
    i.category,
    m.quantity,
    m.reason,
    m.user
FROM movements m
INNER JOIN items i ON i.item_id = m.item_id
ORDER BY m.movement_date DESC
LIMIT 20;


-- ------------------------------------------------------------
-- 3) LEFT JOIN + aggregation: items with no movement history
--    (useful to flag inventory that has never been used/logged)
-- ------------------------------------------------------------
SELECT
    i.collection_code,
    i.taxon,
    i.category,
    COUNT(m.movement_id) AS n_movements
FROM items i
LEFT JOIN movements m ON m.item_id = i.item_id
GROUP BY i.item_id
HAVING n_movements = 0
ORDER BY i.category;


-- ------------------------------------------------------------
-- 4) Window function: running stock balance per item over time
--    (net of IN/OUT movements, cumulative by date)
-- ------------------------------------------------------------
WITH signed_movements AS (
    SELECT
        item_id,
        movement_date,
        CASE WHEN movement_type = 'IN' THEN quantity ELSE -quantity END AS delta
    FROM movements
)
SELECT
    item_id,
    movement_date,
    delta,
    SUM(delta) OVER (
        PARTITION BY item_id
        ORDER BY movement_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS running_balance
FROM signed_movements
WHERE item_id = (SELECT item_id FROM items LIMIT 1)
ORDER BY movement_date;


-- ------------------------------------------------------------
-- 5) Window function: rank items by total OUT movements per category
--    (identifies the most frequently used reference materials)
-- ------------------------------------------------------------
WITH usage_counts AS (
    SELECT
        i.item_id,
        i.category,
        i.collection_code,
        i.taxon,
        COUNT(m.movement_id) AS times_used
    FROM items i
    JOIN movements m ON m.item_id = i.item_id AND m.movement_type = 'OUT'
    GROUP BY i.item_id
),
ranked AS (
    SELECT
        category,
        collection_code,
        taxon,
        times_used,
        RANK() OVER (PARTITION BY category ORDER BY times_used DESC) AS rank_in_category
    FROM usage_counts
)
SELECT * FROM ranked
WHERE rank_in_category <= 3
ORDER BY category, rank_in_category;


-- ------------------------------------------------------------
-- 6) CTE + CASE: expiration status per item
--    (mirrors the kind of alerting logic a real LIMS/inventory
--    dashboard needs — due soon / overdue / ok)
-- ------------------------------------------------------------
WITH status AS (
    SELECT
        collection_code,
        taxon,
        category,
        stock,
        reactivation_date,
        CASE
            WHEN DATE(reactivation_date) < DATE('now')                       THEN 'Overdue'
            WHEN DATE(reactivation_date) <= DATE('now', '+30 days')          THEN 'Due in 30 days'
            WHEN DATE(reactivation_date) <= DATE('now', '+90 days')          THEN 'Due in 90 days'
            ELSE 'OK'
        END AS reactivation_status
    FROM items
)
SELECT reactivation_status, COUNT(*) AS n_items
FROM status
GROUP BY reactivation_status
ORDER BY
    CASE reactivation_status
        WHEN 'Overdue' THEN 1
        WHEN 'Due in 30 days' THEN 2
        WHEN 'Due in 90 days' THEN 3
        ELSE 4
    END;


-- ------------------------------------------------------------
-- 7) View: low-stock alert list
--    (a view keeps this logic reusable — the dashboard queries
--    this view directly instead of repeating the CASE statement)
-- ------------------------------------------------------------
CREATE VIEW IF NOT EXISTS v_low_stock AS
SELECT
    collection_code,
    taxon,
    category,
    stock,
    CASE
        WHEN stock = 0 THEN 'Out of stock'
        WHEN stock <= 2 THEN 'Low stock'
        ELSE 'OK'
    END AS stock_status
FROM items
WHERE stock <= 2;

SELECT * FROM v_low_stock ORDER BY stock ASC;
