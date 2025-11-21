import os
import pandas as pd
import re
import datetime

# ---------------------------------------------------------
# USER CONFIG
# ---------------------------------------------------------
INPUT_FOLDER = r"dataset/2082MV"        # folder containing all monthly XLSX files
OUTPUT_FOLDER = r"extractedDataset/2082MV"      # where month-wise outputs will be created
LOG_FILE = "extraction_log.txt"

# Data ranges
START_ROW = 2      # row 3 in human counting
END_ROW = 31
TIME_COL = "A"
MW_COL = "Y"

# Match sheets ending with {11KV} or (11KV), allow optional spaces, case-insensitive
SHEET_PATTERN = re.compile(r".*[\{\(]\s*11KV\s*[\}\)]\s*$", re.IGNORECASE)


# ---------------------------------------------------------
# LOGGING UTIL
# ---------------------------------------------------------
def write_log(msg):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {msg}\n")


# Clear log file on start
open(LOG_FILE, "w").close()


# ---------------------------------------------------------
# NEW MONTH DETECTION LOGIC
# ---------------------------------------------------------
def detect_year_month(filename):
    """
    Month = first number at the beginning of the filename (1–12)
    Year = first 4-digit number (e.g., 2080)
    """
    # Example: "1 log sheet 2080 BAISAKH.xlsx"
    month_match = re.match(r"^\s*(\d{1,2})", filename)
    if not month_match:
        return None, None

    month = int(month_match.group(1))
    if not (1 <= month <= 12):
        return None, None

    # find year (first 4-digit number)
    year_match = re.search(r"(20\d{2})", filename)
    if not year_match:
        return None, None

    year = year_match.group(1)
    month_str = f"{month:02d}"

    return year, month_str


# ---------------------------------------------------------
# PROCESSING START
# ---------------------------------------------------------
print("\nStarting month-wise extraction...\n")
month_data = {}   # stores extracted data per month


