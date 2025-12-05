import os
import re
import pandas as pd
import datetime


# --------------------------
# USER CONFIG — edit these
# --------------------------
# List the FOUR folders to process (absolute or relative to this script)
FOLDERS = [
    r"structuredDataset/2079MV",
    r"structuredDataset/2080MV",
    r"structuredDataset/2081MV",
    r"structuredDataset/2082MV",
]

# Output folder for per-folder combined files and final combined file
OUTPUT_FOLDER = r"combineDataset"
# filename pattern for per-folder output: foldername_combined.xlsx
PER_FOLDER_FILENAME_PATTERN = "{foldername}_combined.xlsx"
# final combined file (combines all folders)
FINAL_OUTPUT = "all_folders_combined.xlsx"

# Log file
LOG_FILE = "data_combine_log.txt"


def write_log(msg):
    ts = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def find_header_row_and_cols(df, max_rows=10):
    """
    Search the first `max_rows` rows for a header row that contains a time-like column and an MV/MW column.
    Returns (header_row_index, time_col_index, mw_col_index).
    If not found, returns (None, 0, 1) as fallback (assume first two columns).
    """
    time_keywords = [r"^\s*time\s*$", r"time\s*\(|timestamp"]
    mw_keywords = [r"\bmw\b", r"\bmv\b", r"megawatt", r"megawatt-hour", r"^\s*mw\s*$"]

    rows = min(max_rows, len(df))
    for r in range(rows):
        row_vals = [str(x) if not pd.isna(x) else "" for x in df.iloc[r].tolist()]
        # find time-like and mw-like columns in this row
        time_col = None
        mw_col = None
        for i, v in enumerate(row_vals):
            low = v.lower()
            for tk in time_keywords:
                if re.search(tk, low):
                    time_col = i
                    break
            if time_col is not None:
                break

        for i, v in enumerate(row_vals):
            low = v.lower()
            for mk in mw_keywords:
                if mk in low:
                    mw_col = i
                    break
            if mw_col is not None:
                break

        if time_col is not None and mw_col is not None:
            return r, time_col, mw_col

    # fallback
    return None, 0, 1


def extract_sheet_data(xls_path, sheet_name):
    try:
        df = pd.read_excel(xls_path, sheet_name=sheet_name, header=None, engine='openpyxl')
    except Exception as e:
        write_log(f"ERROR reading sheet '{sheet_name}' in '{xls_path}': {e}")
        return None

    header_row, time_col, mw_col = find_header_row_and_cols(df)
    if header_row is None:
        # assume header is first row and data follows
        data = df
        header = None
    else:
        header = [str(x) for x in df.iloc[header_row].tolist()]
        data = df.iloc[header_row + 1:]

    # pick time and mw columns by index
    # create a cleaned DataFrame with two columns named 'Time' and 'MW'
    data2 = pd.DataFrame()
    if data.shape[1] <= max(time_col, mw_col):
        # not enough columns — skip
        write_log(f"Skipping sheet '{sheet_name}' in '{xls_path}': not enough columns")
        return None

    data2['Time'] = data.iloc[:, time_col].astype(str)
    data2['MW'] = data.iloc[:, mw_col]

    # drop rows where both are empty/null
    data2 = data2[~(data2['Time'].str.strip().eq('') & data2['MW'].isna())]

    # Drop header-like rows that slipped through: rows where Time column contains header text
    # or MW column contains 'MW'/'MV'/"megawatt" etc.
    time_header_re = re.compile(r"^\s*(time|timestamp|return time)\b", re.IGNORECASE)
    mw_header_re = re.compile(r"^\s*(mw|mv|megawatt)\b", re.IGNORECASE)

    def is_time_header(x):
        try:
            return bool(time_header_re.search(str(x)))
        except Exception:
            return False

    def is_mw_header(x):
        try:
            return bool(mw_header_re.search(str(x)))
        except Exception:
            return False

    header_mask = data2['Time'].apply(is_time_header) | data2['MW'].apply(is_mw_header)
    if header_mask.any():
        data2 = data2[~header_mask]

    # reset index
    data2 = data2.reset_index(drop=True)

    return data2


def combine_files_in_folder(folder):
    """Combine all sheets of all .xlsx files in `folder` into one DataFrame."""
    all_file_dfs = []
    for fname in sorted(os.listdir(folder)):
        if not fname.lower().endswith('.xlsx'):
            continue
        file_path = os.path.join(folder, fname)
        write_log(f"Processing file: {file_path}")
        try:
            xls = pd.ExcelFile(file_path, engine='openpyxl')
        except Exception as e:
            write_log(f"ERROR opening '{file_path}': {e}")
            continue

        file_dfs = []
        for sheet in xls.sheet_names:
            d = extract_sheet_data(file_path, sheet)
            if d is None or d.empty:
                write_log(f"No data extracted from sheet '{sheet}' in '{fname}'")
                continue
            # append sheet data
            file_dfs.append(d)

        if file_dfs:
            # concat all sheets from this file into one DF
            file_combined = pd.concat(file_dfs, ignore_index=True)
            # keep only first header (we already removed header rows during extraction)
            all_file_dfs.append(file_combined)
            write_log(f"Combined {len(file_dfs)} sheets from '{fname}' ({len(file_combined)} rows)")

    if not all_file_dfs:
        return None

    folder_combined = pd.concat(all_file_dfs, ignore_index=True)
    return folder_combined


def sanitize_sheet_name(name: str) -> str:
    return re.sub(r"[:\\/*?\[\]]", "_", name)[:31]


def main():
    # clear log
    open(LOG_FILE, 'w', encoding='utf-8').close()
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    per_folder_paths = []
    for folder in FOLDERS:
        if not os.path.isdir(folder):
            write_log(f"Skipping missing folder: {folder}")
            continue

        write_log(f"Combining folder: {folder}")
        folder_df = combine_files_in_folder(folder)
        if folder_df is None or folder_df.empty:
            write_log(f"No data found in folder: {folder}")
            continue

        # write per-folder combined file
        foldername = os.path.basename(os.path.normpath(folder)) or 'folder'
        out_name = PER_FOLDER_FILENAME_PATTERN.format(foldername=foldername)
        out_path = os.path.join(OUTPUT_FOLDER, out_name)
        try:
            folder_df.to_excel(out_path, index=False)
            write_log(f"Wrote per-folder combined: {out_path} ({len(folder_df)} rows)")
            per_folder_paths.append(out_path)
        except Exception as e:
            write_log(f"ERROR writing per-folder file '{out_path}': {e}")

    # combine per-folder files into a final workbook
    final_dfs = []
    for p in per_folder_paths:
        try:
            df = pd.read_excel(p, engine='openpyxl')
            final_dfs.append(df)
        except Exception as e:
            write_log(f"ERROR reading per-folder file '{p}': {e}")

    if final_dfs:
        final_df = pd.concat(final_dfs, ignore_index=True)
        final_out = os.path.join(OUTPUT_FOLDER, FINAL_OUTPUT)
        try:
            final_df.to_excel(final_out, index=False)
            write_log(f"Wrote final combined file: {final_out} ({len(final_df)} rows)")
            print(f"Done — final combined file: {final_out}")
        except Exception as e:
            write_log(f"ERROR writing final combined file '{final_out}': {e}")
    else:
        write_log("No per-folder combined files to merge into final file")


if __name__ == '__main__':
    main()
