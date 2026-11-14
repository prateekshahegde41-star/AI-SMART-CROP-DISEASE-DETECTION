"""Open-Meteo: current + 7-day weather and soil moisture. Owner: Group 2 (Shravani)."""
import time
import requests

URL = "https://api.open-meteo.com/v1/forecast"
_cache: dict = {}
TTL = 3600


def fetch(lat: float, lon: float) -> dict:
    key = (round(lat, 1), round(lon, 1))
    hit = _cache.get(key)
    if hit and time.time() - hit[0] < TTL:
        return hit[1]
    r = requests.get(URL, timeout=10, params={
        "latitude": lat, "longitude": lon, "timezone": "auto", "forecast_days": 7,
        "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
        "hourly": "relative_humidity_2m,soil_moisture_0_to_1cm",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
    })
    r.raise_for_status()
    j = r.json()

    def day_mean(var):                       # average the hourly values per date
        buckets: dict = {}
        for t, v in zip(j["hourly"]["time"], j["hourly"][var]):
            if v is not None:
                buckets.setdefault(t[:10], []).append(v)
        return {d: sum(v) / len(v) for d, v in buckets.items()}

    hum, soil = day_mean("relative_humidity_2m"), day_mean("soil_moisture_0_to_1cm")
    d = j["daily"]
    daily = []
    for i, date in enumerate(d["time"]):
        tmax, tmin = d["temperature_2m_max"][i], d["temperature_2m_min"][i]
        daily.append({"date": date, "t_max": tmax, "t_min": tmin, "t_mean": (tmax + tmin) / 2,
                      "humidity": round(hum.get(date, 0), 1), "rain_mm": d["precipitation_sum"][i] or 0,
                      "wind_kmh": d["wind_speed_10m_max"][i],
                      "soil_moisture": round(soil.get(date, 0), 3)})
    c = j["current"]
    out = {"current": {"temp_c": c["temperature_2m"], "humidity": c["relative_humidity_2m"],
                       "rain_mm": c["precipitation"], "wind_kmh": c["wind_speed_10m"],
                       "soil_moisture": daily[0]["soil_moisture"]},
           "daily": daily}
    _cache[key] = (time.time(), out)
    return out
