
import sqlite3
from datetime import datetime

DB_PATH = 'Chinook.db'

TOP_GENRES_QUERY = """
SELECT g.Name AS Genre, COUNT(il.InvoiceLineId) AS TotalSales
FROM Genre g
JOIN Track t ON g.GenreId = t.GenreId
JOIN InvoiceLine il ON t.TrackId = il.TrackId
GROUP BY g.GenreId
ORDER BY TotalSales DESC;
"""

def run_daily_update():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_genres (
            date TEXT,
            genre TEXT,
            total_sales INTEGER
        )
    """)

    results = cursor.execute(TOP_GENRES_QUERY).fetchall()

    today = datetime.now().strftime('%Y-%m-%d')
    for row in results:
        cursor.execute("INSERT INTO daily_genres VALUES (?, ?, ?)", (today, row[0], row[1]))

    conn.commit()
    print(f"{datetime.now()}: Inserted {len(results)} rows for {today}")
    conn.close()

if __name__ == "__main__":
    run_daily_update()
