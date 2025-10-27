import os
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random

load_dotenv()
app = FastAPI()

# --- Geoapify Configuration ---
GEOAPIFY_API_KEY = os.getenv("GEOAPIFY_API_KEY")
GEOAPIFY_GEOCODE_URL = "https://api.geoapify.com/v1/geocode/search"
GEOAPIFY_PLACES_URL = "https://api.geoapify.com/v2/places"

if not GEOAPIFY_API_KEY:
    print("WARNING: GEOAPIFY_API_KEY not found in .env. Itinerary agent will likely fail.")
    # Consider raising an error or exiting if the key is essential

# --- Helper Function: Get City Coordinates ---
def get_city_coordinates(city_name: str):
    """Fetches latitude and longitude for a city using Geoapify Geocoding."""
    if not GEOAPIFY_API_KEY:
        return None, None, "API key not configured."

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
    except Exception as e:
        print(f"Error processing geocode response: {e}")
        return None, None, f"Error processing geocode data: {e}"

# --- Helper Function: Fetch POIs from Geoapify ---
def fetch_pois_from_api(lat, lon, interests: list):
    """Fetches POIs near coordinates based on interest categories using Geoapify Places."""
    if not GEOAPIFY_API_KEY:
        return [], "API key not configured."

    # Map general interests to Geoapify categories (adjust as needed)
    category_map = {
        'history': 'historic',
        'food': 'catering',
        'nature': 'natural',
        'shopping': 'commercial',
        'beach': 'beach',
        'culture': 'entertainment', # Broad category, might include museums, theatres
        'art': 'entertainment.culture',
        'museum': 'entertainment.museum',
        # Add more mappings
    }
    categories = set()
    for interest in interests:
        mapped = category_map.get(interest.strip().lower())
        if mapped:
            categories.add(mapped)
        elif interest == 'general': # Add some defaults for 'general'
            categories.update(['tourism', 'catering'])

    if not categories:
        return [], f"Could not map interests '{', '.join(interests)}' to API categories."

    pois = []
    errors = []

    # Make separate API calls for each category to ensure variety
    # You might want to limit the number of categories queried if interests list is long
    for category in list(categories)[:3]: # Limit to 3 categories per request for brevity
        params = {
            'categories': category,
            'filter': f'circle:{lon},{lat},10000', # Search within 10km radius
            'limit': 10, # Get up to 10 results per category
            'apiKey': GEOAPIFY_API_KEY
        }
        try:
            response = requests.get(GEOAPIFY_PLACES_URL, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('features'):
                for feature in data['features']:
                    props = feature.get('properties', {})
                    pois.append({
                        "name": props.get('name', props.get('address_line1', 'Unknown Place')),
                        "type": props.get('categories', [category])[0].split('.')[0], # Simplified type
                        "duration": "N/A", # Geoapify doesn't provide this directly
                        "cost": "N/A",     # Geoapify doesn't provide this directly
                        # Optional: Add address if needed: props.get('formatted', '')
                    })
            # Give specific error if API fails for a category
            elif response.status_code != 200:
                 errors.append(f"API error for category '{category}': Status {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"Error calling Geoapify Places API for {category}: {e}")
            errors.append(f"Network error for category '{category}'")
            # Don't stop if one category fails, try others
        except Exception as e:
            print(f"Error processing places response for {category}: {e}")
            errors.append(f"Processing error for category '{category}'")

    # Combine errors into a single message if any occurred
    error_message = "; ".join(errors) if errors else None
    return list({poi['name']: poi for poi in pois}.values()), error_message # Deduplicate by name

# --- Updated Itinerary Planning Logic ---
def get_trip_duration(start_date_str, end_date_str):
    """Calculates the number of full days in the trip (inclusive)."""
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        duration = (end_date - start_date).days + 1
        return max(1, duration)
    except (ValueError, TypeError):
        print(f"Error parsing dates: {start_date_str}, {end_date_str}")
        return 1

def plan_itinerary_with_api(context: dict) -> dict:
    """
    Generates itinerary using Geoapify API based on interests, duration, and city.
    """
    city_name = context.get('destination_city')
    start_date_str = context.get('check_in_date')
    end_date_str = context.get('check_out_date')
    interests_str = context.get('interests', 'general')

    if not city_name or not start_date_str or not end_date_str:
        return {"error": "Missing city or dates for itinerary planning."}

    # 1. Get Coordinates
    lat, lon, geo_error = get_city_coordinates(city_name)
    if geo_error:
        return {"error": geo_error}

    interests = [i.strip().lower() for i in interests_str.split(',')]
    duration_days = get_trip_duration(start_date_str, end_date_str)
    itinerary = {}

    # 2. Fetch POIs from API
    relevant_pois, poi_error = fetch_pois_from_api(lat, lon, interests)
    if poi_error and not relevant_pois: # If errors occurred AND we got no POIs at all
        return {"error": f"Failed to fetch activities: {poi_error}"}
    elif not relevant_pois:
         return {"error": f"Could not find activities in {city_name} matching interests: {interests_str}."}

    # 3. Assign POIs to Days (Using the same logic as before)
    random.shuffle(relevant_pois)
    pois_per_day = 2 # Target number of activities per day
    assigned_poi_names_overall = set()
    available_pois = relevant_pois[:]

    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')

    for day_num in range(duration_days):
        current_date = start_date + timedelta(days=day_num)
        day_label = f"Day {day_num + 1} ({current_date.strftime('%a, %b %d')})"
        itinerary[day_label] = []
        added_today = 0
        used_indices_today = []

        for i, poi in enumerate(available_pois):
            time_slot = "Morning" if added_today == 0 else "Afternoon/Evening"
            itinerary[day_label].append({
                 "time": time_slot,
                 "name": poi["name"],
                 "type": poi.get("type", "Activity"),
                 "duration": poi.get("duration", "N/A"), # Will be N/A from API
                 "cost": poi.get("cost", "N/A")      # Will be N/A from API
            })
            assigned_poi_names_overall.add(poi['name'])
            used_indices_today.append(i)
            added_today += 1
            if added_today >= pois_per_day:
                break

        available_pois = [poi for i, poi in enumerate(available_pois) if i not in used_indices_today]

        # Handle cases where not enough unique POIs were found
        if added_today == 0:
             itinerary[day_label].append({
                "time": "Full Day", "name": f"Explore {city_name} / Local Markets",
                "type": "Leisure/Shopping", "duration": "Variable", "cost": "Variable"
            })
        elif added_today < pois_per_day:
             itinerary[day_label].append({
                "time": "Evening", "name": f"Relax / Dinner in {city_name}",
                "type": "Leisure/Food", "duration": "Variable", "cost": "Variable"
             })

        # Simple refill (can be improved)
        if not available_pois and day_num < duration_days - 1:
            print("Refilling POI pool from API results (may cause repeats)")
            available_pois = [p for p in relevant_pois if p['name'] not in assigned_poi_names_overall]
            random.shuffle(available_pois)
            if not available_pois: # If truly exhausted unique POIs from API call
                 available_pois = relevant_pois[:] # Allow repeats
                 random.shuffle(available_pois)

    # Add API errors as a note if some categories failed but we still got results
    if poi_error:
        itinerary["Note"] = f"Could not fetch suggestions for all interests due to: {poi_error}"


    return itinerary

# --- Pydantic Schema ---
class ItineraryRequest(BaseModel):
    destination_city: str
    check_in_date: str
    check_out_date: str
    interests: str = 'general' # Default interest

# --- FastAPI Endpoint ---
@app.post("/plan_itinerary")
def plan_itinerary_endpoint(request: ItineraryRequest):
    """
    Endpoint for Itinerary Planning, calls the API-based planner.
    """
    print(f"Itinerary Agent received request: {request.model_dump()}")
    context = request.model_dump()
    # Call the API-based planning function
    results = plan_itinerary_with_api(context)

    if isinstance(results, dict) and results.get('error'):
         # Return specific error message
         return {"status": "error", "message": results['error']}
    if not results: # Handle empty dict case
         return {"status": "error", "message": "Failed to generate itinerary, results empty."}

    # Add note to results if present
    final_results = results
    note = results.pop("Note", None) # Remove Note from main results if it exists

    response_payload = {"status": "success", "results": final_results}
    if note:
        response_payload["note"] = note # Add note separately for clarity

    return response_payload

# --- Run Command ---
# uvicorn agents.itinerary_agent:app --port 8003 --reload