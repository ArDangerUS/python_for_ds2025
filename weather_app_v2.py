import datetime as dt
import json
import requests
import openai
from flask import Flask, jsonify, request

API_TOKEN = "YOUR_TOKEN"
VISUAL_CROSSING_API_KEY = "YOUR_TOKEN"
OPENAI_API_KEY = "YOUR_TOKEN"

app = Flask(__name__)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv["message"] = self.message
        return rv


def get_weather_data(location: str, date: str):
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{date}?unitGroup=metric&include=days&key={VISUAL_CROSSING_API_KEY}&contentType=json"

    try:
        response = requests.get(url)
        
        if response.status_code == requests.codes.ok:
            return response.json()
        else:
            raise InvalidUsage(response.text, status_code=response.status_code)
    except Exception:
        raise InvalidUsage("Internal error while fetching weather data", status_code=500)


def get_ai_suggestion(weather):
    try:
        prompt = f"""
        Поточна погода:
        - Температура: {weather['temp_c']}°C
        - Вітер: {weather['wind_kph']} км/год
        - Тиск: {weather['pressure_mb']} мбар
        - Вологість: {weather['humidity']}%

        На основі цих даних:
        1. Який одяг найкраще носити?
        """

        openai.api_key = OPENAI_API_KEY

        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ти експерт з погоди та рекомендацій, щодо одягу який краще одягати."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Не вдалося отримати рекомендації від ШІ: {str(e)}"


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route("/")
def home_page():
    return "<p><h2>KMA L2: Python Weather SaaS.</h2></p>"


@app.route("/weather", methods=["POST"])
def weather_endpoint():
    json_data = request.get_json()

    if json_data.get("token") != API_TOKEN:
        raise InvalidUsage("Wrong API token", status_code=403)

    location = json_data.get("location")
    date = json_data.get("date")
    requester_name = json_data.get("requester_name")

    if not location or not date or not requester_name:
        raise InvalidUsage("Missing required fields", status_code=400)

    weather_data = get_weather_data(location, date)
    weather_info = weather_data.get("days", [{}])[0]

    weather = {
        "temp_c": weather_info.get("temp", None) or "N/A",
        "wind_kph": weather_info.get("windspeed", None) or "N/A",
        "pressure_mb": weather_info.get("pressure", None) or "N/A",
        "humidity": weather_info.get("humidity", None) or "N/A",
    }

    result = {
        "requester_name": requester_name,
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "location": location,
        "date": date,
        "weather": weather,
    }
    
    return jsonify(result)


@app.route("/weather_with_ai", methods=["POST"])
def weather_with_ai_endpoint():
    json_data = request.get_json()

    if json_data.get("token") != API_TOKEN:
        raise InvalidUsage("Wrong API token", status_code=403)

    location = json_data.get("location")
    date = json_data.get("date")
    requester_name = json_data.get("requester_name")

    if not location or not date or not requester_name:
        raise InvalidUsage("Missing required fields", status_code=400)

    weather_data = get_weather_data(location, date)
    weather_info = weather_data.get("days", [{}])[0]

    weather = {
        "temp_c": weather_info.get("temp", None) or "N/A",
        "wind_kph": weather_info.get("windspeed", None) or "N/A",
        "pressure_mb": weather_info.get("pressure", None) or "N/A",
        "humidity": weather_info.get("humidity", None) or "N/A",
    }

    ai_suggestion = get_ai_suggestion(weather)

    result = {
        "requester_name": requester_name,
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
        "location": location,
        "date": date,
        "weather": weather,
        "ai_suggestion": ai_suggestion,
    }
    
    return jsonify(result)


if __name__ == "__main__":
    app.run(debug=True)