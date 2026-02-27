import sqlite3
import re
import os

class DatabaseManager:
    def __init__(self):
        # Local database file creation
        self.db_path = "financial_data.db"
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.create_table()
        print(f"🏠 Local Database Active: {self.db_path}")

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS financial_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            query TEXT,
            result TEXT,
            revenue TEXT,
            net_income TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
        self.conn.execute(query)
        self.conn.commit()

    def save_analysis(self, filename, query, result):
        try:
            # Smart extraction for bonus points (Revenue/Income)
            def extract(pattern, text):
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                return match.group(1).strip() if match else "N/A"

            rev = extract(r"(?:Total Revenue|Total revenues).*?([\$\d,.-]+(?:\s*(?:billion|million|B|M|%))?)", str(result))
            inc = extract(r"(?:Net Income).*?([\$\d,.-]+(?:\s*(?:billion|million|B|M))?)", str(result))

            cursor = self.conn.cursor()
            cursor.execute(
                "INSERT INTO financial_analysis (filename, query, result, revenue, net_income) VALUES (?, ?, ?, ?, ?)",
                (filename, query, str(result), rev, inc)
            )
            self.conn.commit()
            print(f"✅ Auto-Saved to History: {filename}")
            return True
        except Exception as e:
            print(f"❌ Local Save Error: {e}")
            return False

    def get_history(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM financial_analysis ORDER BY created_at DESC")
            rows = cursor.fetchall()
            data = []
            for r in rows:
                data.append({
                    "id": r[0], "filename": r[1], "query": r[2], 
                    "result": r[3], "revenue": r[4], "net_income": r[5], "created_at": r[6]
                })
            return type('obj', (object,), {'data': data})
        except Exception:
            return type('obj', (object,), {'data': []})

db = DatabaseManager()