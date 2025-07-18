-- 1. Admin User: Highest reliability, full access.
INSERT INTO users (username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score)
VALUES
('admin_user', 'admin@example.com', '+10000000001', TRUE, NOW(), NOW(), 'admin', 0.99);

-- 2. Verified User: High reliability, trusted contributor.
INSERT INTO users (username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score)
VALUES
('verified_user', 'verified@example.com', '+10000000002', TRUE, NOW(), NOW(), 'verified', 0.85);

-- 3. Regular User: Standard user with a decent track record.
INSERT INTO users (username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score)
VALUES
('regular_user', 'regular@example.com', '+10000000003', TRUE, NOW(), NOW(), 'regular', 0.70);

-- 4. New User: Default for new sign-ups, lower initial reliability.
INSERT INTO users (username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score)
VALUES
('new_user', 'new@example.com', '+10000000004', TRUE, NOW(), NOW(), 'new', 0.50);

-- 5. Flagged User: Low reliability, possibly due to poor quality reports.
INSERT INTO users (username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score)
VALUES
('flagged_user', 'flagged@example.com', '+10000000005', TRUE, NOW(), NOW(), 'flagged', 0.25);