# db.py
import os
import duckdb
from dotenv import load_dotenv

load_dotenv()

MD_TOKEN = os.getenv("MOTHERDUCK_TOKEN")
MD_DATABASE = os.getenv("MD_DATABASE", "fbref_soccer_stats")

# Global connection that your app reuses.
# This loads the MotherDuck extension and attaches the cloud DB.
def get_connection():
    con = duckdb.connect()  # in-memory duckdb client
    con.execute("INSTALL motherduck;")
    con.execute("LOAD motherduck;")
    if MD_TOKEN:
        con.execute(f"SET motherduck_token='{MD_TOKEN}';")
    # Attach the cloud DB under schema md
    con.execute(f"ATTACH 'md:{MD_DATABASE}' AS md;")
    # Optional: keep our tables in schema md.fbref
    con.execute("CREATE SCHEMA IF NOT EXISTS md.fbref;")
    return con

# singleton
CON = get_connection()
