import os
import sys
import asyncio
import logging
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Ensure the backend/ directory is on the Python path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import UrbanCascadeEngine, CITY_DATABASE
from data_sourcing import fetch_weather, fetch_aqi, fetch_demographics

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("ripple_engine")

# ---------------------------------------------------------------------------
# Configuration & Initialization
# ---------------------------------------------------------------------------
load_dotenv()

# 1. INITIALIZE THE APP EXACTLY ONCE
app = FastAPI(title="Ripple Engine Core", version="1.0.0")

# 2. ADD THE WIDE-OPEN CORS MIDDLEWARE EXACTLY ONCE
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"status": "error", "detail": "Rate limit exceeded. Please wait."}
    )

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = UrbanCascadeEngine()

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
VALID_CITIES = set(CITY_DATABASE.keys())

class SimulationRequest(BaseModel):
    city: str = Field(
        default="lucknow",
        description="City key (e.g. 'lucknow', 'delhi', 'mumbai')"
    )
    zone: str = Field(..., description="Zone key within the selected city")
    intervention: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="The structural project proposal in natural language"
    )
    year: int = Field(
        default=2035,
        ge=2025,
        le=2100,
        description="The timeline target horizon year"
    )

    @field_validator('city')
    @classmethod
    def validate_city(cls, v):
        if v not in VALID_CITIES:
            raise ValueError(f"Invalid city '{v}'. Must be one of: {', '.join(sorted(VALID_CITIES))}")
        return v

    @field_validator('intervention')
    @classmethod
    def sanitize_intervention(cls, v):
        # Strip dangerous characters to prevent prompt injection
        return v.strip().replace('\n', ' ').replace('\r', ' ')

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health_check():
    """Health check endpoint for monitoring and Docker health checks."""
    return {
        "status": "ok",
        "service": "Ripple Engine Core",
        "version": "1.0.0",
        "supported_cities": sorted(VALID_CITIES)
    }


@app.get("/api/cities")
@limiter.limit("60/minute")
async def list_cities(request: Request):
    """Return all supported cities with metadata for the city dropdown."""
    return {
        "cities": engine.list_cities()
    }


@app.get("/api/zones")
@limiter.limit("60/minute")
async def list_zones(
    request: Request,
    city: str = Query("lucknow", description="City key (e.g. 'lucknow', 'delhi', 'mumbai')")
):
    """Return zones for a given city."""
    try:
        city_meta = engine.get_city_metadata(city)
        return {
            "city": city,
            "display_name": city_meta["display_name"],
            "zones": engine.list_zones(city)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/demographics")
@limiter.limit("10/minute")
async def get_geonames_demographics(
    request: Request,
    city: str = Query("lucknow", description="City key (e.g. 'lucknow', 'delhi', 'mumbai')")
):
    """Pulls macroscopic city baseline parameters via GeoNames to anchor our system."""
    try:
        city_meta = engine.get_city_metadata(city)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    data = fetch_demographics(city_meta["display_name"])
    return {
        "city": data["city"],
        "population": data["population"],
        "source": data["source"]
    }


@app.get("/api/simulate")
@limiter.limit("30/minute")
async def simulate_urban_cascade(
    request: Request,
    city: str = Query("lucknow", description="City key (e.g. 'lucknow', 'delhi', 'mumbai')"),
    zone: str = Query(..., description="Zone key within the selected city"),
    intervention: str = Query(..., description="The structural project proposal"),
    year: int = Query(2035, description="The timeline target horizon year")
):
    """
    Main Execution API. Combines user inputs, live environment data,
    and triggers the Monte Carlo vector simulation.
    """
    # 1. Validate with Pydantic
    try:
        sim_req = SimulationRequest(city=city, zone=zone, intervention=intervention, year=year)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Validate the zone exists within the selected city
    try:
        city_meta = engine.get_city_metadata(sim_req.city)
        engine.get_zone(sim_req.city, sim_req.zone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Gather live baseline telemetry from external APIs (with caching)
    weather_data = fetch_weather(city_meta["display_name"])
    aqi_data = fetch_aqi(city_meta["lat"], city_meta["lon"])

    # Adapt to the format the engine expects
    live_weather = {"precip_mm": weather_data["precip_mm"], "temp_c": weather_data["temp_c"]}
    live_aqi = {"current_aqi": aqi_data["current_aqi"]}

    try:
        # 4. Fire the NumPy Monte Carlo simulation in a thread — don't block the event loop
        simulation_output = await asyncio.to_thread(
            engine.run_monte_carlo,
            city_name=sim_req.city,
            zone_name=sim_req.zone,
            intervention_name=sim_req.intervention,
            live_weather=live_weather,
            live_aqi=live_aqi,
            target_year=sim_req.year
        )

        # 5. Compile response bundle
        return {
            "status": "success",
            "metadata": {
                "selected_city": sim_req.city,
                "selected_zone": sim_req.zone,
                "proposed_intervention": sim_req.intervention,
                "target_year": sim_req.year,
                "live_conditions_used": {
                    "precipitation": f"{live_weather['precip_mm']} mm",
                    "ambient_temperature": f"{live_weather['temp_c']} °C",
                    "baseline_aqi_index": live_aqi["current_aqi"]
                }
            },
            "payload": simulation_output
        }

    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.exception("Simulation pipeline failure")
        raise HTTPException(status_code=500, detail=f"Simulation Pipeline Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting Ripple Engine on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
