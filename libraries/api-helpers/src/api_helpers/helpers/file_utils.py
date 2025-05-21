import os


def delete_files_in_directory(directory: str, file_pattern: str):
    for filename in os.listdir(directory):
        if file_pattern not in filename:
            continue
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
