from datetime import datetime
import requests
import schedule
import pymysql
import time
import json

############################################################################################
############################################################################################

# json 파일 불러오기
with open('json/mariadb.json') as file:
    mariadb = json.load(file)
host = mariadb['host']
port = mariadb['port']
user = mariadb['user']
password = mariadb['password']
database = 'SeoFulL'
table = 'weather_data'

with open('json/openweather.json') as file:
    openweather = json.load(file)
api = openweather['api']

# MariaDB 연결
connection = pymysql.connect(host=host, port=port, user=user, password=password, database=database)

############################################################################################
############################################################################################

# OpenWeatherAPI 링크 설정
openweather_url = 'https://api.openweathermap.org/data/3.0/onecall?lat=37.5642135&lon=127.0016985&exclude=current,minutely,daily,alert&appid=' + api

# 서버로부터 날씨 정보 받아오기
def get_weather_data():
    response = requests.get(openweather_url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

############################################################################################
############################################################################################

# db에 날씨 정보 저장하기1
def save_weather_data(weather_data):
    # 기존 weather_data 테이블의 데이터 모두 삭제
    with connection.cursor() as cursor:
        delete_query = "DELETE FROM weather_data"
        cursor.execute(delete_query)
        for hour in weather_data['hourly']:
            dt = hour['dt']
            temperature = round(hour['temp'] - 273.15, 1)  # 온도를 섭씨로 변환하고 소수점 한 자리까지 반올림
            humidity = hour['humidity']
            wind_speed = round(hour['wind_speed'], 1)  # 풍속을 소수점 한 자리까지 반올림
            rain = hour.get('rain', {}).get('1h', 0)
            query = "INSERT INTO weather_data (dt, temperature, humidity, wind_speed, rain) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (dt, temperature, humidity, wind_speed, rain))
    connection.commit()

# db에 날씨 정보 저장하기2
def update_weather_data():
    weather_data = get_weather_data()
    if weather_data:
        save_weather_data(weather_data)
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Weather information in DB is updated! ({current_time})")
    else:
        print("Failed to fetch weather data.")

############################################################################################
############################################################################################

# 실행 시 바로 db에 날씨 정보 저장
update_weather_data()

# 매 30분마다 db에 새로운 날씨정보 저장
schedule.every().hour.at("00:00").do(update_weather_data)
schedule.every().hour.at("01:00").do(update_weather_data)
schedule.every().hour.at("30:00").do(update_weather_data)
schedule.every().hour.at("31:00").do(update_weather_data)
while True:
    schedule.run_pending()
    time.sleep(1)