import os
import requests
from dotenv import load_dotenv

# securly load env var 

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WAQI_API_KEY = os.getenv("WAQI_API_KEY")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME")

# hard time out (prevent ui feezing if 3rd party fails/error)

REQUEST_TIMEOUT = 4.0

def fetch_weather(city_name="Lucknow"):
    """
    Fetches live precipitation and temperature from WeatherAPI.
    Returns a dictionary with raw data and the source of the truth.
    """
    # Safe baseline fallbacks for Uttar Pradesh dry season
    data = {"precip_mm": 0.0, "temp_c": 32.0, "source": "fallback"}

    if not WEATHER_API_KEY:
        print("⚠️ No WEATHER_API_KEY found in .env. Using fallback weather.")
        return data
    
    try:
        url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={city_name}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status() # Catches 401 Unauthorized or 404 errors
        res_json = response.json()
        
        data["precip_mm"] = float(res_json["current"].get("precip_mm", 0.0))
        data["temp_c"] = float(res_json["current"].get("temp_c", 32.0))
        data["source"] = "live_weatherapi"
        
    except requests.exceptions.RequestException as e:
        print(f" WeatherAPI timeout or error: {e}. Falling back to baseline.")
        
    return data

def fetch_aqi(lat="26.8467", lon="80.9462"):
    """
    Fetches live Air Quality Index from WAQI using geospatial coordinates.
    Default coordinates are anchored to Lucknow center.
    """
    # Safe baseline fallback (100 = Moderate)
    data = {"current_aqi": 100, "source": "fallback"}
    
    if not WAQI_API_KEY:
        print(" No WAQI_API_KEY found in .env. Using fallback AQI.")
        return data
    

    try:
        url = f"https://api.waqi.info/feed/lucknow/?token={WAQI_API_KEY}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()
        
        if res_json.get("status") == "ok":
            data["current_aqi"] = int(res_json["data"].get("aqi", 100))
            data["source"] = "live_waqi"
            
    except requests.exceptions.RequestException as e:
        print(f" WAQI API timeout or error: {e}. Falling back to baseline.")
        
    return data


def fetch_demographics(city_name="Lucknow"):
    """
    Fetches macroscopic city population baseline from GeoNames to anchor 
    the density algorithms in the Monte Carlo engine.
    """
    # Safe baseline fallback based on last known census estimates
    data = {"city": city_name, "population": 3900000, "source": "fallback"}
    
    if not GEONAMES_USERNAME:
        print(" No GEONAMES_USERNAME found in .env. Using fallback demographics.")
        return data
        
    try:
        url = f"http://api.geonames.org/searchJSON?q={city_name}&maxRows=1&username={GEONAMES_USERNAME}"
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        res_json = response.json()
        
        if "geonames" in res_json and len(res_json["geonames"]) > 0:
            geo_data = res_json["geonames"][0]
            data["city"] = geo_data.get("name", city_name)
            data["population"] = geo_data.get("population", 3900000)
            data["source"] = "live_geonames"
            
    except requests.exceptions.RequestException as e:
        print(f" GeoNames API timeout or error: {e}. Falling back to baseline.")
        
    return data

# --- Local Verification Test ---
if __name__ == "__main__":
    print(" Testing Live Data Sourcing Pipeline...\n")
    
    weather = fetch_weather()
    print(f" Weather Data: {weather}")
    
    aqi = fetch_aqi()
    print(f" AQI Data: {aqi}")
    
    demo = fetch_demographics()
    print(f"  Demographic Data: {demo}")
    print("\n✅ Pipeline check complete.")