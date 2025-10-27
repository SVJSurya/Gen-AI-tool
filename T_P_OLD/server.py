from flask import Flask, request, jsonify, render_template, session
# Ensure run_conversation is correctly imported
from app.utils import run_conversation
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder=os.path.join(os.getcwd(), 'templates'))
app.secret_key = os.getenv("FLASK_SECRET_KEY")

if not app.secret_key:
    raise ValueError("No FLASK_SECRET_KEY set in .env file. Required for session.")

print("\n--- Flask Server Initialized ---")
print("Ensure all agents (8001, 8002, 8003, 8004) are running!")

@app.route('/')
def index():
    # Clear session history when the page is loaded/reloaded
    session.pop('chat_history', None)
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('message')
    if not user_input:
        return jsonify({'response': "No message received.", 'structured_data': None}), 400

    # Get chat history from the user's session
    chat_history = session.get('chat_history', [])

    try:
        # Run conversation using Gemini
        # *** UPDATED: Handle three return values ***
        response_text, structured_data, updated_history = run_conversation(user_input, chat_history)

        # Save the updated history back to the session
        session['chat_history'] = updated_history

        # *** UPDATED: Return both text and structured data ***
        return jsonify({
            'response': response_text,
            'structured_data': structured_data # Pass agent JSON to frontend
        })

    except Exception as e:
        print(f"Error in /chat endpoint: {e}")
        # Optionally clear history on error
        # session.pop('chat_history', None)
        return jsonify({'response': f"An unexpected error occurred: {e}", 'structured_data': None}), 500

if __name__ == '__main__':
    # Make sure debug=True is appropriate for your environment
    app.run(port=5000, debug=True, threaded=False)