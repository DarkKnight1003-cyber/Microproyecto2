from flask import Flask, request, jsonify
import joblib
import numpy as np

app = Flask(__name__)

model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")

CLASES = ["class_0", "class_1", "class_2"]

@app.route("/predict", methods=["POST"])
def predict():
    datos = request.get_json()
    valores = datos.get("features")

    if valores is None or len(valores) != 13:
        return jsonify({"error": "Se requieren 13 valores en 'features'"}), 400

    entrada = np.array(valores).reshape(1, -1)
    entrada_scaled = scaler.transform(entrada)

    pred = model.predict(entrada_scaled)[0]
    prob = model.predict_proba(entrada_scaled)[0][pred]

    return jsonify({
        "clase_predicha": CLASES[pred],
        "probabilidad": round(float(prob), 3)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)