import os
import requests
import json
from dotenv import load_dotenv
import google.generativeai as genai
from datetime import datetime
import sys # Import sys for exiting on critical error

load_dotenv()

# --- CONFIGURATION & AGENT URLS ---
try:
    API_KEY = os.getenv("GOOGLE_API_KEY")
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not found in .env file")
    genai.configure(api_key=API_KEY)
except Exception as e:
    print(f"FATAL: Error configuring Gemini API: {e}")
    sys.exit(1) # Exit if API key is missing or invalid

FLIGHT_URL = os.getenv("FLIGHT_AGENT_URL", "http://localhost:8001/search_flights")
HOTEL_URL = os.getenv("HOTEL_AGENT_URL", "http://localhost:8002/search_hotels")
CAR_URL = os.getenv("CAR_AGENT_URL", "http://localhost:8004/search_cars")
ITINERARY_URL = os.getenv("ITINERARY_AGENT_URL", "http://localhost:8003/plan_itinerary")

# --- TOOL IMPLEMENTATION (Functions remain the same) ---
def search_flights(source: str, destination: str, date: str) -> str:
    try:
        # Basic date format validation before calling agent
        datetime.strptime(date, '%Y-%m-%d')
        response = requests.post(FLIGHT_URL, json={"source": source, "destination": destination, "date": date}, timeout=10)
        response.raise_for_status()
        return json.dumps(response.json())
    except ValueError:
         print(f"TOOL Error: Invalid date format '{date}' received for search_flights. Expected YYYY-MM-DD.")
         return json.dumps({"status": "error", "message": f"Invalid date format '{date}'. Please use YYYY-MM-DD."})
    except Exception as e: return json.dumps({"status": "error", "message": f"Flight agent connection error: {e}"})

def search_hotels(city: str, check_in: str, check_out: str, budget: str = None, room_preference: str = None) -> str:
    payload = {"city": city, "check_in": check_in, "check_out": check_out}
    if budget: payload["budget"] = budget
    if room_preference: payload["room_preference"] = room_preference
    try:
        response = requests.post(HOTEL_URL, json=payload, timeout=10)
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e: return json.dumps({"status": "error", "message": f"Hotel agent connection error: {e}"})

def find_car_rental(city: str, rental_date: str, vehicle_type: str = None, duration_hours: int = None) -> str:
    payload = {"city": city, "rental_date": rental_date}
    if vehicle_type: payload["vehicle_type"] = vehicle_type
    if duration_hours: payload["duration_hours"] = duration_hours
    try:
        response = requests.post(CAR_URL, json=payload, timeout=10)
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e: return json.dumps({"status": "error", "message": f"Car agent connection error: {e}"})

def plan_trip_itinerary(city: str, check_in_date: str, check_out_date: str, interests: str) -> str:
    try:
        response = requests.post(ITINERARY_URL, json={
            "destination_city": city, "check_in_date": check_in_date,
            "check_out_date": check_out_date, "interests": interests
        }, timeout=20)
        response.raise_for_status()
        return json.dumps(response.json())
    except Exception as e: return json.dumps({"status": "error", "message": f"Itinerary agent connection error: {e}"})

AVAILABLE_TOOLS = {
    "search_flights": search_flights,
    "search_hotels": search_hotels,
    "find_car_rental": find_car_rental,
    "plan_trip_itinerary": plan_trip_itinerary
}

