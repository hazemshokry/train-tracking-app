import requests
import time
import csv

# Input CSV file path with train numbers
input_csv_file = 'trains_data.csv'  # Update this path if needed
output_csv_file = 'train_routes_with_station_name.csv'

# Function to read train numbers from CSV file
def read_train_numbers(file_path):
    train_numbers = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header row
        for row in reader:
            train_numbers.append(row[0])  # Assuming train number is in the first column
    return train_numbers

# Function to fetch train data from API and parse it
def fetch_train_data(train_number):
    url = f'https://egytrains.com/_next/data/qYQO4LZb0GzIWuO0yo6iR/train/{train_number}.json'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        train_info = data.get('pageProps', {}).get('data', {})
        cities = train_info.get('cities', [])
        train_name = train_info.get('name', train_number)  # Default to train number if name isn't available
        return train_name, cities
    else:
        print(f"Failed to fetch data for train {train_number}")
        return train_number, []

# Fetch train numbers from the input CSV
train_numbers = read_train_numbers(input_csv_file)

# Write the parsed train routes data to output CSV
with open(output_csv_file, mode='w', newline='', encoding='utf-8') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(['Train Number', 'Train Name', 'Station Sequence Number', 'Station Name', 'Scheduled Arrival', 'Scheduled Departure'])  # Header

    # Iterating over each train number and fetching data
    for train_number in train_numbers:
        train_name, train_data = fetch_train_data(train_number)
        
        # Print train number and name
        print(f"Fetching data for Train Number: {train_number}, Train Name: {train_name}")
        
        # Writing each station's data with sequence number starting from 0
        for sequence, station in enumerate(train_data):
            station_name = station.get('name', '')
            arrival = station.get('a', '')
            departure = station.get('d', '')
            print(f"  Station {sequence} - {station_name}: Arrival - {arrival}, Departure - {departure}")
            writer.writerow([train_number, train_name, sequence, station_name, arrival, departure])
        
        # Delay to avoid hitting the server too frequently
        time.sleep(1)

print(f"Data has been written to {output_csv_file}")