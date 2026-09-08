import pandas as pd
import sqlite3
import streamlit as st

connect = sqlite3.connect("weather.db")

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