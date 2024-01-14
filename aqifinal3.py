# Importing the necessary libraries
import streamlit as st
import pandas as pd
from urllib.request import urlopen
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics.pairwise import euclidean_distances
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
import json
import requests
from streamlit_lottie import st_lottie
import pydeck as pdk
import snowflake.connector
import folium
from streamlit_folium import folium_static

# Initializing empty DataFrames
df_air_quality = None
df_air_quality_forecast = None

# Setting up the initial look of the web page:
# - its title to "Air quality around the World", 
# - layout to "wide", so that the content spans the entire width of the page, 
# - sidebar expanded (open) by default.
st.set_page_config(
    page_title="Air quality around the World",
    layout="wide",
    initial_sidebar_state="expanded")

# Defining the style which can be applied to elements in the Streamlit app to make the text within those elements have a larger font size
st.markdown("""
<style>
.big-font {
    font-size:80px !important;
}
</style>
""", unsafe_allow_html=True)

# The caching mechanism is used to optimize the performance of the app
# Defining a function used to load a Lottie file (a format for representing animations) 
@st.cache_data
def load_lottiefile(filepath: str):
    with open(filepath,"r") as f:
        return json.load(f)


# Options Menu
# Specifying the contents of the Streamlit sidebar:
# - options "Welcome," "City search," and "About."
# - icons for each option: 'sun', 'map', 'info-circle'
# - icon for the menu itself: 'cloud' 
# - the default_index parameter sets the default selected index to 0 (the "Welcome" option)
with st.sidebar:
    selected = option_menu('AQI - World', ["Welcome", 'City search','About'], 
        icons=['sun', 'map', 'info-circle'],menu_icon='cloud', default_index=0)
    # Loading a file containing animation properties into 'lottie' variable:
    lottie = load_lottiefile("similo3.json")
    # Displaying the Lottie animation
    st_lottie(lottie,key='loc')

# Setting up the "Welcome" Page
if selected=="Welcome":
    # Writing down what needs to be displayed in the page's headers
    st.title('Welcome to the Air Quality Index app')
    st.subheader('*A new tool to find Air Quality Index data across the whole world.*')

    st.divider()

    # Writing down the Use cases of our app:
    with st.container():
        col1,col2=st.columns(2)
        with col1:
        # In the left column (col1), there is a set of instructions on how to use the application
            
            st.header('How to use?')
            st.markdown(
                """
                - _Go to City Search and choose a desired city from a dropdown menu_
                - _If the city you are looking for isn't on the list, select "Custom" and enter it's name_
                - _You will immediately see a coloured message about the present state of air quality in the city_
                - _Subsequently, You will be able to look at details concerning pollutants, the weather and other variables_
                - _You will be also presented with a map and poluttion forecast for the upcoming days_
                - _Click the pin on the map to see current weather conditions_
                """
                )
        # Displaying the Lottie animation
        with col2:
            lottie2 = load_lottiefile("place2.json")
            st_lottie(lottie2, key='place',height=300,width=300)

    st.divider()
    
    # Displaying the info on the data which can be retrieved thanks to the app
    with st.container():
        col1,col2=st.columns(2)
        with col1:
            st.header('What info can You retrieve?')
            st.markdown(
                """
                - _Individual AQI for all pollutants (PM2.5, PM10, NO2, CO, SO2, Ozone)_
                - _Station name and its coordinates_
                - _Current weather conditions & its measurement time_
                - _Air Quality forecasts (for 3~8 days)_
                - _Name of the dominant pollutant_
                """
                )

        st.divider()
        
 # Setting up the Search page pt. 1
 
# But in the meantime ...
# Defining a function whose purpose is to simplify the structure of a nested dictionary (from the API)
# The function takes four parameters:
# - d: The input dictionary to be flattened.
# - parent_key='': A string representing the current parent key. It is used for concatenating keys.
# - sep='_': The separator used when concatenating keys.
# - exclude_keys=None: A list of keys to be excluded from the flattened dictionary.


def flatten_dict(d, parent_key='', sep='_', exclude_keys=None):
    if exclude_keys is None:
        exclude_keys = []
