import pandas as pd
import requests
import time

# Load the stations CSV file
stations_df = pd.read_csv('stations_en_ar.csv')

# Define Google Maps Geocoding API endpoint and your API key
API_KEY = "AIzaSyBaLHKh8T7tLK5a_FIQfuUOmLt05qR4Uco"
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Function to get coordinates using the Google Maps API
def get_coordinates(station_name):
    params = {
        "address": station_name,
        "key": API_KEY
    }
    response = requests.get(GEOCODE_API_URL, params=params)
    if response.status_code == 200:
        result = response.json()
        if result['status'] == 'OK' and len(result['results']) > 0:
            location = result['results'][0]['geometry']['location']
            return location['lat'], location['lng']
    return None, None

# Initialize lists to store latitude and longitude
latitudes = []
longitudes = []

# Loop through each station to get coordinates
for index, row in stations_df.iterrows():
    station_name =   "محطة سكك حديد" +  " " + row['name_ar'] + ", " + row['name_en'] +", Egypt"
    print(f"Getting coordinates for: {station_name}")
    lat, lng = get_coordinates(station_name)
    latitudes.append(lat)
    longitudes.append(lng)
    print (lat, lng)
    time.sleep(1)  # Pause to avoid rate limits

# Add coordinates to the DataFrame
stations_df['location_lat'] = latitudes
stations_df['location_long'] = longitudes

# Save the updated DataFrame to a new CSV file
stations_df.to_csv('stations_with_coordinates.csv', index=False)
print("Coordinates saved to stations_with_coordinates.csv")