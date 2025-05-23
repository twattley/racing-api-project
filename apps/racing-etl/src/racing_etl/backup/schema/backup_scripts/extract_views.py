import re

input_file_path = "./src/schema/backup_files/racehorse-database-schema.sql"
drop_views_file_path = "./src/schema/backup_files/drop_views.sql"
create_views_file_path = "./src/schema/backup_files/create_views.sql"

print(f"Reading schema from {input_file_path}")

pattern = re.compile(r"(CREATE VIEW.*?;)\s*(ALTER VIEW.*?;)", re.DOTALL)
view_name_pattern = re.compile(r"CREATE VIEW\s+(?:IF NOT EXISTS\s+)?([\w.]+)")

with open(input_file_path, "r", encoding="utf-8") as file:
    schema_content = file.read()

matches = pattern.findall(schema_content)

drop_view_statements = []


with (
    open(drop_views_file_path, "w", encoding="utf-8") as drop_file,
    open(create_views_file_path, "w", encoding="utf-8") as create_file,
):
    for create_view, alter_view in matches:
        create_file.write(f"{create_view}\n\n{alter_view}\n\n")
        view_name_match = view_name_pattern.search(create_view)
        if view_name_match:
            view_name = view_name_match[1]
            drop_view_statements.append(f"DROP VIEW IF EXISTS {view_name};")

    for drop_statement in drop_view_statements:
        drop_file.write(f"{drop_statement}\n")

print(f"DROP VIEW statements written to {drop_views_file_path}")
print(f"CREATE VIEW and ALTER VIEW statements written to {create_views_file_path}")
