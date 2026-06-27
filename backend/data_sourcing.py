import os
from dotenv import load_module_or_variables

# Load variables from the local .env file
load_dotenv()

# Instantly assign them to engine runtime memory safely
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WAQI_API_KEY = os.getenv("WAQI_API_KEY")