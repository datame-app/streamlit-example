from collections import namedtuple
import altair as alt
import extra_streamlit_components as stx
import json
import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import requests
import streamlit as st


CLIENT_ID = st.secrets["CLIENT_ID"]
CLIENT_SECRET = st.secrets["CLIENT_SECRET"]

data_range = None


@st.cache
def load_steps_data(user_id=None):
    start_date = data_range[0].date()
    end_date = data_range[1].date()
    response_data = {'data': []}
    if user_id:
        url = f"https://api.spikeapi.com/metrics/steps/?user_id={user_id}&start_date={start_date}&end_date={end_date}"
        headers = {'authorizationtoken': CLIENT_SECRET}
        response = requests.request("GET", url, headers=headers)
        if response.status_code < 400:
            response_data = response.json()
    steps_data = pd.DataFrame.from_dict(response_data['data'])
    steps_data.rename(columns={'value': 'steps'}, inplace=True)
    return response_data, steps_data


@st.cache(allow_output_mutation=True)
def load_sleep_data(user_id=None):
    start_date = data_range[0].date()
    end_date = data_range[1].date()
    response_data = {'data': []}
    if user_id:
        url = f"https://api.spikeapi.com/metrics/sleep/?user_id={user_id}&start_date={start_date}&end_date={end_date}"
        headers = {'authorizationtoken': CLIENT_SECRET}
        response = requests.request("GET", url, headers=headers)
        if response.status_code < 400:
            response_data = response.json()
    data = pd.DataFrame.from_dict(response_data['data'])
    return response_data, data


def load_summaries_data():
    return pd.read_json('data_samples/activities_summary_2022-03-01_2022-07-31.json')


@st.cache
def load_heart_data(user_id=None):
    start_date = data_range[0].date()
    end_date = data_range[1].date()
    response_data = {'data': []}
    data = pd.DataFrame()
    if user_id:
        url = f"https://api.spikeapi.com/metrics/heart/?user_id={user_id}&start_date={start_date}&end_date={end_date}"
        headers = {'authorizationtoken': CLIENT_SECRET}
        response = requests.request("GET", url, headers=headers)
        if response.status_code < 400:
            response_data = response.json()
            data = pd.DataFrame.from_dict(response_data['data'])
            data = data.drop(['heart_rate_samples'], axis=1)
    return response_data, data


@st.cache
def load_glucose_data(user_id=None):
    start_date = data_range[0].date()
    end_date = data_range[1].date()
    response_data = {'data': []}
    if user_id:
        url = f"https://api.spikeapi.com/metrics/glucose/?user_id={user_id}&start_date={start_date}&end_date={end_date}"
        headers = {'authorizationtoken': CLIENT_SECRET}
        response = requests.request("GET", url, headers=headers)
        if response.status_code < 400:
            response_data = response.json()
    data = pd.DataFrame.from_dict(response_data['data'])
    return response_data, data


def sidebar():
    global data_range
    st.sidebar.markdown("""
    <style>
            .logo-wrapper {text-align: center; margin-top: -70px;} 
            .logo {width: 150px;}
            .e1fqkh3o3 {display:none;}
    </style>""",
                        unsafe_allow_html=True)

    st.sidebar.markdown("""
                           <div class="logo-wrapper">
                                <img src="https://spikeapi.com/wp-content/uploads/2021/11/spike-logo-n.svg"
                                     class="logo" alt="">
                           </div>
                        """,
                        unsafe_allow_html=True
                        )
    if "date_range" not in st.session_state:
        st.session_state["date_range"] = (datetime.now() - timedelta(days=7), datetime.now())
    data_range = st.sidebar.slider(
        "Select data range",
        key="date_range",
        on_change=slider_changed,
        # value=(datetime(2022, 8, 1, 0, 0), datetime(2022, 9, 1, 0, 0)),
        min_value=datetime.now() - timedelta(days=30),
        max_value=datetime.now(),
        step=timedelta(days=1),
        format="MM/DD")


def slider_changed():
    if data_range[0] == st.session_state["date_range"][0]:
        start = st.session_state["date_range"][1] - timedelta(days=7)
        end = st.session_state["date_range"][1]
    else:
        start = st.session_state["date_range"][0]
        end = st.session_state["date_range"][0] + timedelta(days=7)
    st.session_state["date_range"] = (start, end)


@st.cache(allow_output_mutation=True)
def get_manager():
    return stx.CookieManager()


cookie_manager = get_manager()
cookies = cookie_manager.get_all()

query_params = st.experimental_get_query_params()
user_id = query_params.get('user_id', [None])[0]
# st.write("User ID:", user_id)
if user_id:
    cookie_manager.set("user_id", user_id)
else:
    user_id = cookies.get("user_id")

