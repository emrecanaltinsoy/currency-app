import streamlit as st
import pandas as pd
import plotly.express as px
import datetime
import requests
from bs4 import BeautifulSoup
from fbprophet import Prophet
from fbprophet.plot import plot_plotly

st.write("""# Currency app""")

st.sidebar.header("User Input")

option = st.sidebar.selectbox(
    "How would you like to do?",
    ("View Historical Currency Charts", "Check current rates", "Forecast Prediction"),
)


#@st.cache
def read_data():
    url = "https://raw.githubusercontent.com/emrecanaltinsoy/forex_data/main/forex_usd_data.csv"
    data = pd.read_csv(url)
    cols = data.columns
    return data, cols[1:]


#@st.cache
def get_range(data, date_range):
    start_index = data.index[data["date(y-m-d)"] == str(date_range[0])].tolist()[0]
    end_index = data.index[data["date(y-m-d)"] == str(date_range[1])].tolist()[0]
    data = data.iloc[start_index : end_index + 1]
    cols = data.columns
    dates = data["date(y-m-d)"]
    return data, dates


#@st.cache
def scrape_currency():
    today = datetime.date.today()

    base_url = "https://www.x-rates.com/historical/?from=USD&amount=1&date"

    year = today.year
    month = today.month if today.month > 9 else f"0{today.month}"
    day = today.day if today.day > 9 else f"0{today.day}"

    URL = f"{base_url}={year}-{month}-{day}"

    page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")

    table = soup.find_all("tr")[12:]

    currencies = [table[i].text.split("\n")[1:3][0] for i in range(len(table))]
    currencies.insert(0, "date(y-m-d)")
    currencies.insert(1, "American Dollar")
    rates = [table[i].text.split("\n")[1:3][1] for i in range(len(table))]
    rates.insert(0, f"{year}-{month}-{day}")
    rates.insert(1, "1")
    curr_data = {currencies[i]: rates[i] for i in range(len(rates))}
    curr_data = pd.DataFrame(curr_data, index=[0])

    cols = curr_data.columns

    return curr_data, cols[1:]


#@st.cache
def train_model(data, currency, period):
    df_train = data[["date(y-m-d)", currency]]
    df_train = df_train.iloc[-365*2 :]
    df_train = df_train.rename(columns={"date(y-m-d)": "ds", currency: "y"})

    m = Prophet()
    m.fit(df_train)
    future = m.make_future_dataframe(periods=period)
    forecast = m.predict(future)

    return forecast, m

df_all, columns = read_data()

if option == "View Historical Currency Charts":
    st.write("This app can be used to view historical **currency** charts!")

    date_range = st.date_input(
        "Choose date range",
        value=(
            datetime.date(2011, 1, 1),
            datetime.date(2011, 1, 1) + datetime.timedelta(df_all.shape[0] - 1),
        ),
        min_value=datetime.date(2011, 1, 1),
        max_value=datetime.date(2011, 1, 1) + datetime.timedelta(df_all.shape[0] - 1),
    )

    df, dates = get_range(df_all, date_range)

    selected_curr = st.multiselect("Select currencies", columns)

    ok = st.button("View")
    if ok:
        if selected_curr:
            # st.write(df[selected_curr])

            for curr in selected_curr:
                fig = px.line(
                    x=dates,
                    y=df[curr],
                )
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title=curr,
                )
                st.write(fig)

elif option == "Check current rates":
    st.write("This app can be used to check current **currency** data!")
    daily_df, columns = scrape_currency()
    base_curr = st.selectbox("Select the base currency", columns)
    selected_curr = st.multiselect("Select currencies", columns)
    if selected_curr:
        base = daily_df[base_curr].astype(float)

        selected = daily_df[selected_curr].astype(float)

        converted = selected / float(base)
        st.write(converted)

elif option == "Forecast Prediction":
    currency = st.selectbox("Select the currency for prediction", columns)

    n_weeks = st.slider("Weeks of prediction", 4, 20, 8, 1)

    ok = st.button("Predict")
    if ok:
        train_state = st.text("Training the model...")
        pred, model = train_model(df_all, currency, period=n_weeks * 7)
        train_state.text("Model training completed!!")

        st.subheader("Forecast data")
        fig1 = plot_plotly(model, pred)
        st.plotly_chart(fig1)

