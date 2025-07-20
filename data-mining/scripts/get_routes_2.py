import requests
import time
import csv

# Input CSV file path with train numbers
input_csv_file = 'trains_data.csv'  # Update this path if needed
output_sql_file = 'routes_insert.sql'

# Function to read train numbers from CSV file
def read_train_numbers(file_path):
    """Reads train numbers from a CSV file."""
    train_numbers = []
    try:
        with open(file_path, mode='r', encoding='utf-8') as file:
            reader = csv.reader(file)
            next(reader)  # Skip the header row
            for row in reader:
                train_numbers.append(row[0])  # Assuming train number is in the first column
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
    return train_numbers

# Function to fetch train data from API
def fetch_train_data(train_number):
    """Fetches route data for a specific train number from the API."""
    url = f'https://egytrains.com/_next/data/Z_85_ix5qbw5em7POicYo/train/{train_number}.json'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        train_info = data.get('pageProps', {}).get('data', {})
        cities = train_info.get('cities', [])
        return cities
    except requests.exceptions.RequestException as e:
        print(f"Failed to fetch data for train {train_number}: {e}")
        return []

# --- Main Script Execution ---

# Fetch train numbers from the input CSV
train_numbers = read_train_numbers(input_csv_file)

# Open the output SQL file
with open(output_sql_file, mode='w', encoding='utf-8') as sql_file:
    # Iterate over each train number and fetch its data
    for train_number in train_numbers:
        print(f"Fetching data for Train Number: {train_number}")
        route_data = fetch_train_data(train_number)
        
        if not route_data:
            continue # Skip to the next train if no data was fetched

        sql_file.write(f"-- Routes for Train {train_number}\n")
        
        # Process each station in the route
        for sequence, station in enumerate(route_data):
            station_name = station.get('name', '').replace("'", "''") # Escape single quotes for SQL
            arrival = station.get('a', '')
            departure = station.get('d', '')

            # For the first station (sequence 0), arrival time is NULL
            arrival_time = f"'{arrival}'" if sequence > 0 and arrival else 'NULL'
            
            # For the last station, departure time is NULL
            departure_time = f"'{departure}'" if sequence < len(route_data) - 1 and departure else 'NULL'

            # Construct the SQL INSERT statement
            insert_statement = (
                f"INSERT INTO routes (train_number, station_id, sequence_number, scheduled_arrival_time, scheduled_departure_time) "
                f"VALUES ({train_number}, (SELECT id FROM stations WHERE name_en='{station_name}'), {sequence}, {arrival_time}, {departure_time});\n"
            )
            
            # Write the statement to the file
            sql_file.write(insert_statement)

        # Add a blank line for readability between trains
        sql_file.write("\n")
        
        # Delay to avoid overwhelming the server
        time.sleep(1)

print(f"SQL INSERT statements have been written to {output_sql_file}")
