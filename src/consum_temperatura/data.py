"""Data access with a local cache (Google Drive in Colab, any folder elsewhere).

Every download is saved to `folder`; the next run reads it from there, so a
server outage or rate limit does not stop the analysis. Delete a file to force
a fresh download.
"""
import os
import numpy as np
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


def era5_radiation(lat, lon, start, end, timeout=120):
    """Daily ERA5 shortwave radiation sum (MJ m-2) from Open-Meteo: control for rooftop PV (v0.14)."""
    import requests
    url = ("https://archive-api.open-meteo.com/v1/archive"
           f"?latitude={lat}&longitude={lon}&start_date={start}&end_date={end}"
           "&daily=shortwave_radiation_sum&timezone=Europe%2FMadrid")
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    d = r.json()["daily"]
    return pd.DataFrame({"data": pd.to_datetime(d["time"]), "rad": d["shortwave_radiation_sum"]})


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
    # El portal pot donar el CP com a text "08001" o com a número 8001: el normalitzem a 5 xifres
    d["cp"] = d["cp"].astype(str).str.extract(r"(\d{4,5})")[0].str.zfill(5)
    keys = [k for k in ["data", "cp", "sector", "tram"] if k in d.columns]
    d["kwh"] = pd.to_numeric(d["kwh"].astype(str).str.replace(",", "."), errors="coerce")
    d = d.dropna(subset=["data", "cp", "kwh"])
    # Files repetides (mateix dia, CP, sector i franja): el portal en té algunes. Si se sumessin,
    # aquell dia sortiria doblat; ens quedem amb la primera (com els notebooks des de la v0.2.3).
    n_dup = int(d.duplicated(keys).sum())
    if n_dup:
        print(f"[i] Files duplicades eliminades: {n_dup}")
    return d.drop_duplicates(keys)[keys + ["kwh"]].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Meteocat (XEMA) stations: an independent temperature for the robustness test of v0.14
# ---------------------------------------------------------------------------
# code -> (name, lat, lon, altitude m). Source: XEMA metadata (Generalitat dataset yqwd-vj5e).
XEMA_STATIONS = {
    "X4": ("Barcelona - el Raval", 41.38386, 2.16774, 33),
    "X8": ("Barcelona - Zona Universitària", 41.37922, 2.10537, 82),
    "WU": ("Badalona - Museu", 41.45215, 2.24757, 42),
    "D5": ("Barcelona - Observatori Fabra", 41.41864, 2.12379, 410),   # Collserola: reference only
}
XEMA_CITY = ["X4", "X8", "WU"]
XEMA_URL = "https://analisi.transparenciacatalunya.cat/resource/7bvh-jvq2.csv"   # daily XEMA data
XEMA_VARS = {1000: "tmean", 1001: "tmax"}


def xema_daily(raw):
    """Long XEMA file (codi_estacio, data_lectura, codi_variable, valor) -> one row per station and day."""
    x = raw.copy()
    x["data"] = pd.to_datetime(x["data_lectura"]).dt.normalize()
    x["var"] = x["codi_variable"].astype(int).map(XEMA_VARS)
    x["valor"] = pd.to_numeric(x["valor"], errors="coerce")
    return (x.dropna(subset=["var"]).pivot_table(index=["data", "codi_estacio"], columns="var", values="valor")
             .reset_index().rename(columns={"codi_estacio": "estacio"}))


def _dist_km(lat1, lon1, lat2, lon2):
    kx = 111.32 * np.cos(np.radians((lat1 + lat2) / 2))     # flat distance, good enough at city scale
    return np.hypot((lon1 - lon2) * kx, (lat1 - lat2) * 110.57)


def station_temperature(stations, lat, lon, fallback=None, codes=XEMA_CITY, power=2, min_km=0.3):
    """Inverse-distance-weighted station temperature at (lat, lon), as in notebook v0.11/v0.12.

    stations: output of xema_daily (data, estacio, tmean, tmax). fallback: optional daily DataFrame
    (data, tmean, tmax), e.g. ERA5; days with no station data take fallback + its mean offset.
    Returns (DataFrame data/tmean/tmax, normalised weights).
    """
    d = np.array([_dist_km(lat, lon, XEMA_STATIONS[c][1], XEMA_STATIONS[c][2]) for c in codes])
    w = 1.0 / np.maximum(d, min_km) ** power
    days = (fallback["data"] if fallback is not None else pd.Series(sorted(stations["data"].unique())))
    out = pd.DataFrame({"data": pd.to_datetime(days).values})
    for var in ["tmean", "tmax"]:
        tw = stations.pivot(index="data", columns="estacio", values=var).reindex(columns=list(codes)).reindex(out["data"])
        W = pd.DataFrame(np.tile(w, (len(tw), 1)), index=tw.index, columns=list(codes)).where(tw.notna())
        v = ((tw * W).sum(axis=1) / W.sum(axis=1)).values           # NaN if no station has data
        if fallback is not None:
            f = fallback[var].values
            v = np.where(np.isnan(v), f + np.nanmean(v - f), v)
        out[var] = v
    return out, w / w.sum()
