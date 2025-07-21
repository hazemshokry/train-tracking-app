INSERT INTO users (id, username, email, phone_number, is_active, date_joined, last_login, user_type, reliability_score, device_token) VALUES
('a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e', 'admin_user', 'admin@example.com', '+10000000001', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'admin', 0.99, NULL),
('b5f9f233-1c30-5c9d-9b2b-8c8f2d2f9f9f', 'verified_user', 'verified@example.com', '+10000000002', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'verified', 0.85, NULL),
('c6000344-2d41-6dae-a03c-9d903e300000', 'regular_user', 'regular@example.com', '+10000000003', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'regular', 0.7, NULL),
('d7111455-3e52-7ebf-b14d-aead4f411111', 'new_user', 'new@example.com', '+10000000004', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'new', 0.5, NULL),
('e8222566-4f63-8fd0-c25e-bfbe50522222', 'flagged_user', 'flagged@example.com', '+10000000005', 1, '2025-07-17 19:00:23', '2025-07-17 19:00:23', 'flagged', 0.25, NULL);

INSERT INTO refresh_tokens (token, user_id, expires_at, created_at) VALUES
('dummy_token_for_admin_user_abc123', 'a4e8e122-0b29-4b8c-8a1a-7b7e1c1e8e8e', '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_verified_user_def456', 'b5f9f233-1c30-5c9d-9b2b-8c8f2d2f9f9f', '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_regular_user_ghi789', 'c6000344-2d41-6dae-a03c-9d903e300000', '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_new_user_jkl012', 'd7111455-3e52-7ebf-b14d-aead4f411111', '2025-07-27 19:00:23', '2025-07-17 19:00:23'),
('dummy_token_for_flagged_user_mno345', 'e8222566-4f63-8fd0-c25e-bfbe50522222', '2025-07-27 19:00:23', '2025-07-17 19:00:23');