# --- DEFINE TOOLS FOR GEMINI (Refined Flight Date Description) ---
GEMINI_TOOLS = [
    {
        "function_declarations": [
            {
                "name": "search_flights",
                # *** REFINED DESCRIPTION ***
                "description": "Searches for flight options. Requires source city, destination city, and the specific date in YYYY-MM-DD format. Ensure the date parameter strictly follows the YYYY-MM-DD format.",
                "parameters": { "type_": "OBJECT", "properties": {
                        "source": {"type_": "STRING"},
                        "destination": {"type_": "STRING"},
                        # *** REFINED DESCRIPTION ***
                        "date": {"type_": "STRING", "description": "The exact date of the flight in YYYY-MM-DD format."},
                    }, "required": ["source", "destination", "date"]
                }
            },
            { # Hotel Tool
                "name": "search_hotels",
                "description": "Searches for hotels. Requires city, check-in (YYYY-MM-DD), check-out (YYYY-MM-DD). If budget (e.g., 'budget', 'mid-range', 'luxury') OR room preference (e.g., 'single', 'double') is missing, ASK before calling.",
                "parameters": { "type_": "OBJECT", "properties": {
                        "city": {"type_": "STRING"},
                        "check_in": {"type_": "STRING", "description": "Date YYYY-MM-DD"},
                        "check_out": {"type_": "STRING", "description": "Date YYYY-MM-DD"},
                        "budget": {"type_": "STRING", "description": "Optional: 'budget', 'mid-range', or 'luxury'"},
                        "room_preference": {"type_": "STRING", "description": "Optional: 'single', 'double', 'suite'"}
                    }, "required": ["city", "check_in", "check_out"]
                }
            },
            { # Car Tool
                "name": "find_car_rental",
                "description": "Searches for car rentals. Requires city and rental date (YYYY-MM-DD). If vehicle type (e.g., 'car', 'suv', 'bike') OR duration (in hours, e.g., 48 for 2 days) is missing, ASK before calling.",
                "parameters": { "type_": "OBJECT", "properties": {
                        "city": {"type_": "STRING"},
                        "rental_date": {"type_": "STRING", "description": "Date YYYY-MM-DD"},
                        "vehicle_type": {"type_": "STRING", "description": "Optional: 'car', 'suv', 'bike'"},
                        "duration_hours": {"type_": "INTEGER", "description": "Optional: total hours"}
                    }, "required": ["city", "rental_date"]
                }
            },
             { # Itinerary Tool
                "name": "plan_trip_itinerary",
                "description": "Generates a detailed, daily itinerary. Requires city, check-in date (YYYY-MM-DD), check-out date (YYYY-MM-DD), and interests.",
                 "parameters": { "type_": "OBJECT", "properties": {
                        "city": {"type_": "STRING"},
                        "check_in_date": {"type_": "STRING", "description": "Start date YYYY-MM-DD"},
                        "check_out_date": {"type_": "STRING", "description": "End date YYYY-MM-DD"},
                        "interests": {"type_": "STRING", "description": "Comma-separated list (e.g., 'history, food')"},
                    }, "required": ["city", "check_in_date", "check_out_date", "interests"]
                }
            },
        ]
    }
]

# --- SYSTEM PROMPT (Remains the same as previous correct version) ---
current_date = datetime.now().strftime("%Y-%m-%d")
SYSTEM_PROMPT = (
    "You are Atlas, a friendly, helpful AI travel assistant. Your ONLY purpose is to assist users in planning trips by utilizing the provided tools for flights, hotels, car rentals, and itineraries. "
    f"Today's date is {current_date}. Always resolve relative dates (like 'tomorrow', 'next weekend') to this exact date in YYYY-MM-DD format before using any tool. "
    "\n**Mandatory Interaction Flow & Rules:**\n"
    "1. **Greeting:** Start politely.\n"
    "2. **Initial Query Handling:**\n"
    "   - If the user asks for something specific (e.g., 'find flights'), proceed directly to gather information for that tool (Rule #7).\n"
    "   - If the user's request is general (e.g., 'plan a trip'), **you MUST follow this sequence**: \n"
    "     a. Ask: 'First, would you like help finding flights for your trip?' If yes, gather details (Rule #7). If no, proceed.\n"
    "     b. Ask: 'Next, shall I look for hotel accommodations for you?' If yes, gather details (Rule #7).\n"
    "     c. Ask: 'Would you like me to create a suggested itinerary based on your interests?' If yes, gather details (Rule #7).\n"
    "     d. Ask: 'Finally, do you need assistance with booking a car rental?' If yes, gather details (Rule #7).\n"
    "3. **Tool Parameter Gathering (CRITICAL PRE-COMPUTATION):**\n"
    "   - **BEFORE calling `Google Hotels`**: You MUST explicitly ask the user for their budget preference ('budget', 'mid-range', or 'luxury'?) AND their room type preference ('single', 'double', 'suite'?) unless they have *already clearly stated both* in the current conversation turn or previous turns. Ask one question at a time.\n"
    "   - **BEFORE calling `find_car_rental`**: You MUST explicitly ask the user for their preferred vehicle type ('car', 'suv', or 'bike'?) AND the rental duration (e.g., 'for 3 days', '8 hours') unless they have *already clearly stated both*. Convert duration to total hours (e.g., '3 days' = 72 hours). Ask one question at a time.\n"
    "   - For ALL tools: Ensure ALL **required** parameters (like city, dates) are collected before calling. Ensure dates strictly follow YYYY-MM-DD format.\n"
    "4. **Off-Topic Refusal:** If asked anything unrelated to travel planning using the available tools, politely state: 'I can only assist with planning flights, hotels, car rentals, and itineraries. How can I help with your trip?' Do not answer other questions.\n"
    "5. **Result Presentation:** When a tool returns successful results (check the 'status' field in the tool response), clearly summarize the key findings for the user. Do not just output raw JSON data."
)

