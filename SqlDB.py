import sqlite3
from datetime import datetime

# Define database name
DB_NAME = 'BinPj.db'

# Initialize the database and create tables if they don't exist
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            points INTEGER DEFAULT 0,
            last_update DATETIME
        )
    ''')
    conn.commit()
    conn.close()

# get today's points for checking
def get_today_points(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT points FROM users 
        WHERE user_id = ? AND date(last_update) = date(?)
    ''', (user_id, today))
    
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# update user points
def update_user_points(user_id: str, points: int):

    current_today_points = get_today_points(user_id)
    if current_today_points >= 50:
        total = get_user_points(user_id)
        return total, 50

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = datetime.now()

    cursor.execute('''
        INSERT INTO users (user_id, points, last_update) 
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET 
            points = points + excluded.points,
            last_update = excluded.last_update
    ''', (user_id, points, now))
    conn.commit()

    # get updated points
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
    total_points = cursor.fetchone()[0]

    conn.close()
    return total_points, current_today_points + points

# get user points
def get_user_points(user_id: str):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT points FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0