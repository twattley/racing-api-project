import re

input_file_path = "./src/schema/backup_files/racehorse-database-schema.sql"
truncate_tables_file_path = "./src/schema/temp/truncate_tables.sql"

print(f"Reading schema from {input_file_path}")

# This pattern is designed to capture schema and table names from CREATE TABLE statements.
# It accounts for potential spaces and the full structure, including schema names if they are present.
pattern = re.compile(
    r"CREATE TABLE\s+(?:IF NOT EXISTS\s+)?(([\w]+)\.)?([\w]+)\s", re.DOTALL
)

with open(input_file_path, "r", encoding="utf-8") as file:
    schema_content = file.read()

matches = pattern.findall(schema_content)

truncate_table_statements = []

for match in matches:
    # Extract schema name if present, default to public if not
    schema_name = match[1] or "public"
    table_name = match[2]
    truncate_statement = f"TRUNCATE TABLE {schema_name}.{table_name} CASCADE;"
    truncate_table_statements.append(truncate_statement)

print(truncate_table_statements)

# with open(truncate_tables_file_path, "w", encoding="utf-8") as truncate_file:
#     for statement in truncate_table_statements:
#         truncate_file.write(f"{statement}\n")

print(f"TRUNCATE TABLE statements written to {truncate_tables_file_path}")
