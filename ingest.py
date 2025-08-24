import duckdb
import os
import pandas as pd
from scraping_functions.standardized_scraping_function import scrape_fbref_df, LEAGUE_ID_MAP, STAT_CONFIG

# Connect to MotherDuck using your token
con = duckdb.connect(f"md:?motherduck_token={os.getenv('MOTHERDUCK_TOKEN')}")

# Dedicated database for FBref stats
DB_NAME = "fbref_soccer_stats"
con.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
con.execute(f"USE {DB_NAME}")


# Define seasons to ingest
SEASONS = ["2024-2025"]  # Add more seasons if needed

def ingest_to_motherduck():
    for season in SEASONS:
        for competition, league_id in LEAGUE_ID_MAP.items():
            for stat_type, config in STAT_CONFIG.items():

                # table name
                table_name = table_name = f"{stat_type}_{competition}_{season}".replace("-", "_").replace(" ", "_")

                # Check if table already exists
                result = con.execute(f"""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'main' AND table_name = '{table_name}'
                """).fetchall()

                # Skip if table already exists
                if result:
                    print(f"⏩ Skipping {table_name} (already exists)")
                    continue

                print(f"📥 Scraping {season} | {competition} | {stat_type} ...")
                try:
                    df = scrape_fbref_df(stat_type=stat_type, season=season, competition=competition)

                    if df.empty:
                        print(f"⚠️ No data returned for {season} {competition} {stat_type}")
                        continue

                    # Fill missing expected columns with None
                    expected_cols = config["columns"]
                    for col in expected_cols:
                        if col not in df.columns:
                            df[col] = None

                    # Add season + competition metadata
                    df["season"] = season
                    df["competition"] = competition

                    # Register DataFrame
                    con.register("df_view", df)

                    # Create table
                    con.execute(f"""
                        CREATE TABLE {DB_NAME}.{table_name} AS
                        SELECT * FROM df_view
                    """)

                    print(f"✅ Stored {len(df)} rows into {DB_NAME}.{table_name}")

                except Exception as e:
                    print(f"❌ Failed {season} | {competition} | {stat_type} | {e}")

if __name__ == "__main__":
    ingest_to_motherduck()
