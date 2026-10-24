"""Data access with a local cache (Google Drive in Colab, any folder elsewhere).

Every download is saved to `folder`; the next run reads it from there, so a
server outage or rate limit does not stop the analysis. Delete a file to force
a fresh download.
"""
import os
import pandas as pd


def from_cache(folder, filename, download, date_col="data", until=None, **read_kw):
    """Read folder/filename if it exists and covers `until`; otherwise call download(), save and return."""
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        d = pd.read_csv(path, parse_dates=[date_col], **read_kw)
        if until is None or d[date_col].max() >= pd.Timestamp(until) - pd.Timedelta(days=7):
            print(f"[cau] {filename} llegit ({len(d):,} files)")
            return d
        print(f"[cau] {filename} no arriba fins a {until}: el baixo de nou")
    d = download()
    try:
        os.makedirs(folder, exist_ok=True)
        d.to_csv(path, index=False)
        print(f"[cau] {filename} baixat i desat")
    except OSError as e:
        print(f"[cau] {filename} baixat però no desat ({e})")
    return d


def era5_daily(lat, lon, start, end, timeout=120):
    """Daily ERA5 max and mean 2 m temperature from the Open-Meteo archive API."""
    import requests
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
           "&daily=temperature_2m_max,temperature_2m_mean&timezone=Europe%2FMadrid")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({"data": pd.to_datetime(d["time"]),
                         "tmax": d["temperature_2m_max"], "tmean": d["temperature_2m_mean"]})


def era5_hourly(lat, lon, start, end, timeout=180):
    """Hourly ERA5 2 m temperature and boundary-layer height from Open-Meteo."""
    import requests
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
           "&hourly=temperature_2m,boundary_layer_height&timezone=Europe%2FMadrid")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    h = r.json()["hourly"]
    return pd.DataFrame({"hora": pd.to_datetime(h["time"]), "temp": h["temperature_2m"],
                         "blh": h.get("boundary_layer_height")})


def find_column(df, words):
    """First column whose normalised name contains any of `words` (robust to portal renamings)."""
    for c in df.columns:
        name = c.lower().replace("_", "").replace(" ", "")
        if any(w in name for w in words):
            return c
    return None


def daily_consumption(raw):
    """Open Data BCN / Datadis electricity file -> daily kWh by postcode, sector and time band.

    Returns columns: data, cp, sector, tram (if present), kwh.
    """
    col_date = find_column(raw, ["data", "fecha", "date"])
    col_cp = find_column(raw, ["codipostal", "codigopostal", "postal"])
    col_sec = find_column(raw, ["sector", "tipus", "tipo"])
    col_band = find_column(raw, ["tram", "franja", "horari"])
    col_val = find_column(raw, ["valor", "consum", "kwh", "energia"])
    if None in (col_date, col_cp, col_val):
        raise ValueError(f"No trobo les columnes bàsiques: {list(raw.columns)}")
    ren = {col_date: "data", col_cp: "cp", col_val: "kwh"}
    if col_sec:
        ren[col_sec] = "sector"
    if col_band:
        ren[col_band] = "tram"
    d = raw.rename(columns=ren)
    d["data"] = pd.to_datetime(d["data"])
    d["cp"] = d["cp"].astype(str).str.extract(r"(\d{5})")[0]
    keys = [k for k in ["data", "cp", "sector", "tram"] if k in d.columns]
    return d.groupby(keys, as_index=False)["kwh"].sum()
