INSERT INTO users (id, username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score, device_token) VALUES
(1, 'admin_user', 'admin@example.com', '+10000000001', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'admin', 0.99, NULL),
(2, 'verified_user', 'verified@example.com', '+10000000002', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'verified', 0.85, NULL),
(3, 'regular_user', 'regular@example.com', '+10000000003', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'regular', 0.7, NULL),
(4, 'new_user', 'new@example.com', '+10000000004', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'new', 0.5, NULL),
(5, 'flagged_user', 'flagged@example.com', '+10000000005', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'flagged', 0.25, NULL);

INSERT INTO refresh_tokens (token, user_id, expires_at, created_at) VALUES
('dummy_token_for_admin_user_abc123', 1, '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_verified_user_def456', 2, '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_regular_user_ghi789', 3, '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_new_user_jkl012', 4, '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_flagged_user_mno345', 5, '2025-07-27 19:00:23', '2025-07-17 19:00:23');
