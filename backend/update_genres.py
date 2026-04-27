
import sqlite3
from datetime import datetime
import sys

DB_PATH = "chinook.db"

def run_job():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_genres (
                run_date TIMESTAMP,
                genre_name TEXT,
                total_sales INTEGER
            )
        """)

        # Query top genres
        query = """
            SELECT g.Name, SUM(il.Quantity) as TotalSales
            FROM Genre g
            JOIN Track t ON g.GenreId = t.GenreId
            JOIN InvoiceLine il ON t.TrackId = il.TrackId
            GROUP BY g.Name
            ORDER BY TotalSales DESC
        """
        results = cursor.execute(query).fetchall()

        # Insert results
        now = datetime.now()
        for genre, sales in results:
            cursor.execute("INSERT INTO daily_genres VALUES (?, ?, ?)", (now, genre, sales))

        conn.commit()
        print(f"[{now}] Successfully logged {len(results)} rows to daily_genres.")
        conn.close()
    except Exception as e:
        print(f"[{datetime.now()}] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_job()
