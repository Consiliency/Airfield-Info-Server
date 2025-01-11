import requests
import os
from datetime import datetime

def test_timezone_api(lat, lon, api_key):
    # Get current timestamp
    timestamp = int(datetime.now().timestamp())
    
    # Construct the API URL
    url = f"https://maps.googleapis.com/maps/api/timezone/json?location={lat},{lon}&timestamp={timestamp}&key={api_key}"
    
    # Make the request
    response = requests.get(url)
    print(f"Testing coordinates: {lat}, {lon}")
    print(f"API Response Status: {response.status_code}")
    print(f"API Response: {response.json()}")

if __name__ == "__main__":
    # SNA coordinates
    lat = 33.675701
    lon = -117.867996
    
    # Get API key from environment
    api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    
    if not api_key:
        print("Error: GOOGLE_MAPS_API_KEY environment variable not set")
        exit(1)
    
    test_timezone_api(lat, lon, api_key) 