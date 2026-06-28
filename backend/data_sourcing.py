import os
import time
import logging
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WAQI_API_KEY = os.getenv("WAQI_API_KEY")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME")

REQUEST_TIMEOUT = 4.5  # seconds
RETRY_COUNT = 3
CACHE_TTL_SECONDS = 300  # 5 minutes

# Simple in-memory TTL cache
_cache = {}

def _cache_get(key):
    """Retrieve from cache if not expired."""
    entry = _cache.get(key)
    if entry and (time.monotonic() - entry["ts"]) < CACHE_TTL_SECONDS:
        return entry["data"]
    return None

def _cache_set(key, data):
    """Store in cache with current timestamp."""
    _cache[key] = {"data": data, "ts": time.monotonic()}

def _get_session():
    """Create a requests Session with retry logic."""
    session = requests.Session()
    retry_strategy = Retry(
        total=RETRY_COUNT,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def fetch_weather(city_name="Lucknow"):
    """
    Fetches live precipitation and temperature from WeatherAPI.
    Returns a dictionary with raw data and the source of the truth.
    """
    data = {"precip_mm": 0.0, "temp_c": 30.0, "source": "fallback"}

    if not WEATHER_API_KEY:
        logger.warning("No WEATHER_API_KEY found in .env. Using fallback weather.")
        return data

    cache_key = f"weather_{city_name}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        url = f"https://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city_name}"
        session = _get_session()
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()

        data["precip_mm"] = float(res_json["current"].get("precip_mm", 0.0))
        data["temp_c"] = float(res_json["current"].get("temp_c", 30.0))
        data["source"] = "live_weatherapi"
        logger.info(f"Weather live: {data['temp_c']}°C, {data['precip_mm']}mm precip")

    except requests.exceptions.RequestException as e:
        logger.error(f"WeatherAPI error: {e}. Falling back to baseline.")

    _cache_set(cache_key, data)
    return data

def fetch_aqi(lat="26.8467", lon="80.9462"):
    """
    Fetches live Air Quality Index from WAQI using geospatial coordinates.
    Default coordinates are anchored to Lucknow center.
    """
    data = {"current_aqi": 100, "source": "fallback"}

    if not WAQI_API_KEY:
        logger.warning("No WAQI_API_KEY found in .env. Using fallback AQI.")
        return data

    cache_key = f"aqi_{lat}_{lon}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        # Use geospatial coordinates (not hardcoded city name)
        url = f"https://api.waqi.info/feed/geo:{lat};{lon}/?token={WAQI_API_KEY}"
        session = _get_session()
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()

        if res_json.get("status") == "ok":
            data["current_aqi"] = int(res_json["data"].get("aqi", 100))
            data["source"] = "live_waqi"
            logger.info(f"AQI live: {data['current_aqi']}")

    except requests.exceptions.RequestException as e:
        logger.error(f"WAQI API error: {e}. Falling back to baseline.")

    _cache_set(cache_key, data)
    return data

def fetch_demographics(city_name="Lucknow"):
    """
    Fetches macroscopic city population baseline from GeoNames to anchor
    the density algorithms in the Monte Carlo engine.
    """
    data = {"city": city_name, "population": 3900000, "source": "fallback"}

    if not GEONAMES_USERNAME:
        logger.warning("No GEONAMES_USERNAME found in .env. Using fallback demographics.")
        return data

    cache_key = f"geo_{city_name}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        url = f"https://api.geonames.org/searchJSON?q={city_name}&maxRows=1&username={GEONAMES_USERNAME}"
        session = _get_session()
        response = session.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()

        if "geonames" in res_json and len(res_json["geonames"]) > 0:
            geo_data = res_json["geonames"][0]
            data["city"] = geo_data.get("name", city_name)
            data["population"] = geo_data.get("population", 3900000)
            data["source"] = "live_geonames"
            logger.info(f"Demographics live: {data['city']}, pop={data['population']}")

    except requests.exceptions.RequestException as e:
        logger.error(f"GeoNames API error: {e}. Falling back to baseline.")

    _cache_set(cache_key, data)
    return data

# --- Local Verification Test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    print("Testing Live Data Sourcing Pipeline...\n")

    weather = fetch_weather()
    print(f"  Weather Data: {weather}")

    aqi = fetch_aqi()
    print(f"  AQI Data: {aqi}")

    demo = fetch_demographics()
    print(f"  Demographic Data: {demo}")
    print("\nPipeline check complete.")
