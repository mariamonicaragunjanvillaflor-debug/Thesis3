from flask import Flask, request, jsonify, render_template
import joblib
import os
from flask_cors import CORS
from datetime import datetime
import pandas as pd

from feature_engine import build_basic_features

# ======================
# INIT
# ======================
app = Flask(__name__)
CORS(app)

latest_data_store = {
    "temperature": 0.0,
    "current": 0.0,
    "breakerState": "Unknown",
    "ml": {},
    "time": "00:00:00"
}

# ======================
# LOAD MODELS
# ======================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

hotspot_model = joblib.load(
    os.path.join(BASE_DIR, "ml3/hotspot_model.pkl")
)

overload_model = joblib.load(
    os.path.join(BASE_DIR, "ml3/overload_model.pkl")
)

print("✓ Models loaded")

# Lock feature columns
FEATURE_COLUMNS = hotspot_model.feature_names_in_.tolist()
print("✓ Feature columns locked:", len(FEATURE_COLUMNS))


# ======================
# SENSOR UPDATE + ML INFERENCE
# ======================
@app.route("/api/update", methods=["POST"])
def update_data():
    global latest_data_store

    try:
        data = request.get_json(force=True)

        # ----------------------
        # SAFE PARSING
        # ----------------------
        temp = float(data.get("temperature", 0.0))
        current = float(data.get("current", 0.0))

        # ----------------------
        # FEATURE ENGINEERING
        # ----------------------
        X = build_basic_features(temp, current)

        # enforce training feature order
        X = X.reindex(columns=FEATURE_COLUMNS, fill_value=0)

        # ----------------------
        # ML PREDICTIONS
        # ----------------------
        hot_prob = float(hotspot_model.predict_proba(X)[0][1])
        ovl_prob = float(overload_model.predict_proba(X)[0][1])

        risk = {
            "hotspot_prob": hot_prob,
            "overload_prob": ovl_prob,
            "composite_risk": (hot_prob + ovl_prob) / 2
        }

        # ----------------------
        # DECISION LOGIC (FINAL STATE)
        # ----------------------
        if temp >= 85:
            state = "Overheating"

        elif hot_prob >= 0.65:
            state = "Hotspot Risk"

        elif ovl_prob >= 0.60:
            state = "Overload"

        else:
            state = "Normal"

        # ----------------------
        # UPDATE GLOBAL STORE
        # ----------------------
        latest_data_store = {
            "temperature": temp,
            "current": current,
            "breakerState": state,
            "ml": risk,
            "time": datetime.now().strftime("%H:%M:%S")
        }

        # ----------------------
        # DEBUG LOG
        # ----------------------
        print(
            f"T={temp:.2f}C | "
            f"I={current:.2f}A | "
            f"HOT={hot_prob:.2f} | "
            f"OVR={ovl_prob:.2f} | "
            f"STATE={state}"
        )

        return jsonify({
            "success": True,
            "state": state,
            "ml": risk
        })

    except Exception as e:
        print("❌ ERROR in /api/update:", str(e))

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ======================
# FRONTEND (optional)
# ======================
@app.route("/")
def index():
    return render_template("index.html")


# ======================
# RPI FETCH ENDPOINT
# ======================
@app.route("/api/latest-data")
def latest():
    return jsonify(latest_data_store)


# ======================
# RUN SERVER
# ======================
if __name__ == "__main__":
    print("🔥 SYSTEM STARTED (ML + SENSOR API READY)")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )