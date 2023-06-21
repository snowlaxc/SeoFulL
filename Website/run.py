from flask import Flask, render_template
from datetime import datetime, timedelta
import plotly.express as px
import xgboost as xgb
import pandas as pd
import subprocess
import holidays
import pymysql
import numpy
import time
import json

############################################################################################
############################################################################################

# json 파일 불러오기
with open('json/mariadb.json') as file:
    mariadb = json.load(file)

############################################################################################
############################################################################################

# weather.py 실행 (OpenWeather api를 사용해 날씨 정보를 업데이트)
weather_process = subprocess.Popen(['python', 'weather.py'])

# run.py 코드 실행
try:

############################################################################################
############################################################################################

    #xgboost 모델 불러오기
    new_xgb_model = xgb.XGBRegressor()
    new_xgb_model.load_model('xgb_model.model')

    # DataFrame 값들 정의
    gu_code_values = [11110, 11140, 11170, 11200, 11215,
                    11230, 11260, 11290, 11305, 11320,
                    11350, 11380, 11410, 11440, 11470,
                    11500, 11530, 11545, 11560, 11590,
                    11620, 11650, 11680, 11710, 11740]

    gu_values = ['종로구', '중구', '용산구', '성동구', '광진구',
                '동대문구', '중랑구', '성북구', '강북구', '도봉구',
                '노원구', '은평구', '서대문구', '마포구', '양천구',
                '강서구', '구로구', '금천구', '영등포구' ,'동작구',
                '관악구', '서초구' ,'강남구', '송파구' ,'강동구']

############################################################################################
############################################################################################

    # MariaDB 연결 정보
    host = mariadb['host']
    port = mariadb['port']
    user = mariadb['user']
    password = mariadb['password']
    database = 'SeoFulL'
    table = 'weather_data'

    # 데이터베이스로부터 날씨 정보를 받는 함수 정의
    def db_data_all():
        connection = pymysql.connect(host=host, port=port, user=user, password=password, database=database)
        query = f"SELECT dt, temperature, humidity, wind_speed, rain FROM {table}"
        cursor = connection.cursor()
        cursor.execute(query)
        row = cursor.fetchall()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"Weather information from DB is updated! ({current_time})")
        cursor.close()
        connection.close()
        return row

############################################################################################
############################################################################################

    # UNIX 시간을 변환하는 함수
    def convert_unix_time1(unix_time):
        dt = datetime.fromtimestamp(unix_time)
        formatted_dt = dt.strftime('%Y년 %m월 %d일 (%a) %p %I시')
        formatted_dt = formatted_dt.replace("AM", "오전").replace("PM", "오후")
        formatted_dt = formatted_dt.replace("Mon", "월").replace("Tue", "화").replace("Wed", "수").replace("Thu", "목").replace("Fri", "금").replace("Sat", "토").replace("Sun", "일")
        return formatted_dt

    # UNIX 시간을 변환하는 함수2
    def convert_unix_time2(unix_time):
        dt = datetime.fromtimestamp(unix_time)
        formatted_dt = dt.strftime('%d일 %H시')
        return formatted_dt        

    # 시간 관련 데이터 생성
    def time_data(unix_time):
        dt = datetime.fromtimestamp(unix_time)
        month = dt.month
        holiday = 2 if dt.weekday() >= 5 or dt.date() in holidays.KR() else 0
        day = dt.weekday()
        hour = dt.hour
        data2 = {'month': month, 'holiday': holiday, 'day': day, 'hour': hour}
        return data2

############################################################################################
############################################################################################

    # 공휴일 여부 확인 함수
    def is_holiday(date):
        kr_holidays = holidays.KR(years=date.year)
        return date in kr_holidays

    # 주말 여부 확인 함수
    def is_weekend(date):
        return date.weekday() >= 5  # 5: 토요일, 6: 일요일

