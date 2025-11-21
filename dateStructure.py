import os
import re
import sys
import argparse
import datetime
import pandas as pd


def write_log(log_file, msg):
    timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"{timestamp} {msg}\n")


def bs_to_ad(bs_y, bs_m, bs_d):
    """
    Convert Bikram Sambat (BS) date to Gregorian (AD) date.
    This function tries several common libraries; if none are available
    it raises an informative error asking the user to install one.
    Returns a datetime.date instance.
    """
    # try nepali_datetime (common package name: nepali_datetime)
    try:
        import nepali_datetime as nd
        return nd.date(bs_y, bs_m, bs_d).to_datetime_date()
    except Exception:
        pass

    try:
        # some installs expose date class directly
        from nepali_datetime import date as nd_date

        return nd_date(bs_y, bs_m, bs_d).to_datetime_date()
    except Exception:
        pass

    try:
        # fallback to 'nepali' package if present (older API)
        import nepali

        # nepali.bs_to_ad returns (y,m,d)
        ad = nepali.bs_to_ad(bs_y, bs_m, bs_d)
        return datetime.date(ad[0], ad[1], ad[2])
    except Exception:
        pass

    raise RuntimeError(
        "Nepali BS->AD conversion package not found.\n"
        "Please install one of: `pip install nepali-datetime` or `pip install nepali_datetime` "
        "or `pip install nepali`."
    )


def extract_bs_from_sheetname(sheet_name):
    """Find BS date pattern in sheet name like 2079.02.02 or 2079.2.2"""
    m = re.search(r"(\d{4})[\.\-\s_]*(\d{1,2})[\.\-\s_]*(\d{1,2})", sheet_name)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3))


def find_time_and_value_columns(df):
    """
    Locate the time column and the best candidate MW (numeric) column.
    Strategy:
    - Search for a header cell containing 'time' (case-insensitive). If found, use that column and header row index.
    - Otherwise assume first column is the time column and header is row 0.
    - For MW/value column, pick the column (other than time) that has the most numeric values in the rows below the header.
    Returns (header_row_idx, time_col_idx, value_col_idx).
    """
    header_row = 0
    time_col = 0

    # search for 'Time' header anywhere in the first 5 rows
    for r in range(min(5, len(df))):
        for c in range(df.shape[1]):
            val = str(df.iat[r, c]) if not pd.isna(df.iat[r, c]) else ""
            if re.match(r"^\s*time\s*$", val, flags=re.IGNORECASE):
                header_row = r
                time_col = c
                break
        else:
            continue
        break

    # build candidate rows after header
    data_start = header_row + 1
    data = df.iloc[data_start:]

    # choose value column: the column (not time_col) with most numeric non-null entries
    best_col = None
    best_count = -1
    for c in range(df.shape[1]):
        if c == time_col:
            continue
        col_vals = pd.to_numeric(data.iloc[:, c], errors="coerce")
        count = col_vals.notna().sum()
        if count > best_count:
            best_count = count
            best_col = c

    if best_col is None:
        best_col = time_col + 1 if time_col + 1 < df.shape[1] else None

    return header_row, time_col, best_col


def parse_hour_minute(val):
    """Return (hour, minute) from a time-like string. If no match, return (None, None)."""
    if pd.isna(val):
        return None, None
    s = str(val).strip()
    m = re.match(r"^\s*(\d{1,2})(?:\s*[:\.]\s*(\d{1,2}))?", s)
    if not m:
        return None, None
    hour = int(m.group(1))
    minute = int(m.group(2)) if m.group(2) is not None else 0
    return hour, minute


