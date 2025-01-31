import sqlite3
from datetime import datetime
import pandas as pd

class DatabaseManager:
    def __init__(self, db_name='dpo_data.db'):
        self.db_name = db_name
        self.conn = None
        self.init_db()

    def init_db(self):
        self.conn = sqlite3.connect(self.db_name)
        c = self.conn.cursor()
        
        c.executescript('''
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE,
                value TEXT,
                updated_at TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS datasets (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE,
                created_at TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS entries (
                id INTEGER PRIMARY KEY,
                dataset_id INTEGER,
                question TEXT,
                response_a TEXT,
                response_b TEXT,
                preferred TEXT,
                status TEXT,
                created_at TIMESTAMP,
                FOREIGN KEY (dataset_id) REFERENCES datasets(id)
            );
            
            CREATE TABLE IF NOT EXISTS quick_responses (
                id INTEGER PRIMARY KEY,
                text TEXT,
                created_at TIMESTAMP
            );
        ''')
        self.conn.commit()

    def save_api_key(self, api_key):
        c = self.conn.cursor()
        c.execute(
            """
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES ('openai_api_key', ?, ?)
            """,
            (api_key, datetime.now())
        )
        self.conn.commit()

    def get_api_key(self):
        c = self.conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'openai_api_key'")
        result = c.fetchone()
        return result[0] if result else None

    def create_dataset(self, name):
        try:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO datasets (name, created_at) VALUES (?, ?)",
                (name, datetime.now())
            )
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_datasets(self):
        return pd.read_sql("SELECT * FROM datasets", self.conn)

    def get_entries(self, dataset_name):
        return pd.read_sql(
            """
            SELECT question, response_a, response_b, preferred, created_at
            FROM entries e
            JOIN datasets d ON e.dataset_id = d.id
            WHERE d.name = ?
            ORDER BY e.created_at DESC
            """,
            self.conn,
            params=(dataset_name,)
        )

    def save_entry(self, dataset_name, question, response_a, response_b):
        c = self.conn.cursor()
        c.execute(
            """
            INSERT INTO entries 
            (dataset_id, question, response_a, response_b, preferred, status, created_at)
            VALUES (
                (SELECT id FROM datasets WHERE name = ?),
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                dataset_name,
                question,
                response_a,
                response_b,
                "A",
                "active",
                datetime.now()
            )
        )
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
    
    # Add these methods to db_manager.py

    def get_quick_responses(self):
        return pd.read_sql(
            "SELECT * FROM quick_responses ORDER BY created_at DESC",
            self.conn
        )

    def add_quick_response(self, text):
        try:
            c = self.conn.cursor()
            c.execute(
                "INSERT INTO quick_responses (text, created_at) VALUES (?, ?)",
                (text, datetime.now())
            )
            self.conn.commit()
            return True
        except Exception:
            return False

    def delete_quick_response(self, response_id):
        try:
            c = self.conn.cursor()
            c.execute("DELETE FROM quick_responses WHERE id = ?", (response_id,))
            self.conn.commit()
            return True
        except Exception:
            return False

    def get_dataset_stats(self, dataset_name):
        c = self.conn.cursor()
        c.execute("""
            SELECT 
                COUNT(*) as total_entries,
                COUNT(DISTINCT question) as unique_questions,
                MIN(created_at) as first_entry,
                MAX(created_at) as last_entry
            FROM entries e
            JOIN datasets d ON e.dataset_id = d.id
            WHERE d.name = ?
        """, (dataset_name,))
        return c.fetchone()