-- ==============================================================================
-- CAMPUS LOST AND FOUND — ADVANCED SQL DEMONSTRATION SCRIPT
-- Compatible with MySQL 8.0 & standard relational SQL engines.
-- Demonstrates: DDL Constraints, Joins, Aggregations, GROUP BY, HAVING,
-- Subqueries, Transactions, Concurrency Row Locks, and Query Optimization.
-- ==============================================================================

USE campus_lost_found_db;

-- ------------------------------------------------------------------------------
-- 1. RELATIONAL SCHEMA & INTEGRITY CHECKS
-- ------------------------------------------------------------------------------

-- 1.1 List all tables and table storage engines
SELECT table_name, engine, table_rows, data_length, index_length
FROM information_schema.tables
WHERE table_schema = 'campus_lost_found_db';

-- 1.2 Inspect Foreign Key Relationships and Cascade Rules
SELECT 
    constraint_name, 
    table_name, 
    column_name, 
    referenced_table_name, 
    referenced_column_name
FROM information_schema.key_column_usage
WHERE table_schema = 'campus_lost_found_db' 
  AND referenced_table_name IS NOT NULL;


-- ------------------------------------------------------------------------------
-- 2. BASIC AND ADVANCED JOIN QUERIES
-- ------------------------------------------------------------------------------

-- 2.1 INNER JOIN: Retrieve approved lost/found items with reporter and category details
SELECT 
    i.id AS item_id,
    i.name AS item_name,
    i.report_type,
    c.name AS category_name,
    u.username AS reporter_username,
    u.department AS reporter_department,
    i.location,
    i.report_date,
    i.status
FROM lostfound_item i
INNER JOIN lostfound_category c ON i.category_id = c.id
INNER JOIN accounts_user u ON i.user_id = u.id
WHERE i.verification_status = 'APPROVED'
ORDER BY i.created_at DESC;

-- 2.2 LEFT OUTER JOIN: Retrieve all students and their total items and claims
SELECT 
    u.id AS student_id,
    u.username,
    u.full_name,
    u.usn,
    u.department,
    COUNT(DISTINCT i.id) AS total_items_reported,
    COUNT(DISTINCT cl.id) AS total_claims_submitted
FROM accounts_user u
LEFT JOIN lostfound_item i ON u.id = i.user_id
LEFT JOIN lostfound_claim cl ON u.id = cl.claimant_id
WHERE u.role = 'STUDENT'
GROUP BY u.id, u.username, u.full_name, u.usn, u.department
ORDER BY total_items_reported DESC;

-- 2.3 MULTI-TABLE JOIN: Approved claims with item, finder, and claimant details
SELECT 
    cl.id AS claim_id,
    i.name AS item_name,
    c.name AS category,
    finder.full_name AS found_by,
    finder.email AS finder_email,
    claimant.full_name AS claimed_by,
    claimant.usn AS claimant_usn,
    reviewer.username AS approved_by_admin,
    cl.reviewed_at
FROM lostfound_claim cl
INNER JOIN lostfound_item i ON cl.item_id = i.id
INNER JOIN lostfound_category c ON i.category_id = c.id
INNER JOIN accounts_user finder ON i.user_id = finder.id
INNER JOIN accounts_user claimant ON cl.claimant_id = claimant.id
LEFT JOIN accounts_user reviewer ON cl.reviewed_by_id = reviewer.id
WHERE cl.status = 'APPROVED';


-- ------------------------------------------------------------------------------
-- 3. AGGREGATE FUNCTIONS, GROUP BY & HAVING CLAUSES
-- ------------------------------------------------------------------------------

-- 3.1 Category Breakdown: Count of items reported per category
SELECT 
    c.id AS category_id,
    c.name AS category_name,
    COUNT(i.id) AS total_reports,
    SUM(CASE WHEN i.report_type = 'LOST' THEN 1 ELSE 0 END) AS lost_count,
    SUM(CASE WHEN i.report_type = 'FOUND' THEN 1 ELSE 0 END) AS found_count
FROM lostfound_category c
LEFT JOIN lostfound_item i ON c.id = i.category_id
GROUP BY c.id, c.name
ORDER BY total_reports DESC;

-- 3.2 GROUP BY with HAVING: Categories with more than 1 reported item
SELECT 
    c.name AS category_name,
    COUNT(i.id) AS item_count
FROM lostfound_category c
INNER JOIN lostfound_item i ON c.id = i.category_id
GROUP BY c.id, c.name
HAVING COUNT(i.id) >= 1
ORDER BY item_count DESC;

