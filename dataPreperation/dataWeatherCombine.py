import os
import pandas as pd
import datetime
import re


# --------------------------
# USER CONFIG
# --------------------------
COMBINED_FILE = r"combineDataset/all_folders_combined.xlsx"
WEATHER_FILE = r"structuredDataset/weather/weather.xlsx"
OUTPUT_FOLDER = r"merged_output"
OUTPUT_FILE = "combined_with_weather.xlsx"
LOG_FILE = "data_weather_combine_log.txt"

# Columns to keep from weather (will try to auto-detect names)
WEATHER_COL_KEYWORDS = {
    'Air Temperature': ['air temperature', 'air temp'],
    'Global Solar Radiation': ['global solar', 'solar radiation'],
    'Relative Humidity': ['relative humidity', 'rh']
}


def write_log(msg):
    ts = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{ts} {msg}\n")


def parse_time_allow_24(s):
    """Parse time strings like 'YYYY-MM-DD HH:MM' and also 'YYYY-MM-DD 24:00'.
    Returns a pandas.Timestamp or NaT.
    """
    if pd.isna(s):
        return pd.NaT
    s = str(s).strip()
    # handle 24:00 pattern
    m = re.match(r"(\d{4}-\d{2}-\d{2})\s+24:00\b", s)
    if m:
        date_part = m.group(1)
        try:
            d = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
            # represent 24:00 as next day's 00:00
            dt = datetime.datetime.combine(d, datetime.time(0, 0)) + datetime.timedelta(days=1)
            return pd.Timestamp(dt)
        except Exception:
            return pd.NaT

    # try common formats
    try:
        return pd.to_datetime(s, errors='coerce')
    except Exception:
        return pd.NaT


def find_weather_columns(df):
    cols = df.columns.tolist()
    found = {}
    lc = [c.lower() for c in cols]
    for target, keywords in WEATHER_COL_KEYWORDS.items():
        for i, c in enumerate(cols):
            cl = c.lower()
            for k in keywords:
                if k in cl:
                    found[target] = c
                    break
            if target in found:
                break
    return found


def main():
    # clear log
    open(LOG_FILE, 'w', encoding='utf-8').close()
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    if not os.path.exists(COMBINED_FILE):
        write_log(f"Combined file not found: {COMBINED_FILE}")
        print("Combined file not found; edit COMBINED_FILE path in the script")
        return
    if not os.path.exists(WEATHER_FILE):
        write_log(f"Weather file not found: {WEATHER_FILE}")
        print("Weather file not found; edit WEATHER_FILE path in the script")
        return

    write_log(f"Reading combined file: {COMBINED_FILE}")
    combined = pd.read_excel(COMBINED_FILE, engine='openpyxl')

    if 'Time' not in combined.columns:
        # try to detect time column
        tcols = [c for c in combined.columns if 'time' in c.lower()]
        if not tcols:
            write_log("No Time column found in combined file")
            print("No Time column found in combined file")
            return
        time_col_name = tcols[0]
    else:
        time_col_name = 'Time'

    # parse combined times
    combined['__Time_parsed'] = combined[time_col_name].apply(parse_time_allow_24)
    if combined['__Time_parsed'].isna().all():
        write_log('Failed to parse any times in combined file')
        print('Failed to parse times in combined file')
        return

    # determine start time: topmost time (first row with parsed time)
    first_valid_idx = combined['__Time_parsed'].first_valid_index()
    start_time = combined.loc[first_valid_idx, '__Time_parsed']
    write_log(f"Start time from combined file (topmost): {start_time}")

    # read weather and parse times
    write_log(f"Reading weather file: {WEATHER_FILE}")
    weather = pd.read_excel(WEATHER_FILE, engine='openpyxl')

    # find weather columns
    found_cols = find_weather_columns(weather)
    write_log(f"Detected weather columns: {found_cols}")

    # require Time column in weather
    w_time_cols = [c for c in weather.columns if 'time' in str(c).lower()]
    if not w_time_cols:
        write_log('No Time column found in weather file')
        print('No Time column found in weather file')
        return
    w_time_col = w_time_cols[0]

    # parse weather times
    weather['__Time_parsed'] = weather[w_time_col].apply(parse_time_allow_24)

    # filter weather to start at or after start_time
    weather = weather[weather['__Time_parsed'] >= start_time].copy()
    if weather.empty:
        write_log('No weather rows at or after start_time')
        print('No weather rows at or after start_time')
        return

    # set index by parsed time
    weather = weather.set_index('__Time_parsed')

    # build weather subset with detected columns
    weather_cols = {}
    for target in WEATHER_COL_KEYWORDS.keys():
        col = found_cols.get(target)
        if col and col in weather.columns:
            weather_cols[target] = weather[col]
        else:
            # create empty column
            weather_cols[target] = pd.Series(index=weather.index, dtype='float64')

    weather_df = pd.DataFrame(weather_cols)
    # coerce to numeric
    weather_df = weather_df.apply(pd.to_numeric, errors='coerce')

    # reindex weather to combined times (only times present in combined after start_time)
    combined_times = combined['__Time_parsed']
    # filter combined to rows at/after start_time
    combined = combined[combined['__Time_parsed'] >= start_time].copy()

    # Use combined_times as index for weather reindex
    weather_reindexed = weather_df.reindex(combined['__Time_parsed'])

    # interpolate numeric columns to fill missing values by linear interpolation
    weather_interpolated = weather_reindexed.interpolate(method='linear', limit_direction='both')

    # For any remaining NaN (e.g., at ends), fill by forward/backward fill
    weather_interpolated = weather_interpolated.fillna(method='ffill').fillna(method='bfill')

    # attach weather columns to combined (preserve original combined order)
    combined_out = combined.copy()
    for col in weather_interpolated.columns:
        combined_out[col] = weather_interpolated[col].values

    # drop helper parse column if desired and rename Time column to 'Time'
    combined_out = combined_out.drop(columns=['__Time_parsed'], errors='ignore')

    # ensure output has Time as formatted string
    combined_out['Time'] = combined_out[time_col_name].apply(lambda x: str(x))

    out_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    combined_out.to_excel(out_path, index=False)
    write_log(f"Wrote merged output to {out_path} ({len(combined_out)} rows)")
    print(f"Wrote merged output to {out_path}")


if __name__ == '__main__':
    main()
