from pathlib import Path

from dotenv import load_dotenv


def load_env(app_name: str):
    mono_repo_root = "~/Code/python/racing-api-project/racing-api-project"
    dotenv_path = Path(mono_repo_root) / "apps" / app_name / ".env"
    load_dotenv(dotenv_path=dotenv_path)