# - It initializes an empty list called items to store key-value pairs of the flattened dictionary.
    items = []
    if isinstance(d, dict):
        # k - key
        # v - value
        for k, v in d.items():
            new_key = f'{parent_key}{sep}{k}' if parent_key else k
            # - It checks if the current value (v) is a dictionary. If so, it recursively calls flatten_dict on the nested dictionary.
            if isinstance(v, dict):
                items.extend(flatten_dict(v, new_key, sep=sep, exclude_keys=exclude_keys).items())
            # - If the value is not a dictionary, it appends a key-value pair to the items list. 
            # - If the key is not in the exclude_keys, it appends the pair; otherwise, it is skipped.
            elif new_key not in exclude_keys:
                items.append((new_key, v))
    else:
        # Handling the case where the value is a string (or another non-dictionary type)
        items.append((parent_key, d))
# - Finally, it returns a dictionary created from the items list.
    return dict(items)

# Defining a function that retrieves air quality information for a specified city using the World Air Quality Index (WAQI) API. 
def get_air_quality(city):
    base_url = "https://api.waqi.info/"
    endpoint = f"/feed/{city}/?token=136f8d87c3aa5d2a7a6fe9b84cb80ac79abf0adf"
    url = base_url + endpoint

    try:
        response = requests.get(url)
        data = response.json()

        if response.status_code == 200:
            return data
        else:
            print(f"Error: {data['status']}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        return None

# Defining a function which fetches air quality data for a specified location using the get_air_quality function and processes the data into a DataFrame. 
def fetch_air_quality_data(selected_location, columns_to_exclude=None):
    global df_all  # Using the global keyword to access the df_all in the broader scope
    data_list = []

    result = get_air_quality(selected_location)

    if result:
        flat_data = flatten_dict(result['data'], exclude_keys=['city_location', 'forecast_daily_uvi', 'city_name', 'attributions', 'city_url', 'time_v',
                                                                'debug_sync', 'time_tz', 'time_iso', 'forecast_daily_o3', 'forecast_daily_pm10', 'forecast_daily_pm25'])
        city_data = {
            "city": selected_location,
            **flat_data
        }
        data_list.append(city_data)

    df_all = pd.DataFrame(data_list)
    df_all['city'] = df_all['city'].astype(str)
    df_all.set_index('city', inplace=True)
    # Renaming column names for better readability
    df_all.rename(columns={'iaqi_co_v': 'Carbon_Monoxyde',
                           'iaqi_h_v': 'Relative_Humidity',
                           'iaqi_no2_v': 'Nitrogen_Dioxide',
                           'iaqi_o3_v': 'Ozone',
                           'iaqi_p_v': 'Atmospheric_Pressure',
                           'iaqi_pm10_v': 'Particulate_Matter_(10µm)',
                           'iaqi_pm25_v': 'Particulate_Matter_(2.5µm)',
                           'iaqi_so2_v': 'Sulphur_Dioxide',
                           'iaqi_t_v': 'Temperature',
                           'iaqi_w_v': 'Wind',
                           'iaqi_dew_v': 'Dew',
                           'iaqi_r_v': 'Rain_(precipitation)',
                           'city_geo': 'Station_lat/long',
                           'time_s': 'Local_measurement_time',
                           'dominentpol': 'Dominent_pollutant',
                           'idx': 'Station_id',
                           'aqi': 'AQI',

                        
                        
                           }, inplace=True)

    # Checking if columns to exclude are present in the DataFrame
    if columns_to_exclude:
        columns_to_exclude = [col for col in columns_to_exclude if col in df_all.columns]
        df_all = df_all.drop(columns=columns_to_exclude)

    # Returning the resulting DataFrame
    return df_all

####################################################################################################
# Defining a function which generates a descriptive message based on the Air Quality Index (AQI) value
# It uses a series of if and elif statements to categorize the air quality level based on the specified ranges.
# Each range corresponds to a different descriptive message regarding the air quality and potential health implications.
def get_air_quality_message(aqi_value):
    if 0 <= aqi_value <= 50:
        return "Air quality is good. The air pollution pose no threat. The conditions ideal for outdoor activities."
    elif 51 <= aqi_value <= 100:
        return "Air quality is moderate. The air pollution pose minimal risk to exposed persons. People with respiratory diseases should limit outdoor exertion."
    elif 101 <= aqi_value <= 150:
        return "Air quality may be unhealthy for certains groups. People with respiratory diseases should limit outdoor exertion."
    elif 151 <= aqi_value <= 200:
        return "Air quality is unhealty. The air pollution pose a threat for people at risk which may experience health effects. Other people should limit spending time outdoors, especially when they experience symptoms such as cough or sore throat."
    elif 201 <= aqi_value <= 300:
        return "Air quality is bad. People at risk should avoid going outside. The rest should limit outdoor activities."
    elif aqi_value > 300:
        return "The quality of air is dangerously wrong. Those at risk should avoid going outside. Others should limit the output to a minimum. All outdoor activities are discouraged."

# Defining a function which assigns a color based on the Air Quality Index (AQI) value (for a more user-friendly, visual interface )  
def get_air_quality_color(aqi_value):
    if 0 <= aqi_value <= 50:
        return "lightgreen"
    elif 51 <= aqi_value <= 100:
        return "yellow"
    elif 101 <= aqi_value <= 150:
        return "orange"
    elif 151 <= aqi_value <= 200:
        return "red"
    elif 201 <= aqi_value <= 300:
        return "lavender"
    elif aqi_value > 300:
        return "burlywood"
 
# Defining a function that fetches air quality forecast data (specifically daily forecast data for O3, PM10, and PM2.5) 
# for a specified city using the World Air Quality Index (WAQI) API   
def get_air_quality_forecast(city):
    base_url = "https://api.waqi.info/"
    endpoint = f"/feed/{city}/?token=136f8d87c3aa5d2a7a6fe9b84cb80ac79abf0adf"
    url = base_url + endpoint

    response = requests.get(url)

    if response.status_code == 200:
        response_data = response.json()
        extracted_data = response_data.get('data', {})
        forecast_data = extracted_data.get('forecast', {})
        daily_forecast_data = forecast_data.get('daily', {})

        # Checking if 'daily_forecast_data' is a dictionary
        if isinstance(daily_forecast_data, dict):
            # Extracting relevant data for the DataFrames
            o3_daily_forecast_data = daily_forecast_data.get('o3', [{}])
            pm10_daily_forecast_data = daily_forecast_data.get('pm10', [{}])
            pm25_daily_forecast_data = daily_forecast_data.get('pm25', [{}])

            # Creating a DataFrame for daily forecast of O3:
            o3_daily_forecast_df = pd.DataFrame(o3_daily_forecast_data)
            o3_daily_forecast_df['city'] = city
            o3_daily_forecast_df.set_index('city', inplace=True)

            # Creating a DataFrame for daily forecast of PM10:
            pm10_daily_forecast_df = pd.DataFrame(pm10_daily_forecast_data)
            pm10_daily_forecast_df['city'] = city
            pm10_daily_forecast_df.set_index('city', inplace=True)

            # Creating a DataFrame for daily forecast of PM25:
            pm25_daily_forecast_df = pd.DataFrame(pm25_daily_forecast_data)
            pm25_daily_forecast_df['city'] = city
            pm25_daily_forecast_df.set_index('city', inplace=True)

            return o3_daily_forecast_df, pm10_daily_forecast_df, pm25_daily_forecast_df
        else:
            print(f"Warning: 'daily_forecast_data' has unexpected structure for city {city}")
    else:
        print(f"Error: {response.status_code} for city {city}")
        print(response.text)

# Defining a function which will return a DataFrame with column names prefixed by the specified prefix
# The function is used later on in add_prefixes() function
def add_prefixes(df, prefix):
    return df.rename(columns=lambda col: f"{prefix}_{col}")

def fetch_air_quality_forecast(selected_location):
    # Fetching air quality forecast data only for the selected city
    o3_df, pm10_df, pm25_df = get_air_quality_forecast(selected_location)

    # Adding prefixes to columns for each pollutant
    o3_df = add_prefixes(o3_df, 'o3')
    pm10_df = add_prefixes(pm10_df, 'pm10')
    pm25_df = add_prefixes(pm25_df, 'pm25')

    # Adding the city name as a column in each DataFrame
    o3_df['o3_city'] = selected_location
    pm10_df['pm10_city'] = selected_location
    pm25_df['pm25_city'] = selected_location

    # Concatenating the DataFrames along the columns
    combined_df = pd.concat([o3_df, pm10_df, pm25_df], axis=1)

    return combined_df



###########################################################################################
# Creating a line plot for air quality forecast data. 
# The resulting plot includes three lines representing the average values for O3, PM10, and PM2.5 pollutants
def plot_air_quality_forecast(df_air_quality_forecast):
    fig = px.line(df_air_quality_forecast, x=df_air_quality_forecast.index, y=["o3_avg", "pm10_avg", "pm25_avg"], title="Air Pollutants Forecast")
    st.plotly_chart(fig, use_container_width=True)

# Defining a function to display air quality data and forecasts for a selected city
def display_air_quality_data(city_select, df_air_quality):
    # Fetching air quality forecast data
    df_air_quality_forecast = fetch_air_quality_forecast(city_select)

    # Excluding specified columns from df_air_quality
    columns_to_exclude = ["Station_id", "iaqi_wa_v", "iaqi_wg_v",]
    df_air_quality = df_air_quality.drop(columns=columns_to_exclude, errors='ignore')
    # Excluding specified columns from df_air_quality_forecast
    columns_to_exclude2 = ["o3_city", "pm10_city", "pm25_city", "pm10_day", "pm25_day",]
    df_air_quality_forecast = df_air_quality_forecast.drop(columns=columns_to_exclude2, errors='ignore')
    # Renaming and formatting columns in df_air_quality_forecast
    df_air_quality_forecast = df_air_quality_forecast.rename(columns={'o3_day': 'Date'})
    df_air_quality_forecast['Date'] = pd.to_datetime(df_air_quality_forecast['Date']).dt.date
    df_air_quality_forecast.set_index('Date', inplace=True)

    st.divider()
    # Displaying DataFrames in Streamlit app
    st.dataframe(df_air_quality)
    st.dataframe(df_air_quality_forecast)

    # Checking if 'Station_lat/long' column is present in df_air_quality
    if 'Station_lat/long' in df_air_quality.columns:
        location_data = df_air_quality.at[city_select, 'Station_lat/long']
        # Displaying a folium map (see the display_folium_map() below)
        display_folium_map(city_select, location_data, df_air_quality)

        # Plotting air quality forecast
        plot_air_quality_forecast(df_air_quality_forecast)

# Creating a function to display a Folium map with a marker at the specified location for the selected city
def display_folium_map(city_select, location_data, df_air_quality):
    # The function checks the format of location_data (either a list of coordinates or a string with comma-separated latitude and longitude).
    if isinstance(location_data, list):
        latitude, longitude = location_data
    elif isinstance(location_data, str):
        latitude, longitude = map(float, location_data.split(','))
    else:
        st.error("Invalid data format for location coordinates.")
# It extracts air quality parameters from the df_air_quality DataFrame for the selected city.
    aqi = df_air_quality.at[city_select, 'AQI']
    temperature = df_air_quality.at[city_select, 'Temperature']
    atmospheric_pressure = df_air_quality.at[city_select, 'Atmospheric_Pressure']
    wind = df_air_quality.at[city_select, 'Wind']
    relative_humidity = df_air_quality.at[city_select, 'Relative_Humidity']
    dominant_pollutant = df_air_quality.at[city_select, 'Dominent_pollutant']
# It creates a Folium map (m) centered at the specified location.
    m = folium.Map(location=[latitude, longitude], zoom_start=7)

# It generates a popup content for the marker, including information about AQI, temperature, atmospheric pressure, wind, humidity, and the dominant pollutant.
    popup_content = f"<b>{city_select}</b><br>AQI: {aqi}<br>Temperature: {temperature}<br>Pressure: {atmospheric_pressure}<br>Wind: {wind}<br>Humidity: {relative_humidity}<br>Dominant Pollutant: {dominant_pollutant}"
# It adds a marker to the map with the popup content.
    folium.Marker([latitude, longitude], popup=popup_content).add_to(m)
# Displaying the Folium map in the Streamlit app.
    folium_static(m)

# Setting up the Search page pt. 2
# City search
if selected == "City search":
    # Writing down what text needs to be displayed in the header
    st.subheader('Select location for which You would like to see the Air Quality data')
    # Defining a list of city options (for the selectbox)
    city_options = ['Custom', "Szczecin", "Bydgoszcz", "Torun", "Lublin", "Gorzow Wielkopolski", "Zielona Gora", "Lodz", "Krakow", "Wroclaw", "Opole", "Rzeszow", "Bialystok", "Gdansk", "Katowice", "Kielce", "Poznan", "Warszawa"]
    # Creating a selectbox (dropdown) to choose a city
    city_select = st.selectbox(label='Select City', options=city_options, index=len(city_options) - 1, label_visibility='collapsed')

    # Setting up an alternative option -> the custom city input
    if city_select == 'Custom':
        city_select = st.text_input('Enter Custom City:')
        if city_select:
            # Fetching air quality data for the custom city
            df_air_quality_custom = fetch_air_quality_data(city_select)
            if not df_air_quality_custom.empty:
                # Getting AQI value and displaying information
                if 'AQI' in df_air_quality_custom.columns:
                    aqi_value = df_air_quality_custom.at[city_select, 'AQI']
                    message = get_air_quality_message(aqi_value)
                    color = get_air_quality_color(aqi_value)
                    st.info(message)
                    st.markdown(f'<style>div.st-cc{{background-color: {color};}}</style>', unsafe_allow_html=True)
                    display_air_quality_data(city_select, df_air_quality_custom)
                else:
                    st.warning(f"No 'AQI' data available for the custom city: {city_select}")
            else:
                st.warning(f"No data available for the custom city: {city_select}")
    # Fetching air quality data for the selected city from the dropdown            
    else:
        df_air_quality_selected = fetch_air_quality_data(city_select)
        if not df_air_quality_selected.empty:
            aqi_value = df_air_quality_selected.at[city_select, 'AQI']
            message = get_air_quality_message(aqi_value)
            color = get_air_quality_color(aqi_value)
            st.info(message)
            st.markdown(f'<style>div.st-cc{{background-color: {color};}}</style>', unsafe_allow_html=True)
            display_air_quality_data(city_select, df_air_quality_selected)
        else:
            st.warning(f"No data available for the selected city: {city_select}")
            aqi_value = df_air_quality_selected.at[city_select, 'AQI']
            message = get_air_quality_message(aqi_value)
            color = get_air_quality_color(aqi_value)
            st.info(message)
            st.markdown(f'<style>div.st-cc{{background-color: {color};}}</style>', unsafe_allow_html=True)
            display_air_quality_data(city_select, df_air_quality_selected)

        
# Setting up the About page
if selected=='About':
    # The "API reference" section provides a layout with three columns to show the source, description, and link for each data source.
    st.title('API reference')
    st.subheader('All data for this project was publicly sourced from:')
    col1,col2,col3=st.columns(3)
    col1.subheader('Source')
    col2.subheader('Description')
    col3.subheader('Link')
    # The information for the World Air Quality Index Project and SimiLo is displayed in separate containers.
    with st.container():
        col1,col2,col3=st.columns(3)
        col1.write(':blue[The World Air Quality Index Project]')
        col2.write('The World Air Quality Index project is a non-profit project started in 2007. Its mission is to promote air pollution awareness for citizens and provide a unified and world-wide air quality information.')
        col3.write('https://aqicn.org/api/')
    
    with st.container():
        col1,col2,col3=st.columns(3)
        col1.write(':blue[SimiLo]')
        col2.write('SimiLo is a Streamlit app created by Kevin Soderholm. It has been used as a template for this project.')
        col3.write('https://similobeta2.streamlit.app/')
    
    
    st.divider()
# The "Creators" section provides information about the creators of the project, including names and the university affiliation.
st.title('Creators')
col1 = st.columns(1)
col1[0].write('')
col1[0].write('')
col1[0].write('**Names:**    Oliwia K., Alicja R., Grzegorz L.')
col1[0].write('**University:**    Kozminski University')