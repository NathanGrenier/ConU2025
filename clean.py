import logging
from enum import Enum

import pandas as pd

from config import VIOLATIONS_FILE_PATH, logger


class ViolationDomain(Enum):
    AIR = "AIR"
    WATER = "EAU"


def renameColumns(df: pd.DataFrame) -> pd.DataFrame:
    column_mapping = {
        "nom_contrevenant": "offender_name",
        "infraction": "offence",
        "lieu_infraction": "location",
        "date_infraction": "infraction_date",
        "date_jugement": "judgment_date",
        "montant_reclame": "amount_claimed",
        "sentence": "sentence",
        "reglement": "regulation_violated",
        "domaine": "domain",
    }

    return df.rename(columns=column_mapping)


def cleanViolations(df: pd.DataFrame) -> pd.DataFrame:
    # Clean the regulation_violated column to only keep the violation code
    # df["regulation_violated"] = df["regulation_violated"].apply(
    #     lambda x: re.search(r"\d{4}-\d{2}", x).group()
    #     if re.search(r"\d{4}-\d{2}", x)
    #     else x
    # )

    # return df
    pass


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    df_violations = pd.read_csv(f"{VIOLATIONS_FILE_PATH}")
    df_violations = renameColumns(df_violations)

    # df_violations = cleanViolations(df_violations)

    # List all regulations violated and the number of times they were violated
    regulations_violated = df_violations["regulation_violated"].value_counts()
    print("Regulations violated and the number of times they were violated:")
    print(regulations_violated)

    # Display locations of violations of the type "2001-10"
    violations_2001_10 = df_violations[
        df_violations["regulation_violated"].str.contains("2001-10")
    ]
    print("Locations of violations of the type '2001-10':")
    pd.set_option("display.max_colwidth", None)
    print(violations_2001_10["location"])
