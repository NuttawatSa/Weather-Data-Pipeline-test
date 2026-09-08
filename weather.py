import pandas as pd
import requests as rq
import json
import sqlite3
import logging
import time
import os

url = "https://api.open-meteo.com/v1/forecast"
os.makedirs("raw", exist_ok=True)
cities = {
    "Bangkok": (13.754, 100.5014),
    "Chiang_Mai": (18.7904, 98.9847),
    "Phuket": (7.8906, 98.3981),
    "Khon_Kaen": (16.4467, 102.833),
    "Hat_Yai": (7.0084, 100.4767),
}
city_list=[]

start_time = time.time()
success_cities = 0
failed_cities = []

logging.basicConfig(
    filename="weather.log",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

for c ,(lat, long) in cities.items():
    params = {
        "latitude": lat,
        "longitude": long,
        "hourly": ["temperature_2m", "precipitation_probability"],
        "forecast_days": 7,
        "timezone": "auto",
    }
    try:
    
        response = rq.get(url, params= params)
        response.raise_for_status() 
        cities_data = response.json() 
        with open(f"raw/{c}.json", "w", encoding="utf-8") as f:
            json.dump(cities_data, f, ensure_ascii=False, indent=4)
        df = pd.DataFrame(
            {
                "date_time": cities_data["hourly"]["time"],
                "city": c,
                "temperature": cities_data["hourly"]["temperature_2m"],
                "rain_probability": cities_data["hourly"]["precipitation_probability"],
            }
        )
        df["date_time"] = pd.to_datetime(df["date_time"])
        df["Date"] = df["date_time"].dt.strftime("%Y-%m-%d")
        df["time"] = df["date_time"].dt.strftime("%H:%M:%S")
        df = df[["city", "Date", "time", "temperature", "rain_probability"]]
        
        city_list.append(df)
        success_cities += 1
        logging.info(f"{c} processed {len(df)} rows")
        print(f"{c} loaded successfully")
        
    except Exception as e:
        print("Failed to load data.")
        failed_cities.append(c)
        logging.error(f"{c} failed {e}")
        
        continue

if city_list:
    result = pd.concat(city_list, ignore_index=True)
    print(result)
    logging.info(f"{success_cities} cities")
    
else:
    result = pd.DataFrame()
    print("No data")
    logging.error(f"failed_cities {failed_cities}")

logging.info(f"run_time {time.time()-start_time:.2f} s")


connect = sqlite3.connect("weather.db")

conn = connect.cursor()

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS weather_forecast (
        city TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        temperature REAL,
        rain_probability REAL,
        PRIMARY KEY (city, date, time)
    )

"""
)
data = []
for row in result.itertuples(index=False):
    data.append((row.city, row.Date, row.time, row.temperature, row.rain_probability))

connect.executemany(
    """
    INSERT INTO weather_forecast 
    (city, date, time, temperature, rain_probability)
    VALUES (?, ?, ?, ?, ?)
    ON CONFLICT(city, date, time)
    DO UPDATE SET
	    temperature = excluded.temperature,
	    rain_probability = excluded.rain_probability
""",
data,
)

connect.commit()
connect.close()






    