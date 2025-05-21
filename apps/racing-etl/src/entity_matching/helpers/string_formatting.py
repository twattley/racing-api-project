import pandas as pd


def format_horse_name(data: pd.DataFrame) -> pd.DataFrame:
    data = data.assign(
        filtered_horse_name=lambda x: x["horse_name"]
        .str.replace("'", "")
        .str.replace(r"\(.*?\)", "", regex=True)
        .str.strip()
        .str.lower()
    )

    return data
