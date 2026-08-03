UPDATE users
SET status = 'inactive'
WHERE id = 10;

UPDATE users
SET balance = 999.00
WHERE id = 500;

DELETE FROM users
WHERE id = 900;

INSERT INTO users (id, name, status, balance)
VALUES (1001, 'New User', 'active', 150.00);
