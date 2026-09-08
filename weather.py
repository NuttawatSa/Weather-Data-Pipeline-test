import pandas as pd
import requests as rq
import json
import sqlite3
import logging
import time
import os
import streamlit as st

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
    
        response = rq.get(url, params= params, timeout=10)
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
        df["rain_probability"] = df["rain_probability"] / 100
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
    logging.info(f"Rows processed: {len(result)}")
    
else:
    result = pd.DataFrame()
    print("No data")
    logging.error(f"failed_cities {failed_cities}")

logging.info(f"run_time {time.time()-start_time:.2f} s")


connect = sqlite3.connect("weather.db")

with open("schema.sql", "r", encoding="utf-8") as f:
    schema = f.read()

connect.executescript(schema)

data = []
for row in result.itertuples(index=False):
    data.append((row.city, row.Date, row.time, row.temperature, row.rain_probability))

try:
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
except sqlite3.Error as e:
    connect.rollback()
    print("Database error:", e)

export = []
query1 = """
    SELECT city, date,
        ROUND(AVG(temperature), 2) AS avg_temperature,
        MAX(temperature) AS max_temperature,
        MIN(temperature) AS min_temperature
    FROM weather_forecast
    GROUP BY city, date
    ORDER BY city, date;
"""
result1 = pd.read_sql_query(query1, connect)


query2 = """
    SELECT city,
        ROUND(MAX(temperature) - MIN(temperature), 2) AS temperature_range
    FROM weather_forecast
    GROUP BY city
    ORDER BY temperature_range DESC, city ASC
    LIMIT 1;
"""
result2 = pd.read_sql_query(query2, connect)

query3 = """
    SELECT city, date,time, rain_probability
    FROM weather_forecast AS w
    WHERE rain_probability = (
        SELECT MAX(rain_probability)
        FROM weather_forecast
        WHERE city = w.city AND date = w.date
    )
    ORDER BY city, date, time;
"""
result3 = pd.read_sql_query(query3, connect)

query4 = """
    WITH daily_avg AS (
    SELECT city,date,
        ROUND(AVG(temperature), 2) AS avg_temperature
    FROM weather_forecast
    GROUP BY city, date
    )

    SELECT city, date, avg_temperature,
        ROUND(
            avg_temperature - LAG(avg_temperature) OVER (
                PARTITION BY city
                ORDER BY date
            ),
            2
    ) AS difference_from_previous_day
    FROM daily_avg
    ORDER BY city, date;
"""
result4 = pd.read_sql_query(query4, connect)

connect.close()


st.title("Weather Dashboard")

st.header("1. Daily Temperature Summary")
st.dataframe(result1, hide_index=True)

st.header("2. Widest Temperature Range")
st.dataframe(result2, hide_index=True)

st.header("3. Highest Rain Probability")
st.dataframe(result3, hide_index=True)

st.header("4. Temperature Change From Previous Day")
st.dataframe(result4, hide_index=True)   