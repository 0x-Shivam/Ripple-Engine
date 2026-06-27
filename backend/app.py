import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import requests
from dotenv import load_dotenv
from engine import UrbanCascadeEngine

# 1. Load configuration and initialize app
load_dotenv()
app = FastAPI(title="Ripple Engine Core", version="1.0.0")

# Enable CORS so our frontend can access the endpoints without security blocks
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize our ultra-fast NumPy math simulator
engine = UrbanCascadeEngine()

# Retrieve secure tokens from local system environment variables
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WAQI_API_KEY = os.getenv("WAQI_API_KEY")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME")

# Target baseline parameters for the MVP
TARGET_CITY = "Lucknow"
CITY_LAT = "26.8467"
CITY_LON = "80.9462"

def fetch_live_telemetry():
    """Fetches real-time environmental data streams from official API endpoints."""
    live_weather = {"precip_mm": 0.0, "temp_c": 30.0}
    live_aqi = {"current_aqi": 100}
    
    # A. Fetch Live Weather data
    if WEATHER_API_KEY:
        try:
            url = f"http://api.weatherapi.com/v1/current.json?key={WEATHER_API_KEY}&q={TARGET_CITY}"
            res = requests.get(url, timeout=3).json()
            live_weather["precip_mm"] = float(res["current"].get("precip_mm", 0.0))
            live_weather["temp_c"] = float(res["current"].get("temp_c", 30.0))
        except Exception as e:
            print(f"⚠️ WeatherAPI error: {e}. Falling back to default baseline parameters.")

    # B. Fetch Live Air Quality data
    if WAQI_API_KEY:
        try:
            url = f"https://api.waqi.info/feed/geo:{CITY_LAT};{CITY_LON}/?token={WAQI_API_KEY}"
            res = requests.get(url, timeout=3).json()
            if res.get("status") == "ok":
                live_aqi["current_aqi"] = int(res["data"].get("aqi", 100))
        except Exception as e:
            print(f"⚠️ WAQI API error: {e}. Falling back to default baseline parameters.")

    return live_weather, live_aqi

@app.get("/api/demographics")
async def get_geonames_demographics():
    """Pulls macroscopic city baseline parameters via GeoNames to anchor our system."""
    if not GEONAMES_USERNAME:
        return {"city": TARGET_CITY, "population": 3900000, "source": "Internal Fallback Baseline"}
    
    try:
        # Pinging GeoNames search endpoint for verified structural statistics
        url = f"http://api.geonames.org/searchJSON?q={TARGET_CITY}&maxRows=1&username={GEONAMES_USERNAME}"
        res = requests.get(url, timeout=3).json()
        if "geonames" in res and len(res["geonames"]) > 0:
            geo_data = res["geonames"][0]
            return {
                "city": geo_data.get("name"),
                "country": geo_data.get("countryName"),
                "population": geo_data.get("population", 3900000),
                "coordinates": {"lat": geo_data.get("lat"), "lng": geo_data.get("lng")},
                "source": "GeoNames Live API Service"
            }
    except Exception as e:
        print(f"⚠️ GeoNames exception triggered: {e}")
    
    return {"city": TARGET_CITY, "population": 3900000, "source": "Internal Fallback Baseline"}

@app.get("/api/simulate")
async def simulate_urban_cascade(
    zone: str = Query(..., description="The Lucknow zone profile selected by the user"),
    intervention: str = Query(..., description="The structural project proposal"),
    year: int = Query(2035, description="The timeline target horizon year")
):
    """
    Main Execution API. Combines user inputs, live environment data, 
    and triggers the 10,000-pass vector simulation pass instantly.
    """
    # 1. Gather live baseline telemetry parameters asynchronously
    weather_feed, aqi_feed = fetch_live_telemetry()
    
    try:
        # 2. Fire the NumPy calculation loops inside the engine
        simulation_output = engine.run_monte_carlo(
            zone_name=zone,
            intervention_name=intervention,
            live_weather=weather_feed,
            live_aqi=aqi_feed,
            target_year=year
        )
        
        # 3. Compile structural response bundle for the frontend interface
        return {
            "status": "success",
            "metadata": {
                "selected_zone": zone,
                "proposed_intervention": intervention,
                "target_year": year,
                "live_conditions_used": {
                    "precipitation": f"{weather_feed['precip_mm']} mm",
                    "ambient_temperature": f"{weather_feed['temp_c']} °C",
                    "baseline_aqi_index": aqi_feed["current_aqi"]
                }
            },
            "payload": simulation_output
        }
        
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simulation Pipeline Collapse: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Spin up the Uvicorn deployment server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)