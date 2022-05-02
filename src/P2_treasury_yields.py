from fredapi import Fred
from logger import initialize_logger
import numpy as np
import os
import pandas as pd
from pathlib import Path
import sys
import time

# Tickers for FRED
# 1 Year - `DGS1`
# 2 Year - `DGS2`
# 3 Year - `DGS3`
# 1 Month - `DGS1MO`
# 3 Month - `DGS3MO`
# 6 Month - `DGS6MO`
# 5 Year Breakeven - `T5YIE`

if __name__ == "__main__":
    # Ensure working directory path is correct
    while os.path.split(os.getcwd())[-1] != "Options-Project":
        os.chdir(os.path.dirname(os.getcwd()))

    # User defined parameters
    # Assumes that API key has been saved to env variable `FRED_API_KEY`
    fred = Fred()
    save_path = "data/treasury_yields/"
    metrics_dict = {"DGS1": ["1_Year", 1],
                    "DGS2": ["2_Year", 2],
                    "DGS3": ["3_Year", 3],
                    "DGS5": ["5_Year", 5],
                    "DGS1MO": ["1_Month", 1 / 12],
                    "DGS3MO": ["3_Month", 1 / 4],
                    "DGS6MO": ["6_Month", 1 / 2],
                    "T5YIE": ["5_Year_Inflation", 5]}
    # Create data directory if it doesn't exist
    Path(save_path).mkdir(exist_ok=True)

    logger = initialize_logger(logger_name="treasury_yields", save_path=save_path, file_name="process.log")
    start_time = time.time()

    for metric in metrics_dict.keys():
        # Name and ratio for iteration
        [metric_name, metric_ratio] = metrics_dict[metric]

        # Scrape
        df = fred.get_series(metric)
        # Clean
        df = pd.DataFrame(df).dropna(axis=0).reset_index()
        df.rename(columns={"index": "date", 0: "money market yield"},
                  inplace=True)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df["money market yield"] = (df["money market yield"] * 0.01).round(5)

        df["continuous rate"] = ((1 / metric_ratio) * np.log(1 + df["money market yield"] * metric_ratio)).round(8)

        # Sanity check
        if not (df["money market yield"] >= df["continuous rate"]).all():
            logger.error("Market yield should be >= continuous rate (equal when yield = 0)!")
            sys.exit(1)

        # Save
        try:
            old_df = pd.read_csv(os.path.join(save_path, f"{metric_name}.csv"))
            logger.info(f"Updating local {metric_name} file...")
            old_df["date"] = pd.to_datetime(old_df["date"]).dt.date

            df = df.merge(old_df, how="outer",
                          on=["date", "money market yield", "continuous rate"])

            dups = df.duplicated(subset=["date"], keep=False)
            if any(dups):
                logger.info(df[dups])
                logger.error("Inconsistency between new and old! Data not updated!")
                sys.exit(1)
            else:
                logger.info("Updated!")
        except FileNotFoundError:
            logger.info(f"No local {metric_name} file found...")

        # Sort
        df.sort_values(by="date", inplace=True)

        # Save
        df.to_csv(os.path.join(save_path, f"{metric_name}.csv"), index=False)

    logger.info(f"Processed treasury yields - {round(time.time() - start_time, 2)} seconds")
