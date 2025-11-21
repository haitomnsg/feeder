import os
import datetime
import pandas as pd


# --------------------------
# USER CONFIG (edit these)
# --------------------------
INPUT_FOLDER = r"extractedDataset/weather/"   # folder containing the source weather xlsx
INPUT_FILENAME = "weather_clean.xlsx"      # filename (set to None to auto-detect first .xlsx)

OUTPUT_FOLDER = r"structuredDataset/weather"     # where cleaned file will be written
OUTPUT_FILENAME = "weather_structured.xlsx"

LOG_FILE = "weather_structure_log.txt"


def write_log(msg):
    ts = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ts} {msg}\n")


def find_input_file(folder, filename=None):
    if filename:
        path = os.path.join(folder, filename)
        if os.path.exists(path):
            return path
    # otherwise auto-detect first xlsx
    for fn in os.listdir(folder):
        if fn.lower().endswith('.xlsx'):
            return os.path.join(folder, fn)
    return None


def find_column(columns, keywords):
    for k in keywords:
        for c in columns:
            if k.lower() in str(c).lower():
                return c
    return None


def shift_time_label(orig_dt: pd.Timestamp, shift_minutes: int = 15):
    """Return formatted time label as 'YYYY-MM-DD HH:MM' with special handling for 24:00.
    orig_dt + shift_minutes used to compute hour; if result rolls to next day and hour==0,
    label should be 'YYYY-MM-DD 24:00' with the original date.
    """
    new_dt = orig_dt + pd.Timedelta(minutes=shift_minutes)
    if new_dt.hour == 0 and new_dt.date() != orig_dt.date():
        # represent as previous-day 24:00
        return orig_dt.strftime('%Y-%m-%d') + ' 24:00'
    else:
        return new_dt.strftime('%Y-%m-%d %H:00')


def replace_with_adjacent_mean(series, treat_zero_as_missing=True):
    """Replace NaN (and optionally zeros) in a pandas Series by mean of nearest non-missing neighbors.
    The series is not reindexed; replacements are done in-place on a copy which is returned.
    If only one neighbor exists use that value. If none exist, value remains NaN.
    """
    s = pd.to_numeric(series, errors='coerce').copy()
    n = len(s)
    for i in range(n):
        val = s.iat[i]
        if pd.isna(val) or (treat_zero_as_missing and val == 0):
            # find previous valid
            prev_idx = None
            for j in range(i - 1, -1, -1):
                v = s.iat[j]
                if not pd.isna(v) and (not treat_zero_as_missing or v != 0):
                    prev_idx = j
                    break
            # find next valid
            next_idx = None
            for j in range(i + 1, n):
                v = s.iat[j]
                if not pd.isna(v) and (not treat_zero_as_missing or v != 0):
                    next_idx = j
                    break

            vals = []
            if prev_idx is not None:
                vals.append(float(s.iat[prev_idx]))
            if next_idx is not None:
                vals.append(float(s.iat[next_idx]))

            if vals:
                s.iat[i] = sum(vals) / len(vals)
            else:
                # leave as NaN
                s.iat[i] = pd.NA
    return s


def process_weather(in_path, out_path):
    write_log(f"Reading {in_path}")
    df = pd.read_excel(in_path, engine='openpyxl')

    cols = df.columns.tolist()
    # find columns
    time_col = find_column(cols, ['time (npt)', 'time'])
    air_col = find_column(cols, ['air temperature', 'air temp'])
    solar_col = find_column(cols, ['global solar', 'solar radiation'])
    rh_col = find_column(cols, ['relative humidity', 'relative humidity 1 hour'])

    if not time_col or not air_col or not solar_col or not rh_col:
        write_log(f"ERROR: required columns not found. Found columns: {cols}")
        raise RuntimeError('Required columns not found in weather file')

    work = df[[time_col, air_col, solar_col, rh_col]].copy()
    work.columns = ['Time_raw', 'Air Temperature', 'Global Solar Radiation', 'Relative Humidity']

    # parse time - assume given as local Nepal time strings like '2022-10-01 00:45:00'
    work['Time_parsed'] = pd.to_datetime(work['Time_raw'], errors='coerce')
    before = len(work)
    work = work[work['Time_parsed'].notna()].copy()
    write_log(f"Dropped {before - len(work)} rows with unparseable timestamps")

    # shift time labels: :45 -> next hour :00; 23:45 -> 24:00 on same date
    work['Time'] = work['Time_parsed'].apply(lambda t: shift_time_label(pd.Timestamp(t)))

    # For Air Temperature: replace NaN or zero by mean of nearest valid neighbors
    work['Air Temperature'] = replace_with_adjacent_mean(work['Air Temperature'], treat_zero_as_missing=True)

    # For Relative Humidity: same as air temperature
    work['Relative Humidity'] = replace_with_adjacent_mean(work['Relative Humidity'], treat_zero_as_missing=True)

    # For Global Solar Radiation: set NaN to 0 (zeros remain)
    work['Global Solar Radiation'] = pd.to_numeric(work['Global Solar Radiation'], errors='coerce').fillna(0)

    # Final ordering and drop helper column
    out = work[['Time', 'Air Temperature', 'Global Solar Radiation', 'Relative Humidity']].copy()

    os.makedirs(os.path.dirname(out_path) if os.path.dirname(out_path) else '.', exist_ok=True)
    out.to_excel(out_path, index=False)
    write_log(f"Wrote structured weather to {out_path} ({len(out)} rows)")


def main():
    # clear log
    open(LOG_FILE, 'w', encoding='utf-8').close()
    in_path = find_input_file(INPUT_FOLDER, INPUT_FILENAME)
    if not in_path:
        msg = f"Input weather file not found in {INPUT_FOLDER}"
        print(msg)
        write_log(msg)
        return
    out_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILENAME)
    process_weather(in_path, out_path)
    print(f"Done — output written to {out_path}")


if __name__ == '__main__':
    main()
