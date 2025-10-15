import psycopg2, os
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
cur = conn.cursor()

cur.execute("UPDATE users SET role = 'admin' WHERE username = 'EmirOzdemir';")
conn.commit()
print("✅ Emir admin yapıldı.")

cur.close()
conn.close()