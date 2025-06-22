from flask import Flask
from flask_cors import CORS
from routes.full_process import full_process_bp 
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# Register blueprints
app.register_blueprint(full_process_bp, url_prefix="/full")

@app.route("/")
def health():
    return {"status: ok" }, 200
    


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
