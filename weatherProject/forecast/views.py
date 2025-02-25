from django.shortcuts import render

# Create your views here.
import sys
sys.path.append("/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages")
import requests # fetch data from API
import pandas as pd # handling and anlysising data
import numpy as np # numeric operations
from sklearn.model_selection import train_test_split # split data into training and test sets
from sklearn.preprocessing import LabelEncoder # convert catogerucal data into numericals valus
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor # models for classification and regression taks
from sklearn.metrics import mean_squared_error # measure the accuracy of our prediction
from datetime import datetime, timedelta
import pytz
import os

API_KEY = '45928991225d87e22d47ed995e58ffac'
BASE_URL = 'https://api.openweathermap.org/data/2.5/'

# 1. Fetch the CURRENT WEATHER DATA
def get_current_weather(city):
  url = f"{BASE_URL}weather?q={city}&appid={API_KEY}&units=metric"
  response = requests.get(url)
  data = response.json()
  return {
      'city' : data['name'],
      'current_temp' : round(data['main']['temp']),
      'feels_like' : round(data['main']['feels_like']),
      'temp_min' : round(data['main']['temp_min']),
      'temp_max' : round(data['main']['temp_max']),
      'humidity' : round(data['main']['humidity']),
      'description' : data['weather'][0]['description'],
      'country' : data['sys']['country'],
      'wind_gust_dir' : data['wind']['deg'],
      'pressure' : data['main']['pressure'],
      'Wind_Gust_Speed' : data['wind']['speed'],


      'clouds' :  data['clouds']['all'],
      'Visibility' : data['visibility'],
  }

# 2. READ HISTORICAL DATA
def read_historical_data(filename):
  df = pd.read_csv(filename)
  df = df.dropna()
  df = df.drop_duplicates()
  return df

# 3. Prepare data for training
def prepare_data(data):
  le =  LabelEncoder()
  data['WindGustDir'] = le.fit_transform(data['WindGustDir']) # Convert categorical data to numerical data
  data['RainTomorrow'] = le.fit_transform(data['RainTomorrow']) # Convert categorical data to numerical data

  X = data[['MinTemp','MaxTemp','WindGustDir','WindGustSpeed','Humidity','Pressure','Temp']]
  y = data['RainTomorrow']

  return X,y,le


# 4. Train Rain Prediction Model
def train_rain_model(X,y): # Split to test and train to see how models performs in new unseen data, not only in exist data
  X_train, X_test, y_train, y_test = train_test_split(X,y,test_size=0.2,random_state=42) # 20% of data for testing; 80% of data for training: 80% of data for training; The Hitchhiker's Guide to the Galaxy: 42 (or any other integer) ensures that the data split is reproducible. This means that every time you run the code, you'll get the same train-test split, which is crucial for consistency in experiments and debugging
  model = RandomForestClassifier(n_estimators=100, random_state=42) #Group of decision tree to make prediction, 100 decision tree
  model.fit(X_train,y_train)  #train the data
  # after trainning the data, using model to make prediction on test data
  y_pred = model.predict(X_test)  #make prediction on test set
  print("Mean Squared Error for Rain Model")
  print(mean_squared_error(y_test,y_pred))
  # A lower MSE indicates that the model's predictions are closer to the actual values, meaning better performance.
  # Conversely, a higher MSE indicates larger errors in the predictions.

  return model

# 5. Prepare REgression data
def prepare_regression_data(data, feature):
  X,y = [],[] # X is for store the feature value; Y is for store the target value that we want to predict
    # like X is today temp and Y is tmr temp
    # Regression model to learn the relationship between past and future

  for i in range(len(data)-1):
    X.append(data[feature].iloc[i])

    y.append(data[feature].iloc[i+1])

  X = np.array(X).reshape(-1,1) # converts the list X into a NumPy array, reshape the array into a 2D array with one column and many rows to fit all the elements; -1 means infer the number of rows automatically
  y = np.array(y)

  return X,y

# Train the regression model
def train_regression_model(X,y):
  model = RandomForestRegressor(n_estimators=100, random_state=42)
  model.fit(X,y)
  return model

# Predict Future
def predict_future(model, current_value):
  predictions = [current_value]

  for i in range(5):
    next_value = model.predict(np.array([[predictions[-1]]]))

    predictions.append(next_value[0])

  return predictions[1:]

