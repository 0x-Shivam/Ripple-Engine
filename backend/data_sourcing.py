import os
import requests
from dotenv import load_dotenv

# securly load env var 

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
WAQI_API_KEY = os.getenv("WAQI_API_KEY")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME")

# hard time out (prevent ui feezing if 3rd party fails/error)

REQUEST_TIMEOUT = 3.5

def fetch WEATHER_API_KEY