def normalize_day_series(times, values):
    """
    Given lists/series of times and numeric values, build a Series indexed 1..24
    with MW values for each hour. Missing hours are filled by linear interpolation.
    times: iterable of time-like strings
    values: iterable of numeric values (coerced to float; non-numeric -> NaN)
    Returns a pandas Series indexed by hour (1..24) with float values.
    """
    hour_map = {}
    for t, v in zip(times, values):
        h, m = parse_hour_minute(t)
        if h is None:
            continue
        if h == 0:
            # treat 0 as 24
            h = 24
        # keep only rows where minutes == 0
        if m != 0:
            continue
        # prefer first occurrence for the hour
        if h not in hour_map:
            try:
                hour_map[h] = float(v)
            except Exception:
                hour_map[h] = float('nan')

    # build series for 1..24
    idx = list(range(1, 25))
    s = pd.Series(index=idx, dtype='float64')
    for h in idx:
        s.at[h] = hour_map.get(h, pd.NA)

    # convert to numeric and interpolate
    s = s.astype('float64')
    s = s.interpolate(method='linear', limit_direction='both')

    return s


def process_file(in_path, out_path, log_file):
    xls = pd.ExcelFile(in_path)
    write_log(log_file, f"Processing file: {os.path.basename(in_path)}")

    with pd.ExcelWriter(out_path, engine='openpyxl') as writer:
        for sheet in xls.sheet_names:
            write_log(log_file, f"  sheet: {sheet}")
            bs = extract_bs_from_sheetname(sheet)
            if not bs:
                write_log(log_file, f"    skipping (no BS date found): {sheet}")
                continue

            try:
                ad_date = bs_to_ad(*bs)
            except Exception as e:
                write_log(log_file, f"    ERROR converting BS->AD for {sheet}: {e}")
                continue

            # read sheet
            df = pd.read_excel(in_path, sheet_name=sheet, header=None, engine='openpyxl')

            header_row, time_col, value_col = find_time_and_value_columns(df)
            if value_col is None:
                write_log(log_file, f"    no value column found for {sheet}, skipping")
                continue

            data_start = header_row + 1
            data = df.iloc[data_start:]
            times = data.iloc[:, time_col]
            values = data.iloc[:, value_col]

            series = normalize_day_series(times, values)

            # Build output dataframe with YYYY-MM-DD HH:MM format (hours 01..24)
            out_rows = []
            for h in range(1, 25):
                hh = f"{h:02d}"
                time_str = f"{ad_date:%Y-%m-%d} {hh}:00"
                # for 24 we keep '24:00' as requested
                if h == 24:
                    time_str = f"{ad_date:%Y-%m-%d} 24:00"
                out_rows.append({'Time': time_str, 'MW': series.at[h]})

            out_df = pd.DataFrame(out_rows)

            # sheet name should be YYYY.MM.DD
            out_sheet_name = f"{ad_date.year}.{ad_date.month:02d}.{ad_date.day:02d}"
            # Excel sheet name cannot exceed 31 chars
            out_sheet_name = out_sheet_name[:31]

            out_df.to_excel(writer, sheet_name=out_sheet_name, index=False)
            write_log(log_file, f"    wrote sheet {out_sheet_name} with {len(out_df)} rows")


def main():
    parser = argparse.ArgumentParser(description="Convert BS-dated sheet names to AD and normalize 24-hour MW series")
    parser.add_argument("input_folder", help="Folder containing .xlsx files to process")
    parser.add_argument("output_folder", help="Folder where processed files will be written")
    parser.add_argument("--log", default="date_structure_log.txt", help="Log file path")
    args = parser.parse_args()

    os.makedirs(args.output_folder, exist_ok=True)
    # clear or create log
    open(args.log, 'w', encoding='utf-8').close()

    for fname in os.listdir(args.input_folder):
        if not fname.endswith('.xlsx'):
            continue
        in_path = os.path.join(args.input_folder, fname)
        out_path = os.path.join(args.output_folder, fname)
        try:
            process_file(in_path, out_path, args.log)
        except Exception as e:
            write_log(args.log, f"ERROR processing {fname}: {e}")

    print("Processing completed. See log for details.")


if __name__ == '__main__':
    main()