############################################################################################
############################################################################################

    # Flask 생성
    app = Flask(__name__)

    # /main 페이지로 redirection
    @app.route("/")
    def redirection():
        return render_template("redirection.html")

    # /main 페이지
    @app.route("/main")
    def index():
        return render_template("main.html")

    # /congestion 페이지
    @app.route("/congestion/<int:index>", methods=["GET"])
    def congestion(index):

        # 2일 내 정보 외 접근 시
        if index < 0 or index > 47:
            return render_template("error.html")
        
        # dataframe 초기화
        new_data = pd.DataFrame({'gu_code': [], 'month': [], 'holiday': [], 'day': [],
                                'hour': [], 'temp': [], 'wind': [], 'rain': [], 'humidity': []})

        # 데이터베이스로부터 날씨 정보를 받아옴
        row = db_data_all()
        row = row[index]

        # 데이터를 딕셔너리로 변환
        data1 = {
            'dt': convert_unix_time1(row[0]),
            'temperature': row[1],
            'humidity': row[2],
            'wind_speed': row[3],
            'rain': row[4],
        }

        # 시간 데이터 생성
        data2 = time_data(row[0])
        
        # 분석 위한 새로운 data 생성
        new_data['gu_code'] = gu_code_values
        new_data['month'] = data2['month']
        new_data['holiday'] = data2['holiday']
        new_data['day'] = data2['day']
        new_data['hour'] = data2['hour']
        new_data['temp'] = data1['temperature']
        new_data['wind'] = data1['wind_speed']
        new_data['rain'] = data1['rain']
        new_data['humidity'] = data1['humidity']

        # data 타입 변경
        new_data['month'] = new_data['month'].astype('int64')
        new_data['holiday'] = new_data['holiday'].astype('int64')
        new_data['day'] = new_data['day'].astype('int64')
        new_data['hour'] = new_data['hour'].astype('int64')
        new_data['temp'] = new_data['temp'].astype('float64')
        new_data['wind'] = new_data['wind'].astype('int64')
        new_data['rain'] = new_data['rain']
        new_data['humidity'] = new_data['humidity'].astype('float64')
        
        # xgb_model을 통해 예측
        new_data['people'] = new_xgb_model.predict(new_data).round()
        new_data['people'] = new_data['people'].astype('int64')
        
        # DataFrame 정리
        new_data = new_data[['gu_code', 'people']]
        new_data['gu'] = gu_values
        new_data = new_data.sort_values('people')
        new_data = new_data.reset_index().drop(['index'], axis = 1).reset_index()
        new_data['index'] = (new_data['index']+1)*4
        new_data.columns = ['cong', 'gu_code', 'people', 'gu']
        new_data = new_data.sort_values('gu_code').reset_index().drop(['index'], axis = 1)
        new_data['cong_info'] = pd.cut(new_data['cong'], bins=[4, 24, 44, 64, 84, 101], labels=['매우 한산', '한산', '보통', '혼잡', '매우 혼잡'], right=False)
        hansan_gu = list(new_data[new_data['cong_info']=='매우 한산']['gu'])
        hansan_gu = ' '.join(hansan_gu)
        honzap_gu = list(new_data[new_data['cong_info']=='매우 혼잡']['gu'])
        honzap_gu = ' '.join(honzap_gu)

        # DataFrame 출력
        # print(new_data)
        return render_template("congestion.html", data1 = data1, new_data = new_data, hansan_gu = hansan_gu, honzap_gu = honzap_gu)

    # /weather 페이지
    @app.route("/weather", methods=["GET"])
    def weather():

        # 데이터베이스로부터 날씨 정보를 받아옴
        row = db_data_all()
        row = pd.DataFrame(row)
        row.columns = ['dt', 'temp', 'humidity', 'wind', 'rain']
        row['dt1'] = row['dt'].apply(convert_unix_time1)
        row['dt2'] = row['dt'].apply(convert_unix_time2)
        row = row[['dt1', 'dt2', 'temp', 'humidity' ,'wind', 'rain']]
        row

        # Create the plotly figure
        fig = px.line(row, x='dt2', y='temp')

        # Update the layout
        fig.update_layout(
            title='온도',
            plot_bgcolor='#f1f1f1',
            width=400,
            height=90,
            margin=dict(b=20)
        )

        # Convert the plotly figure to JSON
        graphJSON = fig.to_json()
        
        return render_template("weather.html", graphJSON=graphJSON, row = row)

    # 없는 주소 접근 시
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html')

############################################################################################
############################################################################################

    # Flask 실행
    if __name__ == "__main__":
        app.run(host='0.0.0.0', port={{port_number}}, debug=False)

############################################################################################
############################################################################################

# run.py 중지 시 weather.py 프로세스를 중지
except Exception:
    weather_process.terminate()
