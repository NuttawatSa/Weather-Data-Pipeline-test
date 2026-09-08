CREATE TABLE IF NOT EXISTS weather_forecast (
    city TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    temperature REAL,
    rain_probability REAL,

    PRIMARY KEY (city, date, time)
);