-- Insert statement to add a user
INSERT INTO users (username, email, phone_number, password_hash)
-- Select 10 random usernames
SELECT
    -- Generate a random username
    CONCAT('user_', FLOOR(RAND() * 1000000) + 1),
    -- Generate a random email
    CONCAT('user_', FLOOR(RAND() * 1000000) + 1, '@example.com'),
    -- Generate a random phone number
    CONCAT('01', FLOOR(RAND() * 1000000000) + 1),
    -- Use a fixed password hash for all users (insecure, replace with proper hashing in a real application)
    'your_password_hash'
-- Insert 10 rows
FROM DUAL
LIMIT 10;

-- Select the data to verify insertion
SELECT * FROM users;