sidebar()
tab_sleep, tab_steps, tab_heart, tab_glucose, tab_code = st.tabs(["Sleep", "Steps", "Heart", "Glucose",
                                                                  "Code Example"])

if not user_id:
    st.write("Please, connect device")

with tab_sleep:
    response_data, sleep_data = load_sleep_data(user_id)
    if not sleep_data.empty:
        sleep_df = sleep_data.copy()
        sleep_df["total_sleep(min)"] = sleep_df.apply(lambda row: int(row.total_sleep / 60), axis=1)

        col1, col2, col3 = st.columns(3)
        total_diff = int((sleep_df.iloc[-1]["total_sleep"] - sleep_df.iloc[-2]["total_sleep"]) / 60)
        col1.metric("Total sleep",
                    str(int(sleep_df.iloc[-1]["total_sleep"] / 60)) + " min",
                    str(total_diff) + " min")
        total_deep = int((sleep_df.iloc[-1]["deep"] - sleep_df.iloc[-2]["deep"]) / 60)
        col2.metric("Deep sleep",
                    str(int(sleep_df.iloc[-1]["deep"] / 60)) + " min",
                    str(total_deep) + " min")
        total_rem = int((sleep_df.iloc[-1]["rem"] - sleep_df.iloc[-2]["rem"]) / 60)
        col3.metric("Rem sleep",
                    str(int(sleep_df.iloc[-1]["rem"] / 60)) + " min",
                    str(total_rem) + " min")

        sleep_df['date_'] = pd.to_datetime(sleep_df['date'], format='%Y-%m-%d')

        sleep_df['weekday'] = sleep_df['date_'].apply(lambda x: x.day_name())
        df_week_sleep = sleep_df.groupby(['weekday'])['total_sleep(min)'].mean() \
            .reset_index().sort_values('total_sleep(min)', ascending=False)
        base = alt.Chart(df_week_sleep).mark_bar(
            cornerRadiusTopLeft=3,
            cornerRadiusTopRight=3
        ).encode(
            x=alt.X('total_sleep(min)'),
            y=alt.Y('weekday', sort='-x')
        )

        st.altair_chart(base, use_container_width=True)
        chart = alt.Chart(sleep_df).mark_line().encode(
            x=alt.X('monthdate(date):T', axis=alt.Axis(title='Date'.upper())),  # , format=("%d %b")
            y=alt.Y('total_sleep(min):Q', scale=alt.Scale(domain=(sleep_df['total_sleep(min)'].min(),
                                                                  sleep_df['total_sleep(min)'].max()))),
            color=alt.Color("source:N")
        ).configure_legend(
            orient='bottom'
        )
        st.altair_chart(chart, use_container_width=True)
    if user_id:
        st.write(response_data)

with tab_steps:
    response_data, steps_data = load_steps_data(user_id)
    if not steps_data.empty:
        chart = alt.Chart(steps_data).mark_line().encode(
            x=alt.X('monthdate(date):T', axis=alt.Axis(title='Date'.upper())),
            y=alt.Y('steps:Q'),
            color=alt.Color("source:N")
        )
        st.altair_chart(chart, use_container_width=True)
    if user_id:
        st.write(response_data)

with tab_heart:
    response_data, heart_data = load_heart_data(user_id)
    if not heart_data.empty:
        heart_df = heart_data.dropna(subset=['resting_hr'])
        if not heart_df.empty:
            chart = alt.Chart(heart_df).mark_line().encode(
                x=alt.X('monthdate(date):T', axis=alt.Axis(title='Date'.upper())),
                y=alt.Y('resting_hr:Q', scale=alt.Scale(domain=[heart_df['resting_hr'].min(),
                                                                heart_df['resting_hr'].max()])),
                color=alt.Color("source:N")
            )
            st.altair_chart(chart, use_container_width=True)
    if user_id:
        st.write(response_data)

with tab_glucose:
    response_data, glucose_data = load_glucose_data(user_id)
    if not glucose_data.empty:
        chart = alt.Chart(glucose_data).mark_line().encode(
            x=alt.X('time:T', axis=alt.Axis(title='Time'.upper(), format='%e %b, %Y')),
            y=alt.Y('value:Q'),
            color=alt.Color("source_id:N")
        )
        st.altair_chart(chart, use_container_width=True)

    if user_id:
        st.write(response_data)

with tab_code:
    code = '''
url = (
    f"https://api.spikeapi.com/metrics/sleep/?"
    f"user_id={user_id}&start_date={start_date}&end_date={end_date}"
)
headers = {'authorizationtoken': CLIENT_SECRET}
response = requests.request("GET", url, headers=headers)
if response.status_code < 400:
    response_data = response.json()
    data = pd.DataFrame.from_dict(response_data['data'])
    '''

    st.code(code, language='python')
