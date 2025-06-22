from flask import Flask, render_template
import os
from flask_cors import CORS
from full_process import full_process_bp 
from dotenv import load_dotenv


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
CORS(app)

# Register blueprints
app.register_blueprint(full_process_bp, url_prefix="/full")

@app.route("/")
def home():
    return render_template("interview_landing.html")
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
