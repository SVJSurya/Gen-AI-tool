import os
import requests
import random
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from urllib.parse import quote

load_dotenv()
app = FastAPI()

# --- Geoapify Configuration ---
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"

if not GEOAPIFY_API_KEY:
    print("FATAL: GEOAPIFY_API_KEY not found in .env. Hotel agent WILL NOT WORK.")
    # This agent is not useful without the key
    # You could raise an error here to stop it from running

# --- Pydantic Schema for Request Body ---
# This matches the tool definition in utils.py
class HotelRequest(BaseModel):
    city: str
    check_in: str
    check_out: str
    budget: str | None = None
    room_preference: str | None = None

# --- Helper Function: Get City Coordinates ---
def get_city_coordinates(city_name: str):
    """Fetches latitude and longitude for a city using Geoapify Geocoding."""
    if not GEOAPIFY_API_KEY:
        return None, None, "Geoapify API key not configured."

    params = {
        'text': city_name,
        'limit': 1,
        'apiKey': GEOAPIFY_API_KEY
    }
    try:
        response = requests.get(GEOAPIFY_GEOCODE_URL, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data.get('features') and len(data['features']) > 0:
            coords = data['features'][0]['geometry']['coordinates']
            # Geoapify returns lon, lat
            return coords[1], coords[0], None # Return lat, lon, error
        else:
            return None, None, f"Could not find coordinates for city '{city_name}'."
    except requests.exceptions.RequestException as e:
        print(f"Error calling Geoapify Geocode API: {e}")
        return None, None, f"Network error during geocoding: {e}"

# --- Helper Function: Fetch Hotels from Geoapify ---
def fetch_hotels_from_api(lat, lon, budget: str | None, city_name: str):
    """Fetches hotels near coordinates using Geoapify Places."""
    if not GEOAPIFY_API_KEY:
        return [], "Geoapify API key not configured."

    params = {
        'categories': 'accommodation.hotel',
        'filter': f'circle:{lon},{lat},10000', # Search within 10km radius
        'limit': 15, # Get up to 15 results
        'apiKey': GEOAPIFY_API_KEY
    }
    
    try:
        response = requests.get(GEOAPIFY_PLACES_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        hotels = []

        if not data.get('features'):
            return [], None # No error, just no hotels found

        for feature in data['features']:
            props = feature.get('properties', {})
            name = props.get('name')
            
            # Skip if there's no hotel name
            if not name:
                continue

            # Mock price based on budget
            budget_normalized = budget.lower() if budget else 'mid-range'
            if budget_normalized == 'budget':
                price = random.randint(2000, 4500)
            elif budget_normalized == 'luxury':
                price = random.randint(10000, 25000)
            else: # 'mid-range' or other
                price = random.randint(4500, 9500)

            # Generate a reliable search link as requested
            website = props.get('website')
            if not website:
                safe_query = quote(f"{name} {city_name}")
                website = f"https://www.google.com/search?q={safe_query}"

            hotels.append({
                "name": name,
                "address": props.get('formatted', 'Address not available'),
                "rating": round(random.uniform(3.5, 5.0), 1), # Mock rating as it's often missing
                "price_per_night": price,
                "link": website
            })
        
        return hotels, None

    except requests.exceptions.RequestException as e:
        print(f"Error calling Geoapify Places API: {e}")
        return [], f"Network error during hotel search: {e}"
    except Exception as e:
        print(f"Error processing places response: {e}")
        return [], f"Error processing hotel data: {e}"

# --- FastAPI Endpoint (The actual service) ---
@app.post("/search_hotels")
def search_hotels_endpoint(request: HotelRequest):
    """
    Endpoint for Hotel Search.
    """
    print(f"Hotel Agent received request: {request.model_dump()}")

    # 1. Get Coordinates for the city
    lat, lon, geo_error = get_city_coordinates(request.city)
    if geo_error:
         return {"status": "error", "message": geo_error}

    # 2. Fetch hotels from API
    hotels, poi_error = fetch_hotels_from_api(lat, lon, request.budget, request.city)
    if poi_error:
        return {"status": "error", "message": poi_error}
    
    if not hotels:
        return {"status": "success", "results": []} # Return success with empty list

    # 3. Sort results by price (as requested)
    sorted_hotels = sorted(hotels, key=lambda x: x['price_per_night'])

    return {"status": "success", "results": sorted_hotels}

# --- Run Command ---
# uvicorn agents.hotel_agent:app --port 8002 --reload