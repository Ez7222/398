import sqlite3

conn = sqlite3.connect('rgsq.db')
cursor = conn.cursor()

with open('schema.sql', 'r') as f:
    cursor.executescript(f.read())

cursor.executemany ("""INSERT INTO event (title, description, location, date, price, image) VALUES (?, ?, ?, ?, ?, ?)""",
                   [
                       ('Geography writing competition', 'A competition for aspiring geography writers.', 'Brisbane', '2025-10-21 18:30:00', 1.00, 'static/images/1.png'),
                       ('Olympic Games - Elevate 2042 - Legacy', 'A discussion on the legacy of the Olympic Games.', 'Brisbane', '2025-08-01 19:00:00', 12.00, 'static/images/2.jpg'),
                   ])

conn.commit()
conn.close()
