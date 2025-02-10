from flask import Flask, request, render_template, redirect, session, jsonify 
# Flask → Creates the web application.
# request → Handles incoming user requests (like form submissions).
# render_template → Loads HTML templates.
# redirect → Redirects users from one page to another.
# session → Stores user login information.
# jsonify → Converts Python data into JSON format for API responses.

from flask_sqlalchemy import SQLAlchemy # SQLAlchemy → A database library to store user data.
from flask_cors import CORS # CORS → Allows the frontend (if it's on a different domain) to interact with the Flask API.
from rev_ai import apiclient # apiclient (Rev AI) → Used for speech-to-text processing.
from deep_translator import GoogleTranslator, exceptions  # GoogleTranslator → Handles text translation.
import bcrypt # bcrypt → Encrypts passwords for security.
import os
import time
import logging # os, time, logging → System utilities for file handling, delays, and logging errors.

# Initialize Flask app
app = Flask(__name__)
CORS(app) # Enables Cross-Origin Resource Sharing
app.secret_key = '583eccd0ed17d07012ee047b448817da037d81812d79ed693d5c4208a42cf81c' # Secret key for session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db' # Configuring the database

db = SQLAlchemy(app) # Initializing the database

# Rev AI API Client
REV_AI_API_KEY = "02GX5Lx4PLmnyV7ZMQA2C_Iyy4dt3kY94-8RUMAvnvD3Q-4HVqf48UOs1zEW2C9_8thUQ5zKOa7VMxbaKBdjz_5W_FoW0"  # Replace with your actual Rev AI API key
rev_client = apiclient.RevAiAPIClient(REV_AI_API_KEY)

# Ensure uploads folder exists
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True) # Creates folder if it doesn't exist
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True) # Unique ID for each user
    name = db.Column(db.String(100), nullable=False) # User's name
    email = db.Column(db.String(100), unique=True) # User's email
    password = db.Column(db.String(100)) # Hashed password

    def __init__(self, email, password, name):
        self.name = name
        self.email = email
        self.password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password.encode('utf-8'))

# Create database tables
with app.app_context():
    db.create_all()

# Root route redirects to login page
@app.route('/')
def home():
    return redirect('/login')  # Redirect to login page

# Register route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        return redirect('/login')

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['email'] = user.email
            return redirect('/speech_translation')  # Redirect to Speech & Translation Portal
        else:
            return render_template('login.html', error='Invalid user')

    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    session.pop('email', None)
    return redirect('/login')

# Speech & Translation Portal (Protected route)
@app.route('/speech_translation')
def speech_translation():
    if 'email' not in session:
        return redirect('/login')  # Redirect to login if not authenticated
    return render_template('speech_translation.html')  # Main application page

# Upload and process audio file
@app.route("/upload", methods=["POST"])
def upload_audio():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401  # Protect this route

    if "audio" not in request.files or "input_lang" not in request.form:
        return jsonify({"error": "Missing audio file or language input"}), 400

    audio_file = request.files["audio"]
    input_lang = request.form["input_lang"]

    audio_path = os.path.join(app.config["UPLOAD_FOLDER"], audio_file.filename)
    audio_file.save(audio_path)

    try:
        job = rev_client.submit_job_local_file(audio_path, language=input_lang)

        while True:
            job_details = rev_client.get_job_details(job.id)
            if job_details.status in ["transcribed", "failed"]:
                break
            time.sleep(5)

        if job_details.status == "transcribed":
            transcript = rev_client.get_transcript_text(job.id)
            return jsonify({"text": transcript})
        else:
            return jsonify({"error": "Transcription failed"}), 500
    except Exception as e:
        logger.error(f"Error in transcription: {e}")
        return jsonify({"error": str(e)}), 500

# Audio to Text with Translation
@app.route("/translate_audio", methods=["POST"])
def translate_audio():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401  # Protect this route

    if "audio" not in request.files or "input_lang" not in request.form or "target_lang" not in request.form:
        return jsonify({"error": "Missing required inputs"}), 400

    input_lang = request.form["input_lang"]
    target_lang = request.form["target_lang"]
    audio_file = request.files["audio"]

    audio_path = os.path.join(app.config["UPLOAD_FOLDER"], audio_file.filename)
    audio_file.save(audio_path)

    try:
        job = rev_client.submit_job_local_file(audio_path, language=input_lang)

        while True:
            job_details = rev_client.get_job_details(job.id)
            if job_details.status in ["transcribed", "failed"]:
                break
            time.sleep(5)

        if job_details.status == "transcribed":
            transcript = rev_client.get_transcript_text(job.id)
            translated_text = translate_text_with_fallback(transcript, input_lang, target_lang)
            return jsonify({"text": transcript, "translated_text": translated_text})
        else:
            return jsonify({"error": "Transcription failed"}), 500
    except Exception as e:
        logger.error(f"Error in translation: {e}")
        return jsonify({"error": str(e)}), 500

# Translate text with fallback mechanism
def translate_text_with_fallback(text, source_lang, target_lang):
    try:
        translated_text = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        return translated_text
    except exceptions.TranslationNotFound:
        logger.warning(f"Translation not found for text: {text}. Trying alternative translation method.")
        # Implement a fallback translation method here if available
        return "Translation not available"
    except Exception as e:
        logger.error(f"Error in translation: {e}")
        return "Translation not available"

# Translate text
@app.route("/translate_text", methods=["POST"])
def translate_text():
    if 'email' not in session:
        return jsonify({"error": "Unauthorized"}), 401  # Protect this route

    data = request.json
    text = data.get("text", "")
    target_lang = data.get("target_lang", "hi")

    try:
        translated_text = translate_text_with_fallback(text, "auto", target_lang)
        return jsonify({"translated_text": translated_text})
    except Exception as e:
        logger.error(f"Error in translation: {e}")
        return jsonify({"error": str(e)}), 500

# for Running the Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)#port is 5000


    
#-m venv venv -> virtual envo
#venv\Scripts\activate -> activating virtual env
#python3 -m pip install Flask Flask-SQLAlchemy Flask-CORS rev_ai deep-translator bcrypt   -> installing necessary things
#python app.py -> run