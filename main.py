from flask import Flask,request
from flask import jsonify
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, jwt_required, set_access_cookies, unset_jwt_cookies
from flask_jwt_extended import create_access_token
from datetime import timedelta
import os
import joblib
import sqlite3 as sqlite
from dotenv import load_dotenv
from pathlib import Path
from cryptography.fernet import Fernet
dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)
SECRET_KEY = os.getenv("SECRET_KEY")
print(SECRET_KEY)
cipher = Fernet(SECRET_KEY)
api = Flask(__name__)
api.config["JWT_SECRET_KEY"] = SECRET_KEY
api.config['JWT_TOKEN_LOCATION'] = ['headers']
api.config['JWT_HEADER_NAME'] = 'Auth-Token'
api.config['JWT_HEADER_TYPE']=''
api.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=60)
jwt = JWTManager(api)
RAINFALL_MODEL=joblib.load('rainfall.mdl')
@api.route('/login', methods=['POST'])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    db=sqlite.connect('apidb.db')
    cursor = db.cursor()
    cursor.execute("select * from users where name = '%s'" % (username) )
    result=cursor.fetchall()
    print(result)
    for r in result:
        message=cipher.decrypt(r[2]).decode()
        if message==password:
            access_token = create_access_token(identity=username)
            response = jsonify({ "access_token": access_token, "name": username })
            set_access_cookies(response, access_token)
            return response
        else:
            return jsonify({"type":"INFO","message":"Bad user or password"}), 401
    return jsonify({"type":"INFO","message":"Bad user or password"}), 401
@api.route('/test', methods=['POST'])
@jwt_required()
def test():
    response = {'type':"INFO",'message':"Your request was received"}
    return jsonify(response)

@api.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    MinTemp = request.json.get("MinTemp", None)
    MaxTemp = request.json.get("MaxTemp", None)
    Railfall = request.json.get("Railfall", None)
    WindGustDir = request.json.get("WindGustDir", None)
    WindGustSpeed = request.json.get("WindGustSpeed", None)
    WindDir9am = request.json.get("WindDir9am", None)
    WindDir3pm = request.json.get("WindDir3pm", None)
    WindSpeed9am = request.json.get("WindSpeed9am", None)
    WindSpeed3pm = request.json.get("WindSpeed3pm", None)
    Humidity9am = request.json.get("Humidity9am", None)
    Humidity3pm = request.json.get("Humidity3pm", None)
    Pressure9am = request.json.get("Pressure9am", None)
    Pressure3pm = request.json.get("Pressure3pm", None)
    Temp9am = request.json.get("Temp9am", None)
    Temp3pm = request.json.get("Temp3pm", None)
    RainToday = request.json.get("RainToday", None)
    array=[
        MinTemp,
        MaxTemp,
        Railfall,
        WindGustDir,
        WindGustSpeed,
        WindDir9am,
        WindDir3pm,
        WindSpeed9am,
        WindSpeed3pm,
        Humidity9am,
        Humidity3pm,
        Pressure9am,
        Pressure3pm,
        Temp9am,
        Temp3pm,
        RainToday
    ]
    out=RAINFALL_MODEL.predict([array])[0]
    if out==0:
        response = {'type':"INFO",'message':"It won't rain tomorrow"}
    else:
        response = {'type':"INFO",'message':"It will rain tomorrow"}
    return jsonify(response)
if __name__ == '__main__':
    api.run(debug=True,host="0.0.0.0",port=int(os.environ.get('PORT',2024)))