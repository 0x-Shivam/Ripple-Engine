# Ripple Engine

**Fix Issue before they built.**

Ripple Engine is an  digital twin for urban planning. It allows city planners to type infrastructure proposals in plain English and instantly see the statistical ripple effects on traffic, flooding, and the local economy years into the future.

## Why I Built It
**Tested Infrastructure:** Building without a predictive plan is like deploying untested code. I believe we must test the architecture before we build it.

**The Butterfly Effect:** A single mall can cause flooding three neighbourhoods away. I built this engine to simulate those exact ripple effects and patch vulnerabilities early.

## How It Works
1. **Semantic Routing:** You type a natural language proposal (e.g., *"Build an underground metro hub"*). The backend uses Google Gemini 2.5 Flash to instantly understand the intent and map it to a structural archetype.
2. **Monte Carlo Engine:** A custom NumPy simulation runs 10,000 stochastic permutations in under 400ms to calculate the 95th-percentile worst-case scenarios for the city.
3. **Live Telemetry:** The engine pulls live regional weather (precipitation/temperature) and Air Quality Index (AQI) data to dynamically handicap the mathematical models in real-time.

## Tech Stack
* **Frontend:** HTML, JavaScript, Tailwind CSS (Hosted on Vercel)
* **Backend:** Python, FastAPI, NumPy (Containerized with Docker, Hosted on Railway)
* **AI & Data APIs:** * Google Gemini 2.5 Flash (Semantic Routing)
  * WeatherAPI & WAQI (Live Environmental Telemetry)
  * GeoNames (Demographic Anchors)


## MVP Scope & Locked Features (V2 Roadmap)
For this hackathon submission, the application is a highly focused Minimum Viable Product (MVP). To ensure accurate statistical models, several UI elements are currently locked and reserved for V2:

* **Geographic Lock:** The engine is currently heavily calibrated for **Lucknow, UP**. Selecting other cities in the dropdown is disabled.
* **Time-Series Graphs:** The "Impact Over Time" tab is a UI placeholder. Currently, the engine outputs overall statistical impacts, but visual charting will be added in the next update.
* **PDF Export:** The "View Full Impact Report" button is locked. 
* **Financial APIs:** Future versions will integrate real municipal budget APIs to provide exact monetary forecasting alongside the environmental data.

## Running Locally

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/yourusername/ripple-engine.git](https://github.com/yourusername/ripple-engine.git)
   cd ripple-engine