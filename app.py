import dash
import csv
import requests
from flask import Flask, request, render_template, redirect, url_for
from dash import dcc, html
import pandas as pd
import plotly.graph_objs as go

app = Flask(__name__)
dash_app = dash.Dash(__name__, server=app, url_base_pathname='/dashboard/')
dash_app.layout = html.Div()

API_KEY = 'u0Hld6AJaY5SwDsZB7e09yVqALIdZ7Bz'
BASE_URL = 'http://dataservice.accuweather.com'


# Сохраняет данные о погоде в csv
def save_weather_data_to_csv(weather_data_list, csv_file_path, city_names):
    """
    :param weather_data_list: Список данных о погоде для различных городов.
    :param csv_file_path: Путь к файлу CSV, в который будут записаны данные.
    :param city_names: Список названий городов.
    """
    headers = ['City', 'Date', 'Average Temperature', 'Wind Speed', 'Precipitation Probability', 'Condition']

    with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=headers)
        writer.writeheader()

        for i in range(len(weather_data_list)):
            for daily_forecast in weather_data_list[i]['DailyForecasts']:
                date = daily_forecast['Date']
                min_temp = daily_forecast['Temperature']['Minimum']['Value']
                max_temp = daily_forecast['Temperature']['Maximum']['Value']
                aver_temp = (min_temp + max_temp) / 2
                wind_speed = daily_forecast['Day']['Wind']['Speed']['Value']
                prec_prob = daily_forecast['Day']['PrecipitationProbability']

                if aver_temp < 0 or aver_temp > 35 or wind_speed > 50 or prec_prob > 70:
                    condition = "неблагоприятные"
                else:
                    condition = "благоприятные"

                weather_data = {
                    'City': city_names[i],
                    'Date': date,
                    'Average Temperature': aver_temp,
                    'Wind Speed': wind_speed,
                    'Precipitation Probability': prec_prob,
                    'Condition': condition
                }
                writer.writerow(weather_data)


# Получает ключ города по его названию
def get_city_key(city_name):
    """
    :param city_name: Название города.
    :return: Ключ города, если найден; иначе None.
    """
    url = f"{BASE_URL}/locations/v1/cities/search"
    params = {'q': city_name, 'apikey': API_KEY, 'language': 'ru-ru'}
    response = requests.get(url, params=params)

    if response.ok:
        data = response.json()
        if data:
            return data[0]["Key"]
    return None


# Получает данные о погоде для города на n дней
def get_weather_data(city, days):
    """
    :param city: Название города.
    :param days: Количество дней для прогноза.
    :return: Данные о погоде в формате JSON или None в случае ошибки.
    """
    city_key = get_city_key(city)
    url = f'{BASE_URL}/forecasts/v1/daily/{days}day/{city_key}'
    params = {'apikey': API_KEY, 'details': 'true'}
    response = requests.get(url, params=params)

    if response.ok:
        print(response.json())
        return response.json()
    return None


# Объединяет данные о погоде для городов
def combine_cities(start_city, intermediate_cities, end_city, days):
    """
    :param start_city: Начальный город.
    :param intermediate_cities: Список промежуточных городов.
    :param end_city: Конечный город.
    :param days: Количество дней для прогноза.
    :return: Список данных о погоде и список названий городов.
    """
    weather_data_list = []
    city_names = [start_city] + intermediate_cities + [end_city] if intermediate_cities else [start_city, end_city]

    start_weather_data = get_weather_data(start_city, days)
    if start_weather_data:
        weather_data_list.append(start_weather_data)

    for city in intermediate_cities:
        city_weather_data = get_weather_data(city.strip(), days)
        if city_weather_data:
            weather_data_list.append(city_weather_data)

    end_weather_data = get_weather_data(end_city, days)
    if end_weather_data:
        weather_data_list.append(end_weather_data)

    save_weather_data_to_csv(weather_data_list, 'weather_forecast.csv', city_names)
    return weather_data_list, city_names


# Обрабатывает запросы на главной странице
@app.route('/', methods=['GET', 'POST'])
def index():
    """
    :return: HTML-шаблон главной страницы или перенаправление на страницу с данными о погоде.
    """
    if request.method == 'POST':
        start_city = request.form['start_city']
        inter_cities = request.form.getlist('intermediate_city')
        end_city = request.form['end_city']
        days = int(request.form['days'])
        weather_data_list, city_names = combine_cities(start_city, inter_cities, end_city, days)

        if weather_data_list:
            return redirect(url_for('dashboard'))
        else:
            return render_template('error.html', message="Ошибка получения данных о погоде.")

    return render_template('index.html')


# Отображает графики с погодой
@app.route('/dashboard')
def dashboard():
    """
    :return: HTML-шаблон страницы с графиками.
    """
    df = pd.read_csv('weather_forecast.csv')
    cities = df['City'].unique()
    temperatures = []
    wind_speeds = []
    conditions = []

    for city in cities:
        city_data = df[df['City'] == city]
        temperatures.append(go.Scatter(
            x=city_data['Date'],
            y=city_data['Average Temperature'],
            mode='lines+markers',
            name=f'Average Temperature ({city})',
            line=dict(width=2)
        ))
        wind_speeds.append(go.Scatter(
            x=city_data['Date'],
            y=city_data['Wind Speed'],
            mode='lines+markers',
            name=f'Wind Speed ({city})',
            line=dict(width=2)
        ))
        conditions.append(go.Scatter(
            x=city_data['Date'],
            y=[list(cities).index(city)] * len(city_data),
            mode='markers',
            name=f'Condition ({city})',
            marker=dict(
                color=city_data['Condition'].map({
                    "благоприятные": "green",
                    "неблагоприятные": "red"
                }),
                size=10,
                symbol='circle'
            )
        ))
    dash_app.layout = html.Div(children=[
        html.H1(children='Weather Forecast'),
        dcc.Graph(
            id='temperature-graph',
            figure={
                'data': temperatures,
                'layout': go.Layout(
                    title='Average Temperature',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Temperature (°F)'},
                    hovermode='closest'
                )
            }
        ),
        dcc.Graph(
            id='wind-speed-graph',
            figure={
                'data': wind_speeds,
                'layout': go.Layout(
                    title='Wind Speed',
                    xaxis={'title': 'Date'},
                    yaxis={'title': 'Wind Speed (mi/h)'},
                    hovermode='closest'
                )
            }
        ),
        dcc.Graph(
            id='condition-graph',
            figure={
                'data': conditions,
                'layout': go.Layout(
                    title='Weather Conditions',
                    xaxis={'title': 'Date'},
                    yaxis={
                        'tickvals': list(range(len(cities))),
                        'ticktext': cities
                    },
                    hovermode='closest'
                )
            }
        )])
    return dash_app.index()


if __name__ == '__main__':
    app.run()
    dash_app.run()
