from flask import Flask, request, jsonify, render_template
import joblib
import os
from flask_cors import CORS
from datetime import datetime
import pandas as pd

from feature_engine import build_basic_features

# ----------------------
# INIT
# ----------------------
app = Flask(__name__)
CORS(app)

latest_data_store = {}

# ----------------------
# LOAD MODELS
# ----------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# NEW MODEL PATHS
hotspot_model = joblib.load(
    os.path.join(BASE_DIR, "ml3/hotspot_model.pkl")
)

overload_model = joblib.load(
    os.path.join(BASE_DIR, "ml3/overload_model.pkl")
)

print("✓ Models loaded")


# ----------------------
# FEATURE LOCK
# ----------------------
FEATURE_COLUMNS = hotspot_model.feature_names_in_.tolist()

print("✓ Feature columns locked")
print(f"✓ Total features: {len(FEATURE_COLUMNS)}")


# ----------------------
# API
# ----------------------
@app.route("/api/update", methods=["POST"])
def update_data():

    global latest_data_store

    try:

        # ----------------------
        # RECEIVE SENSOR DATA
        # ----------------------
        data = request.json

        temp = float(data["temperature"])
        current = float(data["current"])

        # ----------------------
        # FEATURE ENGINEERING
        # ----------------------
        X = build_basic_features(
            temp,
            current
        )

        # FORCE SAME FEATURE ORDER
        X = X.reindex(
            columns=FEATURE_COLUMNS,
            fill_value=0
        )

        # ----------------------
        # ML PREDICTION
        # ----------------------
        hot_prob = hotspot_model.predict_proba(X)[0][1]

        ovl_prob = overload_model.predict_proba(X)[0][1]

        # ----------------------
        # RISK OBJECT
        # ----------------------
        risk = {

            "hotspot_prob": float(hot_prob),

            "overload_prob": float(ovl_prob),

            "composite_risk": float(
                (hot_prob + ovl_prob) / 2
            )
        }

        # ----------------------
        # IMPROVED STATE LOGIC
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
        # DEBUG PRINTS
        # ----------------------
        print(
            f"T={temp:.2f}C | "
            f"I={current:.2f}A | "
            f"HOT={hot_prob:.2f} | "
            f"OVR={ovl_prob:.2f} | "
            f"STATE={state}"
        )

        # ----------------------
        # SAVE LATEST DATA
        # ----------------------
        latest_data_store = {

            "temperature": temp,

            "current": current,

            "breakerState": state,

            "ml": risk,

            "time": datetime.now().strftime("%H:%M:%S")
        }

        # ----------------------
        # API RESPONSE
        # ----------------------
        return jsonify({

            "success": True,

            "state": state,

            "ml": risk
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({

            "success": False,

            "error": str(e)
        })


# ----------------------
# ROUTES
# ----------------------
@app.route("/")
def index():

    return render_template("index.html")


@app.route("/api/latest-data")
def latest():

    return jsonify(latest_data_store)


# ----------------------
# RUN SERVER
# ----------------------
if __name__ == "__main__":

    print("🔥 SYSTEM STARTED")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )