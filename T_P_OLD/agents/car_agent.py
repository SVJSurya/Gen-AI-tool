from fastapi import FastAPI
from pydantic import BaseModel
from data.db import VEHICLE_DATABASE 
import random # Used for mock total cost calculation if hours aren't provided

app = FastAPI()

class CarRequest(BaseModel):
    city: str
    rental_date: str
    vehicle_type: str | None = None # <-- ADDED optional
    duration_hours: int | None = None # <-- ADDED optional

@app.post("/search_cars")
def search_cars_endpoint(request: CarRequest):
    print(f"Car Agent received request: {request.model_dump()}") # Log received data
    # Use provided duration or default to 48 hours
    hours = request.duration_hours if request.duration_hours else 48
    results = []
    for vehicle in VEHICLE_DATABASE:
        type_match = True
        if request.vehicle_type and vehicle["type"].lower() != request.vehicle_type.lower():
            type_match = False

        if (
            vehicle["location"].lower() == request.city.lower() and
            vehicle["available"] and type_match
        ):
            total_cost = vehicle["price_per_hour"] * hours
            results.append({
                "name": vehicle["name"], "type": vehicle["type"],
                "capacity": vehicle["capacity"],
                "daily_rate": vehicle['price_per_hour'] * 24,
                "total_cost_for_trip": total_cost # Example total cost
            })

    return {"status": "success", "results": results}