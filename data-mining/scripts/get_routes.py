import requests
import time
import csv
import os

# --- Configuration ---
# Input CSV file path with train numbers
INPUT_CSV_FILE = 'data-mining/new_07_15/trains_data.csv'
# Output directory for the SQL file
OUTPUT_DIR = 'data-mining/new_07_15'
# Output SQL file path
INSERT_SQL_FILE = os.path.join(OUTPUT_DIR, 'insert_routes.sql')
# Database table name
DB_TABLE_NAME = 'routes'

# --- Functions ---

def read_train_numbers(file_path):
    """
    Reads train numbers from the first column of a CSV file.
    Returns a list of train numbers or None if the file doesn't exist.
    """
    if not os.path.exists(file_path):
        return None
        
    train_numbers = []
    with open(file_path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        try:
            next(reader)  # Skip the header row
            for row in reader:
                if row: # Ensure row is not empty
                    train_numbers.append(row[0])
        except StopIteration:
            # This handles the case of an empty file (or a file with only a header)
            pass
    return train_numbers

def fetch_train_data(train_number):
    """Fetches and parses train data from the API."""
    # The API endpoint URL for fetching train details.
    url = f'https://egytrains.com/_next/data/Z_85_ix5qbw5em7POicYo/train/{train_number}.json'
    try:
        # Makes a GET request to the API
        response = requests.get(url, timeout=10)
        # Checks if the request was successful
        if response.status_code == 200:
            data = response.json()
            train_info = data.get('pageProps', {}).get('data', {})
            cities = train_info.get('cities', [])
            return cities
        else:
            print(f"Failed to fetch data for train {train_number}. Status code: {response.status_code}")
            return []
    except requests.RequestException as e:
        print(f"An error occurred while fetching data for train {train_number}: {e}")
        return []

def format_time_for_sql(time_str):
    """Formats HH:MM time string for SQL, returning NULL for empty values."""
    if not time_str or not time_str.strip():
        return "NULL"
    # Returns the time string enclosed in single quotes for SQL.
    return f"'{time_str}'"

# --- Main Execution ---

def main():
    """Main function to run the data processing and file generation."""
    # Create output directory if it doesn't exist
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    train_numbers = read_train_numbers(INPUT_CSV_FILE)

    # If the input file doesn't exist, create a sample and exit.
    if train_numbers is None:
        print(f"Error: Input file '{INPUT_CSV_FILE}' not found.")
        # Create a dummy file for demonstration
        with open(INPUT_CSV_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['train_number'])
            writer.writerow(['2'])
            writer.writerow(['982'])
            writer.writerow(['990'])
        print(f"\nA sample '{INPUT_CSV_FILE}' has been created for you.")
        print("Please populate it with the train numbers you want to process and run the script again.")
        return # Stop execution

    if not train_numbers:
        print(f"Warning: '{INPUT_CSV_FILE}' is empty or contains no train numbers. Nothing to process.")
        return

    # Use 'with' to ensure the output file is properly closed
    try:
        with open(INSERT_SQL_FILE, mode='w', encoding='utf-8') as insert_file:
            # Write initial comment to the SQL file
            insert_file.write(f"-- INSERT statements for table: {DB_TABLE_NAME}\n\n")

            # Iterate over each train number and fetch its route data
            for train_number in train_numbers:
                train_data = fetch_train_data(train_number)
                
                print(f"Processing Train Number: {train_number}")
                
                if not train_data:
                    print(f"  No station data found for train {train_number}.")
                    continue

                # Process each station in the train's route
                for sequence, station in enumerate(train_data):
                    # Sanitize station name for SQL by escaping single quotes
                    station_name = station.get('name', 'Unknown Station').replace("'", "''")
                    arrival = station.get('a', '')
                    departure = station.get('d', '')
                    
                    # Format arrival and departure times for SQL
                    arrival_sql = format_time_for_sql(arrival)
                    departure_sql = format_time_for_sql(departure)

                    # Per your requirement: first station has NULL arrival time
                    if sequence == 0:
                        arrival_sql = "NULL"
                    
                    # Per your requirement: last station has NULL departure time
                    if sequence == len(train_data) - 1:
                        departure_sql = "NULL"

                    # Create the final INSERT statement with the subquery for station_id
                    insert_query = (
                        f"INSERT INTO {DB_TABLE_NAME} (train_number, station_id, sequence_number, scheduled_arrival_time, scheduled_departure_time) "
                        f"VALUES ({train_number}, (SELECT id FROM stations WHERE name_en='{station_name}'), {sequence}, {arrival_sql}, {departure_sql});\n"
                    )
                    insert_file.write(insert_query)

                # Add a blank line to the SQL file for readability between trains
                insert_file.write("\n")
                
                print(f"  Successfully processed {len(train_data)} stations.")
                
                # A brief delay to avoid overwhelming the server with requests
                time.sleep(1)

        print("\n--- Processing Complete ---")
        print(f"SQL INSERT statements have been written to: {INSERT_SQL_FILE}")

    except IOError as e:
        print(f"\nAn error occurred while writing to the file: {e}")

if __name__ == '__main__':
    main()
