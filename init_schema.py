from db import CON
with open("schema.sql", "r") as f:
    CON.execute(f.read())
print("Schema created.")