import random
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()
app = FastAPI()

# --- Mock Data ---
MOCK_AIRLINES = {
    "Indigo": "I",
    "Spicejet": "SP",
    "Vistara": "VI",
    "Air India": "AI",
    "Akasa Air": "AK"
}

# --- Pydantic Schema for Request Body ---
class FlightRequest(BaseModel):
    source: str
    destination: str
    date: str

# --- Helper Function for Mock Data ---
def generate_mock_flights(source: str, destination: str, date: str):
    """Generates a list of realistic mock flights."""
    results = []
    airline_names = list(MOCK_AIRLINES.keys())
    
    # Generate 3 to 5 flight options
    for _ in range(random.randint(3, 5)):
        airline = random.choice(airline_names)
        airline_code = MOCK_AIRLINES[airline]
        flight_num = f"{airline_code}{random.randint(100, 999)}"
        
        # Generate a random departure time
        base_time = datetime.strptime(date, "%Y-%m-%d")
        departure_dt = base_time + timedelta(
            hours=random.randint(5, 22),
            minutes=random.choice([0, 15, 30, 45])
        )
        
        # Generate random price
        price = random.randint(4500, 20000)

        # ✅ FIX: Include both 'departure' and 'departure_time'
        departure_str = departure_dt.strftime("%Y-%m-%d %H:%M")
        results.append({
            "airline": airline,
            "flight_number": flight_num,
            "source": source.title(),
            "destination": destination.title(),
            "departure": departure_str,        # existing key
            "departure_time": departure_str,   # new key for summary compatibility
            "price": price
        })
    
    return results


# --- FastAPI Endpoint (The actual service) ---
@app.post("/search_flights")
def search_flights_endpoint(request: FlightRequest):
    """
    Endpoint called by the Orchestrator via HTTP POST.
    Generates mock flight data.
    """
    print(f"Flight Agent received request: {request.model_dump()}")
    
    # Generate mock flights
    flights = generate_mock_flights(
        request.source, 
        request.destination,
        request.date
    )

    if not flights:
        return {"status": "error", "message": "No mock flights could be generated."}
        
    # Sort by price, as requested
    sorted_flights = sorted(flights, key=lambda x: x['price'])
    
    # Return a structured result
    return {"status": "success", "results": sorted_flights}

# --- Run Command ---
# uvicorn agents.flight_agent:app --port 8001 --reload