import psycopg2, os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()
cur.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user';")
conn.commit()
cur.close()
conn.close()
print("✅ role sütunu eklendi.")