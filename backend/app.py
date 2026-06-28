import os
import sys
import asyncio
import logging

# Ensure the backend/ directory is on the Python path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from engine import UrbanCascadeEngine
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
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()
app = FastAPI(title="Ripple Engine Core", version="1.0.0")

# Rate limiter — protect Gemini credits and CPU from abuse
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

# CORS: allow local development origins (file://, localhost on common ports)
# In production, set ALLOWED_ORIGINS to your actual domain.
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5500,http://127.0.0.1:5500,http://localhost:8000,http://127.0.0.1:8000,null,https://ripple-engine-production.up.railway.app:8080"
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Rate-limit exception handler
@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"status": "error", "detail": "Rate limit exceeded. Please wait before making another request."}
    )

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
engine = UrbanCascadeEngine()

# Target baseline parameters for the MVP
TARGET_CITY = "Lucknow"
CITY_LAT = "26.8467"
CITY_LON = "80.9462"

# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------
VALID_ZONES = {"Gomti_Nagar", "Hazratganj", "Aminabad", "Alambagh"}

class SimulationRequest(BaseModel):
    zone: str = Field(..., description="The Lucknow zone profile selected by the user")
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

    @field_validator('zone')
    @classmethod
    def validate_zone(cls, v):
        if v not in VALID_ZONES:
            raise ValueError(f"Invalid zone '{v}'. Must be one of: {', '.join(sorted(VALID_ZONES))}")
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
        "city": TARGET_CITY
    }

@app.get("/api/demographics")
@limiter.limit("10/minute")
async def get_geonames_demographics(request: Request):
    """Pulls macroscopic city baseline parameters via GeoNames to anchor our system."""
    data = fetch_demographics(TARGET_CITY)
    return {
        "city": data["city"],
        "population": data["population"],
        "source": data["source"]
    }

@app.get("/api/simulate")
@limiter.limit("30/minute")
async def simulate_urban_cascade(
    request: Request,
    zone: str = Query(..., description="The Lucknow zone profile"),
    intervention: str = Query(..., description="The structural project proposal"),
    year: int = Query(2035, description="The timeline target horizon year")
):
    """
    Main Execution API. Combines user inputs, live environment data,
    and triggers the Monte Carlo vector simulation.
    """
    # 1. Validate with Pydantic
    try:
        sim_req = SimulationRequest(zone=zone, intervention=intervention, year=year)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 2. Gather live baseline telemetry from external APIs (with caching)
    weather_data = fetch_weather(TARGET_CITY)
    aqi_data = fetch_aqi(CITY_LAT, CITY_LON)

    # Adapt to the format the engine expects
    live_weather = {"precip_mm": weather_data["precip_mm"], "temp_c": weather_data["temp_c"]}
    live_aqi = {"current_aqi": aqi_data["current_aqi"]}

    try:
        # 3. Fire the NumPy Monte Carlo simulation in a thread — don't block the event loop
        simulation_output = await asyncio.to_thread(
            engine.run_monte_carlo,
            zone_name=sim_req.zone,
            intervention_name=sim_req.intervention,
            live_weather=live_weather,
            live_aqi=live_aqi,
            target_year=sim_req.year
        )

        # 4. Compile response bundle
        return {
            "status": "success",
            "metadata": {
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
