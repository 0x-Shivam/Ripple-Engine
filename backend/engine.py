import networkx as nx
import numpy as np
import time
import os
import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    configure_fn = getattr(genai, "configure", None)
    if callable(configure_fn):
        configure_fn(api_key=GEMINI_API_KEY)

class UrbanCascadeEngine:
    def __init__(self):
        print(" Initializing Urban Cascade Monte Carlo Engine...")
        self.graph = nx.DiGraph()
        
        # Real-World Demographic Baselines
        self.zones = {
            "Gomti_Nagar": {"population": 450000, "density_km2": 4200, "base_flood_risk": 0.3},
            "Hazratganj": {"population": 210000, "density_km2": 11500, "base_flood_risk": 0.5},
            "Aminabad": {"population": 320000, "density_km2": 18000, "base_flood_risk": 0.7},
            "Alambagh": {"population": 280000, "density_km2": 8500, "base_flood_risk": 0.4}
        }
        
        # The Mathematical Archetypes for the LLM to route to
        self.archetypes = {
            "Commercial_Heavy": {"Traffic_Flow": 0.18, "Local_Revenue": 0.15, "Property_Values": 0.10, "Flood_Runoff": 0.08, "Emergency_Response": 1.5, "Air_Quality": -0.12},
            "Transit_Hub": {"Traffic_Flow": -0.20, "Local_Revenue": 0.18, "Property_Values": 0.25, "Flood_Runoff": 0.03, "Emergency_Response": -2.0, "Air_Quality": 0.20},
            "Green_Ecology": {"Traffic_Flow": -0.05, "Local_Revenue": 0.08, "Property_Values": 0.18, "Flood_Runoff": -0.30, "Emergency_Response": 0.0, "Air_Quality": 0.35},
            "Utility_Underground": {"Traffic_Flow": 0.15, "Local_Revenue": 0.05, "Property_Values": 0.12, "Flood_Runoff": -0.65, "Emergency_Response": 0.1, "Air_Quality": 0.05},
            "Neutral_Development": {"Traffic_Flow": 0.05, "Local_Revenue": 0.05, "Property_Values": 0.05, "Flood_Runoff": 0.02, "Emergency_Response": 0.2, "Air_Quality": -0.02}
        }

    def _parse_intent(self, raw_text):
        """Uses Gemini 1.5 Flash to semantically route the user's free text to a math model."""
        if not GEMINI_API_KEY or not raw_text.strip():
            print(" No Gemini Key found or empty text. Defaulting to Neutral.")
            return "Neutral_Development"
            
        try:
            # We use flash because we need this to process in <1 second for a snappy UI
            prompt = f"""
            You are a backend routing AI for a city planning simulation.
            Analyze this user proposal: "{raw_text}"
            
            Classify it into EXACTLY ONE of these categories:
            - Commercial_Heavy (malls, towers, factories, commerce)
            - Transit_Hub (roads, metro, transport, vehicles)
            - Green_Ecology (parks, planting trees, environmental)
            - Utility_Underground (water pipes, sewers, electrical grids)
            - Neutral_Development (if vague, unknown, or unrelated)
            
            Return ONLY the exact category name string. No markdown, no punctuation, no explanation.
            """

            if hasattr(genai, "GenerativeModel"):
                model = genai.GenerativeModel('gemini-2.5-flash')
                response = model.generate_content(prompt)
            elif hasattr(genai, "generate_text"):
                response = genai.generate_text(model='gemini-1.5-flash', prompt=prompt)
            else:
                raise RuntimeError("Unsupported google.generativeai API version")

            if hasattr(response, "text"):
                result_key = response.text.strip()
            elif hasattr(response, "content"):
                result_key = response.content.strip()
            else:
                result_key = str(response).strip()
            
            # Safety check: If Gemini hallucinates, fallback to Neutral safely
            if result_key in self.archetypes:
                print(f" Gemini routed '{raw_text}' -> {result_key}")
                return result_key
            else:
                return "Neutral_Development"
                
        except Exception as e:
            print(f" Gemini API Error: {e}")
            return "Neutral_Development"

    def run_monte_carlo(self, zone_name, intervention_name, live_weather, live_aqi, target_year=2035, iterations=10000):
        """Executes a 10,000-pass stochastic simulation using LLM routing and live telemetry."""
        start_time = time.perf_counter()

        # 1. Validate Inputs
        if zone_name not in self.zones:
            raise ValueError("Invalid Zone Request")
            
        zone = self.zones[zone_name]
        
        # 2. Let Gemini parse the user's raw text and pick the action
        matched_archetype_key = self._parse_intent(intervention_name)
        action = self.archetypes[matched_archetype_key]
        
        # 3. Telemetry Modifiers (Live Data scaling)
        density_mult = zone["density_km2"] / 5000.0 
        precip_mult = 1.0 + (live_weather.get("precip_mm", 0) / 100.0)
        aqi_mult = 1.0 + (live_aqi.get("current_aqi", 100) / 500.0)
        
        years_passed = max(0, int(target_year) - 2025)
        timeline_growth = 1.0 + (years_passed * 0.03)

        # 4. Vectorized Monte Carlo Pass
        variance_matrix = np.random.normal(loc=1.0, scale=0.05, size=iterations)

        sim_traffic = action["Traffic_Flow"] * density_mult * timeline_growth * variance_matrix
        sim_revenue = action["Local_Revenue"] * timeline_growth * variance_matrix
        sim_property = action["Property_Values"] * timeline_growth * variance_matrix
        sim_runoff = action["Flood_Runoff"] * precip_mult * (zone["base_flood_risk"] * 2) * timeline_growth * variance_matrix
        sim_emergency = action["Emergency_Response"] * density_mult * timeline_growth * variance_matrix
        sim_aqi = action["Air_Quality"] * aqi_mult * timeline_growth * variance_matrix

        # 5. Extract Statistical Percentiles
        results = {
            "Traffic_Flow": {"median": np.percentile(sim_traffic, 50), "worst": np.percentile(sim_traffic, 95)},
            "Local_Revenue": {"median": np.percentile(sim_revenue, 50), "worst": np.percentile(sim_revenue, 5)},
            "Property_Values": {"median": np.percentile(sim_property, 50), "worst": np.percentile(sim_property, 5)},
            "Flood_Runoff": {"median": np.percentile(sim_runoff, 50), "worst": np.percentile(sim_runoff, 95)},
            "Emergency_Response": {"median": np.percentile(sim_emergency, 50), "worst": np.percentile(sim_emergency, 95)},
            "Air_Quality": {"median": np.percentile(sim_aqi, 50), "worst": np.percentile(sim_aqi, 5)} 
        }

        # 6. Dynamic AI Mitigation Generation
        mitigations = []
        if results["Flood_Runoff"]["worst"] > 0.15:
            mitigations.append(f"CRITICAL: Extreme flood risk detected at {zone['density_km2']} density. Mandate 40% permeable pavement surfaces.")
        if results["Emergency_Response"]["worst"] > 2.0:
            mitigations.append(f"WARNING: Ambulance delays peak at +{results['Emergency_Response']['worst']:.1f} mins. Dedicate smart-transit lanes on arterial roads.")
        if results["Traffic_Flow"]["worst"] > 0.25:
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
                "execution_time_ms": round(execution_time, 2)
            }
        }