# WEather Analysis Function
def weather_view(request):
    if request.method == 'POST':
        city = request.POST.get('city')
        current_weather = get_current_weather(city)

        csv_path = os.path.join('/Users/jackywong1105/Desktop/Real-TimeWeatherForecastingWebsite/weatherProject/weather.csv')
        historical_data = read_historical_data(csv_path) # load historical data

        X,y,le = prepare_data(historical_data) # prepare and train the rain prediction model

        rain_model = train_rain_model(X,y)

        #map win directions to compass points
        wind_deg = current_weather['wind_gust_dir'] % 360
        compass_points = [
          ("N", 0, 11.25),("NNE", 11.25, 33.75),("NE", 33.75, 56.25),
          ("ENE", 56.25, 78.75),("E", 78.75, 101.25),("ESE", 101.25, 123.75),
          ("SE", 123.75, 146.25),("SSE", 146.25, 168.75),("S", 168.75, 191.25),
          ("SSW", 191.25, 213.75),("SW", 213.75, 236.25),("WSW", 236.25, 258.75),
          ("W", 258.75, 281.25),("WNW", 281.25, 303.75),("NW", 303.75, 326.25),
          ("NNW", 326.25, 328.75)
        ]
        
        compass_direction = next(point for point, start, end in compass_points if start <= wind_deg < end)

        compass_direction_encoded = le.transform([compass_direction])[0] if compass_direction in le.classes_ else -1


        current_data = {
          'MinTemp' : current_weather['temp_min'],
          'MaxTemp' : current_weather['temp_max'],
          'WindGustDir' : compass_direction_encoded,
          'WindGustSpeed' : current_weather['Wind_Gust_Speed'],
          'Humidity' : current_weather['humidity'],
          'Pressure' : current_weather['pressure'],
          'Temp': current_weather['current_temp']
        }

        current_df = pd.DataFrame([current_data])
        #rain prediction
        rain_prediction = rain_model.predict(current_df)[0]
          #prepare regression model for temp and hum
        X_temp, y_temp = prepare_regression_data(historical_data, 'Temp')

        X_hum, y_hum = prepare_regression_data(historical_data, 'Humidity')

        temp_model = train_regression_model(X_temp, y_temp)

        hum_model = train_regression_model(X_hum, y_hum)
        #predict future temp and hum
        future_temp = predict_future(temp_model, current_weather['temp_min'])

        future_humidity = predict_future(hum_model, current_weather['humidity'])

        #prepare time for future prediction
        timezone = pytz.timezone('Asia/Shanghai')

        now = datetime.now(timezone)
        next_hour = now + timedelta(hours=1)
        next_hour = next_hour.replace(minute=0, second=0, microsecond=0)

        future_times = [(next_hour + timedelta(hours=i)).strftime("%H:00") for i in range(5)]    

        #store each value seperately
        time1, time2, time3, time4, time5 = future_times
        temp1, temp2, temp3, temp4, temp5 = future_temp
        hum1, hum2, hum3, hum4, hum5 = future_humidity

        # pass data to template
        context = {
          'location' : city,
          'current_temp' : current_weather['current_temp'],
          'MinTemp' : current_weather['temp_min'],
          'MaxTemp' : current_weather['temp_max'],
          'feels_like' : current_weather['feels_like'],
          'humidity' : current_weather['humidity'],
          'clouds' : current_weather['clouds'],
          'description' : current_weather['description'],
          'city' : current_weather['city'],
          'country' : current_weather['country'],

          'time' : datetime.now(),
          'date' : datetime.now().strftime("%B %d,%Y"),

          'wind' : current_weather['Wind_Gust_Speed'],
          'pressure' : current_weather['pressure'],
            
          'visibility' : current_weather['Visibility'],
            
          'time1' : time1,
          'time2' : time2,
          'time3' : time3,
          'time4' : time4,
          'time5' : time5,

          'temp1' : f"{round(temp1, 1)}",
          'temp2' : f"{round(temp2, 1)}",
          'temp3' : f"{round(temp3, 1)}",
          'temp4' : f"{round(temp4, 1)}",
          'temp5' : f"{round(temp5, 1)}",

          'hum1' : f"{round(hum1, 1)}",
          'hum2' : f"{round(hum2, 1)}",
          'hum3' : f"{round(hum3, 1)}",
          'hum4' : f"{round(hum4, 1)}",
          'hum5' : f"{round(hum5, 1)}",
        }

        return render(request, 'weather.html', context)

    return render(request, 'weather.html')