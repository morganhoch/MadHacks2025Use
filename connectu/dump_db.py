import sqlite3

DB_FILE = "connectu.db"
DUMP_FILE = "seed.sql"

conn = sqlite3.connect(DB_FILE)

with open(DUMP_FILE, "w", encoding="utf-8") as f:
    for line in conn.iterdump():
        f.write(f"{line}\n")

conn.close()
print(f"Database dumped to {DUMP_FILE}!")
