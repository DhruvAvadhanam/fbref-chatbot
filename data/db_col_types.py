import duckdb, os
from dotenv import load_dotenv

# loads info from .env file 
load_dotenv()

# gets the motherduck token in the .env file
MOTHERDUCK_TOKEN = os.getenv('MOTHERDUCK_TOKEN')
DB_NAME = "fbref_soccer_stats"

# connect to MotherDuck
con = duckdb.connect(f"md:{DB_NAME}?motherduck_token={os.getenv('MOTHERDUCK_TOKEN')}")

# get all tables
tables = con.execute("SHOW TABLES").fetchdf()["name"].tolist()

sql_statements = []

def detect_numeric_type(values):
    """
    Decide if column is INTEGER or DOUBLE based on sampled values.
    """
    for v in values:
        if v is None:
            continue
        try:
            if "." in str(v):
                return "DOUBLE"
        except:
            pass
    return "INTEGER"

for t in tables:
    # Describe table
    df = con.execute(f'DESCRIBE "main"."{t}"').fetchdf()
    for col, col_type in zip(df["column_name"], df["column_type"]):
        if col_type.upper() == "VARCHAR":
            # Sample 200 rows, quote table and column names to avoid function conflicts
            sample = con.execute(f'SELECT "{col}" FROM "main"."{t}" LIMIT 200').fetchdf()[col].dropna().astype(str)
            
            if len(sample) == 0:
                continue
            
            # Check if values are numeric-looking
            numeric_like = sample.apply(lambda x: x.replace(".", "", 1).isdigit())
            
            if numeric_like.mean() > 0.95:  # >95% numeric
                target_type = detect_numeric_type(sample)
                stmt = f'''
                ALTER TABLE "main"."{t}"
                ALTER COLUMN "{col}" TYPE {target_type} USING TRY_CAST("{col}" AS {target_type});
                '''
                sql_statements.append(stmt)

# Print all generated SQL statements
print("\n".join(sql_statements))
