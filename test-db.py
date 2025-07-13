import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Test the database connection
try:
    conn = psycopg2.connect(os.getenv("DATABASE_URL"))
    print("Database connection successful")
    conn.close()
except psycopg2.Error as e:
    print("Database connection failed:", e)
