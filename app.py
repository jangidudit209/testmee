import os
import json
import requests
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS # To handle Cross-Origin Resource Sharing for frontend

app = Flask(__name__)
CORS(app) # Enable CORS for your frontend to access this API

BATCH_FILE = "batches.json"

# --- Helper function to load batches.json ---
def load_batches():
    try:
        with open(BATCH_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {BATCH_FILE} not found. Please ensure it exists.")
        return {}
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {BATCH_FILE}. Check file format.")
        return {}

# --- API Endpoint 1: Serve the batches.json structure ---
@app.route('/api/batches_structure', methods=['GET'])
def get_batches_structure():
    batches = load_batches()
    # We only send the structure, not the actual lecture links yet
    # The frontend will use this to build the navigation (categories, batches, subjects)
    # The 'uids' are kept as they are needed for the next step
    return jsonify(batches)

# --- API Endpoint 2: Fetch lectures using UIDs (integrating your bot.py logic) ---
@app.route('/api/fetch_lectures', methods=['POST'])
def fetch_lectures_api():
    data = request.get_json()
    uids = data.get('uids')

    if not uids:
        return jsonify({"error": "No UIDs provided"}), 400

    all_videos = []
    all_pdfs = []

    def fetch_all_lectures_from_unacademy(uid):
        all_results = []
        url = f"https://unacademy.com/api/v3/collection/{uid}/items?limit=600"
        while url:
            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                data = r.json()
                all_results.extend(data.get("results", []))
                url = data.get("next")
            except Exception as e:
                print(f"Error fetching UID {uid}: {e}")
                break
        return all_results

    for uid in uids:
        results = fetch_all_lectures_from_unacademy(uid)
        for item in results:
            val = item.get("value", {})
            title = val.get("title", "No Title")
            live_class = val.get("live_class", {})
            
            if live_class is None:
                continue # Skip if live_class is None

            # Extract teacher and date (optional for frontend display)
            author = live_class.get("author", {})
            teacher = f"{author.get('first_name','')} {author.get('last_name','')}".strip()
            date_str = live_class.get("live_at", "")
            
            # You might want to add date filtering here if needed,
            # but for simplicity, we'll fetch all available for the UID.
            
            vurl = live_class.get("video_url", "") or ""
            pdf = live_class.get("slides_pdf", {}).get("with_annotation", "") if live_class.get("slides_pdf") else ""

            if vurl and "uid=" in vurl:
                # Reconstruct the direct video URL as in your bot.py
                uid2 = vurl.split("uid=")[1].split("&")[0]
                direct_video_url = f"https://uamedia.uacdn.net/lesson-raw/{uid2}/output.webm"
                all_videos.append({
                    "title": title,
                    "url": direct_video_url,
                    "thumbnail": val.get("thumbnail_url"), # Unacademy often provides thumbnails
                    "duration": "N/A", # You might need to scrape this or estimate
                    "source": "Unacademy",
                    "teacher": teacher,
                    "date": date_str # Keep original date string
                })
            if pdf:
                all_pdfs.append({
                    "title": title,
                    "url": pdf,
                    "thumbnail": val.get("thumbnail_url"), # Unacademy often provides thumbnails
                    "size": "N/A", # You might need to scrape this or estimate
                    "pages": "N/A", # You might need to scrape this or estimate
                    "source": "Unacademy",
                    "teacher": teacher,
                    "date": date_str
                })
    
    return jsonify({"videos": all_videos, "pdfs": all_pdfs})

# --- Serve static files (your index.html, CSS, JS) ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# If you have other static files (like images in a 'static' folder)
# @app.route('/<path:path>')
# def serve_static(path):
#     return send_from_directory('.', path)

if __name__ == '__main__':
    # Create a dummy batches.json if it doesn't exist for testing
    if not os.path.exists(BATCH_FILE):
        dummy_batches = {
            "Sample Batch 1": {
                "category": "Demo Category",
                "subjects": {
                    "Demo Subject A": {
                        "uids": ["76O3VNLX"], # Replace with a real UID for testing
                        "name": "Demo Subject A"
                    },
                    "Demo Subject B": {
                        "uids": ["W79Z40CU"], # Replace with another real UID
                        "name": "Demo Subject B"
                    }
                }
            }
        }
        with open(BATCH_FILE, "w", encoding="utf-8") as f:
            json.dump(dummy_batches, f, indent=4)
        print(f"Created a dummy {BATCH_FILE} for testing.")

    app.run(debug=True, port=5000) # Run on port 5000, debug=True for development
