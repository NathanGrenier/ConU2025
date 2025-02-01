import logging
from enum import Enum

import pandas as pd

from config import VIOLATIONS_FILE_PATH, logger


class ViolationType(Enum):
    AIR = "AIR"
    WATER = "EAU"


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)
    df = pd.read_csv(f"{VIOLATIONS_FILE_PATH}")
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

    # Rename columns
    df.rename(columns=column_mapping, inplace=True)

    print(df.columns)
