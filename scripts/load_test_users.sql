-- SQL script to load 10 test users
-- Note: Replace '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''' with actual bcrypt password hashes.

INSERT INTO users
    (username, email, hashed_password, role, is_active)
VALUES
    ('testuser1', 'testuser1@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('testuser2', 'testuser2@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('testuser3', 'testuser3@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('testuser4', 'testuser4@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 0),
    -- Inactive user
    ('testuser5', 'testuser5@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('adminuser2', 'adminuser2@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'admin', 1),
    -- Additional admin
    ('testuser6', 'testuser6@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('testuser7', 'testuser7@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('testuser8', 'testuser8@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1),
    ('testuser9', 'testuser9@example.com', '''$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx''', 'user', 1);

-- Example of how to generate a bcrypt hash in Python (using the bcrypt library):
-- import bcrypt
-- password = "password123"
-- hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
-- print(hashed_password.decode('utf-8'))