-- 3.3 Department Report Analytics with HAVING: Departments with active student reporters
SELECT 
    u.department,
    COUNT(DISTINCT u.id) AS registered_students,
    COUNT(i.id) AS total_reports_filed
FROM accounts_user u
INNER JOIN lostfound_item i ON u.id = i.user_id
WHERE u.department IS NOT NULL AND u.department != ''
GROUP BY u.department
HAVING COUNT(i.id) >= 1
ORDER BY total_reports_filed DESC;


-- ------------------------------------------------------------------------------
-- 4. SUBQUERIES (SCALAR, IN, EXISTS, AND CORRELATED)
-- ------------------------------------------------------------------------------

-- 4.1 Subquery with IN: Find items that have at least one PENDING claim
SELECT id, name, location, report_date
FROM lostfound_item
WHERE id IN (
    SELECT DISTINCT item_id 
    FROM lostfound_claim 
    WHERE status = 'PENDING'
);

-- 4.2 Correlated Subquery with EXISTS: Students who have never submitted any reports
SELECT u.id, u.username, u.full_name, u.usn, u.department
FROM accounts_user u
WHERE u.role = 'STUDENT'
  AND NOT EXISTS (
      SELECT 1 
      FROM lostfound_item i 
      WHERE i.user_id = u.id
  );

-- 4.3 Scalar Subquery: Items reported more recently than the campus average report date
SELECT id, name, report_type, report_date
FROM lostfound_item
WHERE report_date > (
    SELECT DATE(AVG(report_date)) 
    FROM lostfound_item
);

-- 4.4 Correlated Subquery for Unread Notification Count
SELECT 
    u.username,
    u.email,
    (
        SELECT COUNT(*) 
        FROM lostfound_notification n 
        WHERE n.user_id = u.id AND n.is_read = FALSE
    ) AS unread_notifications
FROM accounts_user u
WHERE u.role = 'STUDENT';


-- ------------------------------------------------------------------------------
-- 5. TRANSACTION MANAGEMENT & CONCURRENCY ROW LOCKING
-- Demonstrates how lostfound.services.approve_claim guarantees ACID isolation
-- ------------------------------------------------------------------------------

-- Simulation of concurrent claim approval in MySQL:
START TRANSACTION;

-- Step 1: Acquire row-level lock on the target claim and item to prevent race conditions
SELECT * FROM lostfound_claim 
WHERE id = 1 
FOR UPDATE;

SELECT * FROM lostfound_item 
WHERE id = (SELECT item_id FROM lostfound_claim WHERE id = 1) 
FOR UPDATE;

-- Step 2: Approve the selected claim
UPDATE lostfound_claim 
SET status = 'APPROVED', 
    reviewed_at = NOW(), 
    updated_at = NOW()
WHERE id = 1;

-- Step 3: Transition item lifecycle status to CLAIMED
UPDATE lostfound_item 
SET status = 'CLAIMED', 
    updated_at = NOW()
WHERE id = (SELECT item_id FROM lostfound_claim WHERE id = 1);

-- Step 4: Automatically reject all other competing pending claims for the same item
UPDATE lostfound_claim 
SET status = 'REJECTED', 
    admin_remarks = 'Another claim for this item was approved.',
    reviewed_at = NOW(), 
    updated_at = NOW()
WHERE item_id = (SELECT item_id FROM lostfound_claim WHERE id = 1)
  AND id != 1
  AND status = 'PENDING';

-- Step 5: Insert historical audit log
INSERT INTO lostfound_itemstatushistory (item_id, changed_by_id, old_status, new_status, remarks, changed_at)
VALUES (
    (SELECT item_id FROM lostfound_claim WHERE id = 1),
    1, -- Admin User ID
    'ACTIVE',
    'CLAIMED',
    'Claim #1 approved. Item marked as CLAIMED.',
    NOW()
);

-- Commit transaction atomicity
COMMIT;


-- ------------------------------------------------------------------------------
-- 6. QUERY PERFORMANCE & INDEX OPTIMIZATION (EXPLAIN)
-- ------------------------------------------------------------------------------

-- Check execution plan for public listing query utilizing idx_item_type_vstatus
EXPLAIN SELECT * FROM lostfound_item 
WHERE report_type = 'FOUND' 
  AND verification_status = 'APPROVED'
ORDER BY created_at DESC;

-- Check execution plan for student notification query utilizing idx_notification_user_read
EXPLAIN SELECT * FROM lostfound_notification 
WHERE user_id = 1 
  AND is_read = FALSE;
