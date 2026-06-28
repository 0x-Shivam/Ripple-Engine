import numpy as np
import time
import logging
from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

logger = logging.getLogger(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Use the modern google-genai SDK (not the deprecated google-generativeai)
gemini_client = None
if GEMINI_API_KEY:
    try:
        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={'timeout': 10000}  # 10 second timeout for classification
        )
        logger.info("Gemini API client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini client: {e}. LLM routing will use fallback.")
else:
    logger.warning("No GEMINI_API_KEY found - LLM routing will use Neutral_Development fallback")

class UrbanCascadeEngine:
    def __init__(self):
        logger.info("Initializing Urban Cascade Monte Carlo Engine...")

        # Real-World Demographic Baselines for Lucknow zones
        self.zones = {
            "Gomti_Nagar": {"population": 450000, "density_km2": 4200, "base_flood_risk": 0.3},
            "Hazratganj": {"population": 210000, "density_km2": 11500, "base_flood_risk": 0.5},
            "Aminabad": {"population": 320000, "density_km2": 18000, "base_flood_risk": 0.7},
            "Alambagh": {"population": 280000, "density_km2": 8500, "base_flood_risk": 0.4}
        }

        # Mathematical Archetypes — coefficient weights for each infrastructure category
        self.archetypes = {
            "Commercial_Heavy": {"Traffic_Flow": 0.18, "Local_Revenue": 0.15, "Property_Values": 0.10, "Flood_Runoff": 0.08, "Emergency_Response": 1.5, "Air_Quality": -0.12},
            "Transit_Hub": {"Traffic_Flow": -0.20, "Local_Revenue": 0.18, "Property_Values": 0.25, "Flood_Runoff": 0.03, "Emergency_Response": -2.0, "Air_Quality": 0.20},
            "Green_Ecology": {"Traffic_Flow": -0.05, "Local_Revenue": 0.08, "Property_Values": 0.18, "Flood_Runoff": -0.30, "Emergency_Response": 0.0, "Air_Quality": 0.35},
            "Utility_Underground": {"Traffic_Flow": 0.15, "Local_Revenue": 0.05, "Property_Values": 0.12, "Flood_Runoff": -0.65, "Emergency_Response": 0.1, "Air_Quality": 0.05},
            "Neutral_Development": {"Traffic_Flow": 0.05, "Local_Revenue": 0.05, "Property_Values": 0.05, "Flood_Runoff": 0.02, "Emergency_Response": 0.2, "Air_Quality": -0.02}
        }

        # Mitigation thresholds (calibrated from Lucknow urban planning baselines)
        self.mitigation_thresholds = {
            "flood_runoff_worst": 0.15,
            "emergency_response_worst": 2.0,
            "traffic_flow_worst": 0.25,
        }

    def _parse_intent(self, raw_text):
        """Uses Gemini 2.5 Flash to semantically route the user's free text to a math model."""
        if not gemini_client or not raw_text or not raw_text.strip():
            logger.warning("No Gemini client or empty text. Defaulting to Neutral_Development.")
            return "Neutral_Development"

        # Sanitize input: truncate and strip newlines to prevent prompt injection
        sanitized = raw_text.strip().replace('\n', ' ').replace('\r', ' ')[:500]

        try:
            prompt = f"""
You are a backend routing AI for a city planning simulation.
Analyze this user proposal: "{sanitized}"

Classify it into EXACTLY ONE of these categories:
- Commercial_Heavy (malls, towers, factories, commerce)
- Transit_Hub (roads, metro, transport, vehicles)
- Green_Ecology (parks, planting trees, environmental)
- Utility_Underground (water pipes, sewers, electrical grids, internet, 5G towers, telecom)
- Neutral_Development (if vague, unknown, or unrelated)

Return ONLY the exact category name string. No markdown, no punctuation, no explanation.
"""
            # Modern google-genai SDK — Client.models.generate_content
            response = gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )

            if response and response.text:
                result_key = response.text.strip()
            else:
                logger.warning("Gemini returned empty response. Falling back to Neutral.")
                return "Neutral_Development"

            # Validate against known archetypes
            if result_key in self.archetypes:
                logger.info(f"Gemini routed '{sanitized[:60]}...' -> {result_key}")
                return result_key
            else:
                logger.warning(f"Gemini returned unknown archetype: '{result_key}'. Falling back to Neutral.")
                return "Neutral_Development"

        except Exception as e:
            logger.error(f"Gemini API Error: {e}. Falling back to Neutral_Development.")
            return "Neutral_Development"

    def run_monte_carlo(self, zone_name, intervention_name, live_weather, live_aqi,
                         target_year=2035, iterations=10000, random_seed=None):
        """Executes a stochastic simulation using LLM routing and live telemetry.

        Args:
            zone_name: Lucknow zone key (Gomti_Nagar, Hazratganj, Aminabad, Alambagh)
            intervention_name: User's free-text project proposal
            live_weather: dict with 'precip_mm' and 'temp_c' keys
            live_aqi: dict with 'current_aqi' key
            target_year: Future year for timeline projection
            iterations: Number of Monte Carlo samples (default 10,000)
            random_seed: Optional seed for reproducible results
        """
        start_time = time.perf_counter()

        # 1. Validate Inputs
        if zone_name not in self.zones:
            raise ValueError(f"Invalid Zone: '{zone_name}'. Valid zones: {list(self.zones.keys())}")

        zone = self.zones[zone_name]

        # 2. Let Gemini parse the user's raw text and pick the archetype
        matched_archetype_key = self._parse_intent(intervention_name)
        action = self.archetypes[matched_archetype_key]

        # 3. Telemetry Modifiers (Live Data scaling)
        density_mult = zone["density_km2"] / 5000.0
        precip_mult = 1.0 + (live_weather.get("precip_mm", 0) / 100.0)
        aqi_mult = 1.0 + (live_aqi.get("current_aqi", 100) / 500.0)

        years_passed = max(0, int(target_year) - 2025)
        timeline_growth = 1.0 + (years_passed * 0.03)

        # 4. Vectorized Monte Carlo — SEPARATE variance vectors per metric
        # Each metric gets its own noise profile since they have independent
        # stochastic behavior in real urban systems (traffic and revenue don't
        # move in lockstep).
        if random_seed is not None:
            np.random.seed(random_seed)

        noise_traffic   = np.random.normal(loc=1.0, scale=0.05, size=iterations)
        noise_revenue   = np.random.normal(loc=1.0, scale=0.05, size=iterations)
        noise_property  = np.random.normal(loc=1.0, scale=0.05, size=iterations)
        noise_runoff    = np.random.normal(loc=1.0, scale=0.05, size=iterations)
        noise_emergency = np.random.normal(loc=1.0, scale=0.05, size=iterations)
        noise_aqi       = np.random.normal(loc=1.0, scale=0.05, size=iterations)

        sim_traffic   = action["Traffic_Flow"] * density_mult * timeline_growth * noise_traffic
        sim_revenue   = action["Local_Revenue"] * timeline_growth * noise_revenue
        sim_property  = action["Property_Values"] * timeline_growth * noise_property
        sim_runoff    = action["Flood_Runoff"] * precip_mult * (zone["base_flood_risk"] * 2) * timeline_growth * noise_runoff
        sim_emergency = action["Emergency_Response"] * density_mult * timeline_growth * noise_emergency
        sim_aqi       = action["Air_Quality"] * aqi_mult * timeline_growth * noise_aqi

        # 5. Extract Statistical Percentiles
        results = {
            "Traffic_Flow":       {"median": float(np.percentile(sim_traffic, 50)),   "worst": float(np.percentile(sim_traffic, 95))},
            "Local_Revenue":      {"median": float(np.percentile(sim_revenue, 50)),    "worst": float(np.percentile(sim_revenue, 5))},
            "Property_Values":    {"median": float(np.percentile(sim_property, 50)),   "worst": float(np.percentile(sim_property, 5))},
            "Flood_Runoff":       {"median": float(np.percentile(sim_runoff, 50)),     "worst": float(np.percentile(sim_runoff, 95))},
            "Emergency_Response": {"median": float(np.percentile(sim_emergency, 50)),  "worst": float(np.percentile(sim_emergency, 95))},
            "Air_Quality":        {"median": float(np.percentile(sim_aqi, 50)),        "worst": float(np.percentile(sim_aqi, 5))}
        }

        # 6. Dynamic AI Mitigation Generation
        mitigations = []
        t = self.mitigation_thresholds
        if results["Flood_Runoff"]["worst"] > t["flood_runoff_worst"]:
            mitigations.append(f"CRITICAL: Extreme flood risk detected at {zone['density_km2']} density. Mandate 40% permeable pavement surfaces.")
        if results["Emergency_Response"]["worst"] > t["emergency_response_worst"]:
            mitigations.append(f"WARNING: Ambulance delays peak at +{results['Emergency_Response']['worst']:.1f} mins. Dedicate smart-transit lanes on arterial roads.")
        if results["Traffic_Flow"]["worst"] > t["traffic_flow_worst"]:
            mitigations.append(f"Congestion warning. Subsidize public transit passes for commercial employees in {zone_name.replace('_', ' ')}.")

        if not mitigations:
            mitigations.append("System structural integrity is stable. No severe mitigations required.")

        # 7. Format final payload
        formatted_metrics = {}
        for key, val in results.items():
            if key == "Emergency_Response":
                formatted_metrics[key] = f"{'+' if val['median'] > 0 else ''}{val['median']:.1f} mins"
            else:
                formatted_metrics[key] = f"{'+' if val['median'] > 0 else ''}{int(val['median'] * 100)}%"

        execution_time = (time.perf_counter() - start_time) * 1000

        return {
            "metrics": formatted_metrics,
            "statistical_confidence": "95%",
            "mitigation_strategies": mitigations,
            "engine_telemetry": {
                "iterations_run": iterations,
                "execution_time_ms": round(execution_time, 2),
                "archetype_used": matched_archetype_key,
                "random_seed": random_seed
            }
        }
