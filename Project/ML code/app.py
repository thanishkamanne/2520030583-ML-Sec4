from flask import Flask, render_template, request, jsonify
import pandas as pd
import joblib
from pathlib import Path

app = Flask(__name__)
MODEL_PATH = Path(__file__).parent / "model" / "best_model.pkl"
model = joblib.load(MODEL_PATH)

MODEL_FEATURES = [
    "date", "timestamp", "start_frame", "number_of_frames",
    "direction_south", "day_night_day",
    "weather_clear", "weather_overcast", "weather_rain"
]

# These are the exact categories used while training the supplied model.
DIRECTIONS = ["south"]
DAY_NIGHT = ["day"]
WEATHER = ["clear", "overcast", "rain"]

def prepare_input(data):
    # The model was trained with date as YYYYMMDD and timestamp as a numeric value.
    date_text = str(data["date"]).strip()
    date_value = int(date_text.replace("-", ""))

    row = {
        "date": date_value,
        "timestamp": float(data["timestamp"]),
        "start_frame": int(data["start_frame"]),
        "number_of_frames": int(data["number_of_frames"]),
        "direction_south": 1 if data["direction"].lower() == "south" else 0,
        "day_night_day": 1 if data["day_night"].lower() == "day" else 0,
        "weather_clear": 1 if data["weather"].lower() == "clear" else 0,
        "weather_overcast": 1 if data["weather"].lower() == "overcast" else 0,
        "weather_rain": 1 if data["weather"].lower() == "rain" else 0,
    }
    return pd.DataFrame([row], columns=MODEL_FEATURES)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(force=True)

        required = ["date", "timestamp", "direction", "day_night",
                    "weather", "start_frame", "number_of_frames"]
        missing = [x for x in required if str(data.get(x, "")).strip() == ""]
        if missing:
            return jsonify({"ok": False, "error": "Please fill all required fields."}), 400

        if data["direction"].lower() not in DIRECTIONS:
            return jsonify({"ok": False, "error": "Invalid direction selected."}), 400
        if data["day_night"].lower() not in DAY_NIGHT:
            return jsonify({"ok": False, "error": "Invalid day/night value selected."}), 400
        if data["weather"].lower() not in WEATHER:
            return jsonify({"ok": False, "error": "Invalid weather selected."}), 400

        X = prepare_input(data)
        prediction = model.predict(X)[0]

        probabilities = {}
        if hasattr(model, "predict_proba"):
            probs = model.predict_proba(X)[0]
            probabilities = {
                str(cls): round(float(prob) * 100, 2)
                for cls, prob in zip(model.classes_, probs)
            }

        confidence = probabilities.get(str(prediction), 0)
        details = {
            "traffic_class": str(prediction).title(),
            "confidence": confidence,
            "probabilities": probabilities,
            "inputs": {
                "Date": data["date"],
                "Timestamp": data["timestamp"],
                "Direction": data["direction"].title(),
                "Period": data["day_night"].title(),
                "Weather": data["weather"].title(),
                "Start Frame": int(data["start_frame"]),
                "Number of Frames": int(data["number_of_frames"])
            }
        }
        return jsonify({"ok": True, **details})
    except Exception as exc:
        return jsonify({
            "ok": False,
            "error": f"Prediction failed: {exc}"
        }), 500

@app.route("/health")
def health():
    return jsonify({"status": "running", "model": type(model).__name__})

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