# --- CONVERSATION MANAGER (Added detailed error logging) ---
def run_conversation(user_input: str, chat_history: list):
    """
    Runs conversation, returns (final_response_text, structured_tool_result_json, updated_history)
    """
    model = genai.GenerativeModel(
        model_name="models/gemini-2.5-flash", # Using the confirmed model
        tools=GEMINI_TOOLS,
        system_instruction=SYSTEM_PROMPT
    )
    chat = model.start_chat(history=chat_history)
    print(f"\nUser Input: {user_input}")
    last_tool_json_result = None

    try:
        response = chat.send_message(user_input)
        # *** Check for immediate failure or blocking after sending ***
        if not response.candidates:
             print("--- GEMINI RESPONSE BLOCKED ---")
             print(f"Prompt Feedback: {response.prompt_feedback}")
             print("-------------------------------")
             # Try to get block reason
             block_reason = "Unknown"
             try:
                  block_reason = response.prompt_feedback.block_reason or "Reason not specified"
             except Exception:
                  pass
             error_response = f"My response was blocked, possibly due to safety filters: {block_reason}. Please rephrase your request."
             chat_history.append({"role": "user", "parts": [{"text": user_input}]})
             chat_history.append({"role": "model", "parts": [{"text": error_response}]})
             return error_response, None, chat_history

    except Exception as e:
        print(f"Error sending message to Gemini: {e}")
        return f"Sorry, error communicating with AI: {e}", None, chat_history

    # Tool-Calling Loop
    while (response.candidates and
           response.candidates[0].content.parts and
           hasattr(response.candidates[0].content.parts[0], 'function_call') and
           response.candidates[0].content.parts[0].function_call.name):

        # ... (Tool calling logic remains largely the same, ensure tool_response_str is handled) ...
        function_call = response.candidates[0].content.parts[0].function_call
        func_name = function_call.name
        func_args = function_call.args
        print(f"Gemini wants to call tool: {func_name} with args: {func_args}")
        last_tool_json_result = None

        if func_name in AVAILABLE_TOOLS:
            function_to_call = AVAILABLE_TOOLS[func_name]
            args_dict = {key: value for key, value in func_args.items()}
            try:
                tool_response_str = function_to_call(**args_dict)
                try:
                    parsed_response = json.loads(tool_response_str)
                    if parsed_response.get("status") == "success":
                        last_tool_json_result = parsed_response
                except json.JSONDecodeError:
                    print(f"Tool response for {func_name} was not valid JSON: {tool_response_str}")
            except Exception as e:
                print(f"Local tool execution error for {func_name}: {e}")
                tool_response_str = json.dumps({"status": "error", "message": f"Error during local execution: {e}"})

            print(f"Sending tool response to Gemini: {tool_response_str}")
            try:
                 response_content = json.loads(tool_response_str) # Assume it's valid JSON for sending back
                 response = chat.send_message(
                    {"function_response": {
                        "name": func_name,
                        "response": {"content": response_content}
                       }
                    }
                )
                 # *** Check for failure immediately after sending tool response ***
                 if not response.candidates:
                     print("--- GEMINI RESPONSE BLOCKED AFTER TOOL CALL ---")
                     print(f"Tool Response Sent: {tool_response_str}")
                     print(f"Prompt Feedback: {response.prompt_feedback}")
                     print("------------------------------------------")
                     block_reason = "Unknown"
                     try: block_reason = response.prompt_feedback.block_reason or "Reason not specified"
                     except Exception: pass
                     error_response = f"My response after processing tool results was blocked: {block_reason}."
                     chat_history.append({"role": "user", "parts": [{"text": user_input}]}) # Add user input again for context
                     chat_history.append({"role": "model", "parts": [{"text": error_response}]})
                     return error_response, last_tool_json_result, chat_history # Return the tool result for UI

            except json.JSONDecodeError:
                 print(f"Error: Tool response string was not valid JSON, sending as plain text.")
                 response = chat.send_message(
                    {"function_response": { "name": func_name, "response": {"content": tool_response_str} } }
                 )
            except Exception as e:
                print(f"Error sending tool response to Gemini: {e}")
                chat_history.append({"role": "user", "parts": [{"text": user_input}]})
                error_response = f"Sorry, error sending tool results back to AI: {e}"
                chat_history.append({"role": "model", "parts": [{"text": error_response}]})
                return error_response, None, chat_history
        else:
            # ... (Unknown tool handling) ...
            print(f"Error: Gemini tried to call unknown tool '{func_name}'")
            chat_history.append({"role": "user", "parts": [{"text": user_input}]})
            error_response = "I tried to use a tool that doesn't exist."
            chat_history.append({"role": "model", "parts": [{"text": error_response}]})
            return error_response, None, chat_history

    # Get final text response with enhanced error checking
    final_response_text = "Sorry, I encountered an issue generating a response." # Default error
    try:
        # Check finish reason if available
        finish_reason = response.candidates[0].finish_reason
        if finish_reason not in [1, "STOP"]: # 1 is the enum value for STOP
             print(f"--- WARNING: Gemini finished with reason: {finish_reason} ---")
             # Try to get more details if stopped for safety etc.
             if finish_reason in [3, 4, "SAFETY", "RECITATION"]: # Safety or Recitation
                 safety_ratings = response.candidates[0].safety_ratings
                 print(f"Safety Ratings: {safety_ratings}")
                 final_response_text = f"My response was stopped due to content policy ({finish_reason}). Please rephrase."
             else:
                 final_response_text = f"The response generation finished unexpectedly (Reason: {finish_reason}). Please try again."
             # Do not proceed to extract text if finish reason is bad

        else: # Normal STOP reason
            # Extract text safely
            text_parts = [part.text for part in response.candidates[0].content.parts if hasattr(part, 'text')]
            final_response_text = ''.join(text_parts)
            if not final_response_text:
                # This case might happen if finish_reason is STOP but content is empty
                print("Warning: Gemini response finished normally but had no text content.")
                final_response_text = "I processed your request, but didn't generate a text response."

    except (AttributeError, IndexError, ValueError) as e:
         print(f"Error parsing final Gemini response: {e}. Raw Response: {response}")
         final_response_text = "Sorry, I had trouble parsing the final response from the AI."
    except Exception as e:
         print(f"Unexpected error extracting final text response: {e}")
         final_response_text = "Sorry, an unexpected error occurred while extracting the final response."


    # Update history
    chat_history.append({"role": "user", "parts": [{"text": user_input}]})
    chat_history.append({"role": "model", "parts": [{"text": final_response_text}]})

    return final_response_text, last_tool_json_result, chat_history