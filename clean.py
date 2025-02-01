import logging
import os
import re
from enum import Enum
from typing import List

import pandas as pd

from config import AIR_QUALITY_FILE_PATH, DUMP_PATH, VIOLATIONS_FILE_PATH, logger


class ViolationDomain(Enum):
    AIR = "AIR"
    WATER = "EAU"


def renameColumns(df: pd.DataFrame, columnMapping) -> pd.DataFrame:
    return df.rename(columns=columnMapping)


def keepColumns(df: pd.DataFrame, keepColumns: List[str]) -> pd.DataFrame:
    return df_violations[keepColumns]


def dumpData(df: pd.DataFrame, filename: str):
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    df.to_csv(f"{filename}", index=False)


def cleanViolations(df: pd.DataFrame) -> pd.DataFrame:
    # Clean the regulation_violated column to only keep the violation code
    regex = r"\d+-\d+"
    df["regulation_violated"] = df["regulation_violated"].apply(
        lambda x: re.search(regex, x).group() if re.search(regex, x) else x
    )

    return df


def combineDateHour(df: pd.DataFrame) -> pd.DataFrame:
    df["timestamp"] = pd.to_datetime(
        df["date"] + " " + df["hour"].astype(str) + ":00:00", format="%Y-%m-%d %H:%M:%S"
    )
    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return df


if __name__ == "__main__":
    logger.setLevel(logging.DEBUG)

    df_air_quality = pd.read_csv(f"{AIR_QUALITY_FILE_PATH}")
    airQualityNameMapping = {
        "stationId": "stationId",
        "polluant": "pollutant",
        "valeur": "aqi",
        "date": "date",
        "heure": "hour",
    }
    df_air_quality = renameColumns(df_air_quality, airQualityNameMapping)

    df_air_quality = combineDateHour(df_air_quality)
    df_air_quality = df_air_quality.drop(columns=["date", "hour"])
    dumpData(df_air_quality, f"{DUMP_PATH}/cleaned_air_quality.csv")

    df_violations = pd.read_csv(f"{VIOLATIONS_FILE_PATH}")
    violationsNameMapping = {
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
    df_violations = renameColumns(df_violations, violationsNameMapping)

    violationsDropMapping = [
        "offender_name",
        "offence",
        "location",
        "infraction_date",
        "judgment_date",
        "amount_claimed",
        "sentence",
        "regulation_violated",
        "domain",
    ]
    df_violations = keepColumns(df_violations, violationsDropMapping)

    df_violations = cleanViolations(df_violations)

    # List all regulations violated and the number of times they were violated
    # regulations_violated = df_violations["regulation_violated"].value_counts()
    # print("Regulations violated and the number of times they were violated:")
    # print(regulations_violated)

    # Display locations of violations of the type "2001-10"
    # violations_2001_10 = df_violations[
    #     df_violations["regulation_violated"].str.contains("2001-10")
    # ]
    # print("Location of violations of the type '2001-10':")
    # pd.set_option("display.max_colwidth", None)
    # print(violations_2001_10["location"])

    # violations_2001_10 = df_violations[
    #     df_violations["regulation_violated"].str.contains("2001-10")
    # ]
    # print("Description of violations of the type '2001-10':")
    # pd.set_option("display.max_colwidth", None)
    # print(violations_2001_10["offender_name"])
