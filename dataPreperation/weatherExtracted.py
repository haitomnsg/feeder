import os
import datetime
import pandas as pd


# --------------------------
# USER CONFIG (edit these)
# --------------------------
# Folder containing weather.xlsx (or the folder that contains the weather file)
INPUT_FOLDER = r"dataset/weather"
# If you know the exact filename, set it here (otherwise leave None to auto-detect first .xlsx)
INPUT_FILENAME = "weather.xlsx"

# Folder where the cleaned file will be written
OUTPUT_FOLDER = r"extractedDataset/weather"
# Output filename
OUTPUT_FILENAME = "weather_clean.xlsx"

# Log file
LOG_FILE = "weather_extract_log.txt"

# Date range to keep (inclusive). Format: YYYY-MM-DD
START_DATE = "2022-10-01"
END_DATE = "2025-11-01"


def write_log(msg):
    ts = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def find_input_file(folder, filename=None):
    if filename:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path
        return None

    # auto-detect first .xlsx
    for f in os.listdir(folder):
        if f.lower().endswith('.xlsx'):
            return os.path.join(folder, f)
    return None


def find_column(columns, keywords):
    """Return first column name that contains any of the keywords (case-insensitive)."""
    cols = list(columns)
    for k in keywords:
        for c in cols:
            if k.lower() in str(c).lower():
                return c
    return None


def main():
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    # clear log
    open(LOG_FILE, 'w', encoding='utf-8').close()

    in_path = find_input_file(INPUT_FOLDER, INPUT_FILENAME)
    if not in_path:
        msg = f"Input file not found in {INPUT_FOLDER} (tried {INPUT_FILENAME})"
        print(msg)
        write_log(msg)
        return

    write_log(f"Reading input file: {in_path}")
    try:
        df = pd.read_excel(in_path, engine='openpyxl')
    except Exception as e:
        write_log(f"ERROR reading {in_path}: {e}")
        print("ERROR reading input file; see log")
        return

    cols = df.columns.tolist()

    # Find required columns by keywords
    time_col = find_column(cols, ["time (npt)", "time", "timestamp"]) or find_column(cols, ["time (npt)"])
    air_col = find_column(cols, ["air temperature", "air temp"])
    solar_col = find_column(cols, ["global solar", "solar radiation", "global solar radiation"])
    rh_col = find_column(cols, ["relative humidity", "relative humidity 1 hour", "relative humidity 1 hour average"])

    if not time_col or not air_col or not solar_col or not rh_col:
        write_log(f"ERROR: required columns not found. Detected columns: {cols}")
        print("ERROR: required columns not found. See log for detected columns")
        return

    write_log(f"Using columns: Time='{time_col}', Air='{air_col}', Solar='{solar_col}', RH='{rh_col}'")

    # Extract only these columns
    extracted = df[[time_col, air_col, solar_col, rh_col]].copy()
    extracted.columns = ['Time_raw', 'Air Temperature', 'Global Solar Radiation', 'Relative Humidity']

    # Parse Time column to datetime
    extracted['Time_parsed'] = pd.to_datetime(extracted['Time_raw'], errors='coerce')

    # Drop rows with invalid time
    before = len(extracted)
    extracted = extracted[extracted['Time_parsed'].notna()].copy()
    after = len(extracted)
    write_log(f"Dropped {before-after} rows with invalid timestamps")

    # Filter date range (inclusive)
    start_dt = pd.to_datetime(START_DATE)
    end_dt = pd.to_datetime(END_DATE)
    mask = (extracted['Time_parsed'] >= start_dt) & (extracted['Time_parsed'] <= (end_dt + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)))
    kept = extracted[mask].copy()
    write_log(f"Kept {len(kept)} rows within date range {START_DATE} to {END_DATE}")

    # Format Time as 'YYYY-MM-DD HH:MM' (no seconds)
    kept['Time'] = kept['Time_parsed'].dt.strftime('%Y-%m-%d %H:%M')

    # Final columns and rename
    final = kept[['Time', 'Air Temperature', 'Global Solar Radiation', 'Relative Humidity']].copy()

    # Drop rows where all numeric columns are NaN
    final = final.dropna(axis=0, how='all', subset=['Air Temperature', 'Global Solar Radiation', 'Relative Humidity'])

    out_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILENAME)
    try:
        final.to_excel(out_path, index=False)
        write_log(f"Wrote cleaned file: {out_path} ({len(final)} rows)")
        print(f"Wrote cleaned file: {out_path}")
    except Exception as e:
        write_log(f"ERROR writing {out_path}: {e}")
        print("ERROR writing output file; see log")


if __name__ == '__main__':
    main()
