#importing libraries
from flask import Flask,request
from flask import jsonify, send_file
from flask_jwt_extended import JWTManager, get_jwt, get_jwt_identity, jwt_required, set_access_cookies, unset_jwt_cookies
from flask_jwt_extended import create_access_token
from datetime import timedelta
import os
import joblib
import sqlite3 as sqlite
from dotenv import load_dotenv
from pathlib import Path
from cryptography.fernet import Fernet
from sklearn.preprocessing import StandardScaler
from sklearn.preprocessing import LabelEncoder
from werkzeug.utils import secure_filename
import pandas as pd
import json
dotenv_path = Path('.env')
load_dotenv(dotenv_path=dotenv_path)
SECRET_KEY = os.getenv("SECRET_KEY")
cipher = Fernet(SECRET_KEY)
#Config API
api = Flask(__name__)
api.config["JWT_SECRET_KEY"] = SECRET_KEY
api.config['JWT_TOKEN_LOCATION'] = ['headers']
api.config['JWT_HEADER_NAME'] = 'Auth-Token'
api.config['JWT_HEADER_TYPE']=''
api.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(minutes=60)
jwt = JWTManager(api)
#Reading serialized model and Label Encoder and Scaler
RAINFALL_MODEL=joblib.load('rainfall.mdl')
lb_WindGustDir=joblib.load('WindGustDir.joblib')
lb_WindDir9am=joblib.load('WindDir9am.joblib')
lb_WindDir3pm=joblib.load('WindDir3pm.joblib')
lb_RainToday=joblib.load('RainToday.joblib')
sc_scaler=joblib.load('scaler.joblib')
#Reading means and modes to filla null values
with open('means.json', 'r') as file:
    means = json.load(file)
with open('modes.json', 'r') as file:
    modes = json.load(file)
continuous_columns=['MinTemp','MaxTemp','Rainfall','WindGustSpeed',
                        'WindSpeed9am','WindSpeed3pm','Humidity9am',
                        'Humidity3pm','Pressure9am','Pressure3pm',
                        'Temp9am','Temp3pm']
categorical_columns=['WindGustDir',
'WindDir9am',
'WindDir3pm',
'RainToday']
#Method to get a token
@api.route('/login', methods=['POST'])
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    db=sqlite.connect('apidb.db')
    cursor = db.cursor()
    cursor.execute("select * from users where name = '%s'" % (username) )
    result=cursor.fetchall()
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
#Method to test token
@api.route('/test', methods=['POST'])
@jwt_required()
def test():
    response = {'type':"INFO",'message':"Your request was received"}
    return jsonify(response)
#Method to predict a single register
@api.route('/predict', methods=['POST'])
@jwt_required()
def predict():
    MinTemp = request.json.get("MinTemp", None)
    MaxTemp = request.json.get("MaxTemp", None)
    Rainfall = request.json.get("Rainfall", None)
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

    data={'MinTemp':[MinTemp],
            'MaxTemp':[MaxTemp],
            'Rainfall':[Rainfall],
            'WindGustDir':[WindGustDir],
            'WindGustSpeed':[WindGustSpeed],
            'WindDir9am':[WindDir9am],
            'WindDir3pm':[WindDir3pm],
            'WindSpeed9am':[WindSpeed9am],
            'WindSpeed3pm':[WindSpeed3pm],
            'Humidity9am':[Humidity9am],
            'Humidity3pm':[Humidity3pm],
            'Pressure9am':[Pressure9am],
            'Pressure3pm':[Pressure3pm],
            'Temp9am':[Temp9am],
            'Temp3pm':[Temp3pm],
            'RainToday':[RainToday]}
    weather=pd.DataFrame(data)
    
    #Convert categorical features
    weather['WindGustDir']=lb_WindGustDir.transform(weather['WindGustDir'])
    weather['WindDir9am']=lb_WindDir9am.transform(weather['WindDir9am'])
    weather['WindDir3pm']=lb_WindDir3pm.transform(weather['WindDir3pm'])
    weather['RainToday']=lb_RainToday.transform(weather['RainToday'])
    #Normalize values
    weather[continuous_columns] = sc_scaler.transform(weather[continuous_columns])
    #Predict rainfall
    out=RAINFALL_MODEL.predict(weather)[0]
  
    if out==0:
        response = {'type':"INFO",'message':"It won't rain tomorrow"}
    else:
        response = {'type':"INFO",'message':"It will rain tomorrow"}
    return jsonify(response)
#Method to predict many registers by a CSV file
@api.route('/predict_csv', methods=['POST'])
@jwt_required()
def predictCSV():
    try:
        file = request.files['csv']
        if file:
            filename=secure_filename(file.filename)
            a = 'file uploaded'
            file.save(filename)
            weatherOrg=pd.read_csv(filename)
            #Creating a copy
            weather=weatherOrg
            #removing features with missing values more than 30% and irrelevant features
            weather=weather.drop(['row ID','Location','Evaporation','Sunshine','Cloud9am','Cloud3pm'],axis=1)
        
            #fill missing categorical features
            for c in categorical_columns:
                weather[c]=weather[c].fillna(modes[c])
            #Convert categorical features to continous
            weather['WindGustDir']=lb_WindGustDir.transform(weather['WindGustDir'])
            weather['WindDir9am']=lb_WindDir9am.transform(weather['WindDir9am'])
            weather['WindDir3pm']=lb_WindDir3pm.transform(weather['WindDir3pm'])
            weather['RainToday']=lb_RainToday.transform(weather['RainToday'])
            #fill missing continous features
            for c in continuous_columns:    
                weather[c]=weather[c].fillna(means[c])
            
            weather[continuous_columns] = sc_scaler.transform(weather[continuous_columns])

            X=weather
            out=RAINFALL_MODEL.predict(X)
            weatherOrg['RainTomorrow']=out
            file_path='./'+filename.split('.')[0]+'_predicted.csv'
            weatherOrg.to_csv(filename.split('.')[0]+'_predicted.csv',sep=',',header=True,index=False)
            if os.path.isfile(file_path):
                return send_file(file_path,as_attachment=True)
        return a
    except:
        response = {'type':"INFO",'message':"Bad request"}
        return jsonify(response)
if __name__ == '__main__':
    api.run(debug=True,host="0.0.0.0",port=int(os.environ.get('PORT',2024)))