for file in os.listdir(INPUT_FOLDER):
    if not file.endswith(".xlsx"):
        continue

    file_path = os.path.join(INPUT_FOLDER, file)
    print(f"\n📄 File: {file}")
    write_log(f"Processing file: {file}")

    # extract year and month
    year, month = detect_year_month(file)
    if year is None:
        msg = f"ERROR: Could not identify year/month from filename '{file}'"
        print("   ❌ " + msg)
        write_log(msg)
        continue

    year_month_key = f"{year}_{month}"

    if year_month_key not in month_data:
        month_data[year_month_key] = []

    # Try opening the file
    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        err = f"ERROR opening file '{file}': {e}"
        print("   ❌ " + err)
        write_log(err)
        continue

    # List all sheets
    print("   → All sheets:")
    for s in xls.sheet_names:
        print(f"      - {s}")

    write_log(f"All sheets in {file}: {xls.sheet_names}")

    # Filter sheets ending with {11KV} or (11KV)
    matched_sheets = [s for s in xls.sheet_names if SHEET_PATTERN.match(s)]

    if not matched_sheets:
        msg = f"No {{11KV}} sheets found in {file}"
        print(f"   ⚠ {msg}")
        write_log(msg)
        continue

    # Further filter matched sheets to ensure sheet name contains the file's year.month
    # Accept both zero-padded month (e.g. 10) and non-padded (e.g. 9)
    month_nozero = str(int(month))
    month_two = month  # already zero-padded from detect_year_month
    year_month_regex = re.compile(fr"{year}\.({month_two}|{month_nozero})", re.IGNORECASE)

    filtered_sheets = [s for s in matched_sheets if year_month_regex.search(s)]

    if not filtered_sheets:
        msg = f"No {{11KV}} sheets matching year/month {year}.{month_nozero} found in {file}"
        print(f"   ⚠ {msg}")
        write_log(msg)
        continue

    print("   ✓ Matched {11KV} sheets:")
    write_log(f"Matched sheets in {file}: {matched_sheets}")
    if len(filtered_sheets) != len(matched_sheets):
        write_log(f"Filtered out sheets not matching year/month {year}.{month_nozero}: "
                  f"{[s for s in matched_sheets if s not in filtered_sheets]}")

    for s in filtered_sheets:
        print(f"      → {s}")

    # use only the filtered sheets for extraction
    matched_sheets = filtered_sheets

    # Extract data from each matched sheet
    for sheet in matched_sheets:
        try:
            df = pd.read_excel(
                file_path,
                sheet_name=sheet,
                header=None,
                usecols=f"{TIME_COL},{MW_COL}",
                engine="openpyxl"
            )
        except Exception as e:
            err = f"ERROR reading sheet '{sheet}' in file '{file}': {e}"
            print("   ❌ " + err)
            write_log(err)
            continue

        # Extract rows 3–31
        sliced = df.iloc[START_ROW:END_ROW]

        if sliced.isna().all().all():
            msg = f"WARNING: Sheet '{sheet}' in file '{file}' has no usable data"
            print("   ⚠ " + msg)
            write_log(msg)
            continue

        sliced.columns = ["Time", "MW"]
        # Drop half-hour rows: keep only rows where minutes == 0
        # Use regex extraction for hour and minute to avoid pandas parsing warnings
        time_str = sliced["Time"].astype(str).str.strip()
        # extract hour and optional minute; examples matched: '1', '1:00', '01.00', '24:00', ' 7:30 '
        tm = time_str.str.extract(r"^\s*(\d{1,2})(?:\s*[:\.]\s*(\d{1,2}))?", expand=True)
        # tm[0] = hour, tm[1] = minute (may be NaN)
        tm[1] = tm[1].fillna("0")
        # rows that matched the pattern (hour not null) and minute == 0
        matched = tm[0].notna() & (tm[1].astype(int) == 0)
        sliced = sliced[matched]

        if sliced.empty or sliced.isna().all().all():
            msg = f"WARNING: Sheet '{sheet}' in file '{file}' has no usable hourly data"
            print("   ⚠ " + msg)
            write_log(msg)
            continue

        # Keep Time and MW for output, but store sheet info for grouping later
        sliced = sliced.copy()
        sliced["Source File"] = file
        sliced["Sheet"] = sheet

        month_data[year_month_key].append(sliced)

        print(f"   ✓ Extracted {len(sliced)} hourly rows from '{sheet}'")
        write_log(f"Extracted {len(sliced)} hourly rows from '{sheet}' in '{file}'")


# ---------------------------------------------------------
# SAVE OUTPUT FILES
# ---------------------------------------------------------
print("\nSaving month-wise files...\n")

# create output folder if missing
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

for ym_key, dfs in month_data.items():
    if not dfs:
        write_log(f"No data for month {ym_key}, skipping file creation.")
        continue

    final_df = pd.concat(dfs, ignore_index=True)
    output_path = os.path.join(OUTPUT_FOLDER, f"{ym_key}_output.xlsx")

    # Create an Excel workbook with one sheet per original sheet (day).
    # Each sheet will contain only the `Time` and `MW` columns.
    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            # preserve original sheet names; sanitize only invalid characters and truncate to 31 chars
            for sheet_name in final_df["Sheet"].unique():
                group = final_df[final_df["Sheet"] == sheet_name]
                # sanitize sheet name for Excel constraints (cannot contain : \/ * ? [ ] and max 31 chars)
                safe = re.sub(r"[:\\/*?\[\]]", "_", sheet_name)
                out_sheet = safe[:31]

                # write only Time and MW columns
                group_out = group[["Time", "MW"]].reset_index(drop=True)
                group_out.to_excel(writer, sheet_name=out_sheet, index=False)

        print(f"✔ Saved: {output_path}")
        write_log(f"Saved month file: {output_path}")
    except Exception as e:
        err = f"ERROR saving month file '{output_path}': {e}"
        print("   ❌ " + err)
        write_log(err)

print("\n🎉 Extraction completed successfully!")
print(f"✔ Log file generated: {LOG_FILE}")