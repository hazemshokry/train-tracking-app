import csv
import googlemaps

# --- IMPORTANT: Using the API key you provided. ---
# For security in a real application, it's best to load this 
# from a secure source like an environment variable.
Maps_API_KEY = "AIzaSyBaLHKh8T7tLK5a_FIQfuUOmLt05qR4Uco"

def read_stations_from_csv(filename="stations_en_ar.csv"):
    """Reads station pairs from a CSV file.
    
    Args:
        filename (str): The path to the input CSV file. 
                        Expected columns: name_en, name_ar
                        
    Returns:
        list: A list of tuples, where each tuple is (english_name, arabic_name).
    """
    station_pairs = []
    try:
        with open(filename, mode='r', encoding='utf-8') as infile:
            reader = csv.reader(infile)
            next(reader) # Skip header row
            for row in reader:
                if row: # Ensure row is not empty
                    station_pairs.append((row[0], row[1]))
        print(f"--- Successfully read {len(station_pairs)} stations from '{filename}' ---")
    except FileNotFoundError:
        print(f"--- ERROR: Input file not found at '{filename}' ---")
    return station_pairs

def get_station_coordinates_places(station_pairs, api_key):
    """
    Fetches coordinates using the Google Places API (Find Place).
    It uses a hybrid query with both English and Arabic names to improve accuracy.

    Args:
        station_pairs (list): A list of tuples, where each tuple contains 
                              the English and Arabic name of a station.
        api_key (str): Your Google Maps API key.

    Returns:
        dict: A dictionary where keys are English station names and values are the result.
    """
    if not api_key or "YOUR_Maps_API_KEY" in api_key:
        print("\n--- Google Maps search skipped: Please provide a valid API key. ---")
        return {}
        
    gmaps = googlemaps.Client(key=api_key)
    coordinates_data = {}
    print("\n--- Fetching coordinates using Google Places API ---")

    for english_name, arabic_name in station_pairs:
        # --- THIS IS THE MODIFIED LINE ---
        # The Arabic query is now more specific, as requested.
        query = f'"{english_name} train station", محطة قطار {arabic_name}, Egypt'
        
        print(f"  Searching for '{query}'...")
        try:
            places_result = gmaps.find_place(
                query,
                'textquery',
                fields=['place_id', 'name', 'formatted_address', 'geometry']
            )
            
            result_entry = {'query': query, 'english_name': english_name, 'arabic_name': arabic_name}
            
            if places_result and 'candidates' in places_result and places_result['candidates']:
                candidate = places_result['candidates'][0]
                location = candidate['geometry']['location']
                result_entry.update({
                    'latitude': location['lat'],
                    'longitude': location['lng'],
                    'address': candidate.get('formatted_address', 'N/A'),
                    'found_name': candidate.get('name', 'N/A')
                })
            else:
                result_entry['error'] = 'Location not found'
            
            coordinates_data[english_name] = result_entry

        except googlemaps.exceptions.ApiError as e:
            print(f"    Google Places API Error: {e}")
            coordinates_data[english_name] = {'error': f'Google Places API Error: {e}'}
            
    return coordinates_data

def generate_output_files(results_data):
    """Generates a CSV and two SQL files from the fetched coordinate data."""
    if not results_data:
        print("--- No data to process for output files. ---")
        return

    print("\n--- Generating output files ---")
    
    # Define filenames
    csv_output_file = "data-mining/final_stations_with_coordinates.csv"
    sql_update_file = "data-mining/final_update_stations_with_coordinates.sql"
    sql_insert_file = "data-mining/final_insert_stations_with_coordinates.sql"

    # --- 1. Create the new CSV file with coordinates ---
    with open(csv_output_file, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['english_name', 'arabic_name', 'latitude', 'longitude', 'found_name', 'address']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for station_name, data in results_data.items():
            if 'error' not in data:
                writer.writerow({
                    'english_name': data['english_name'],
                    'arabic_name': data['arabic_name'],
                    'latitude': data['latitude'],
                    'longitude': data['longitude'],
                    'found_name': data['found_name'],
                    'address': data['address']
                })
    print(f"  Successfully created '{csv_output_file}'")

    # --- 2. Create the SQL files ---
    with open(sql_update_file, 'w', encoding='utf-8') as f_update, \
         open(sql_insert_file, 'w', encoding='utf-8') as f_insert:
        
        f_update.write("-- SQL statements to update coordinates for existing stations\n")
        f_insert.write("-- SQL statements to insert new stations with coordinates\n")

        for station_name, data in results_data.items():
            if 'error' not in data:
                lat = data['latitude']
                lon = data['longitude']
                name_en = data['english_name'].replace("'", "''") # Escape single quotes for SQL
                name_ar = data['arabic_name'].replace("'", "''")

                # Generate UPDATE statement
                update_sql = f"UPDATE stations SET location_lat = {lat}, location_long = {lon} WHERE name_en = '{name_en}';\n"
                f_update.write(update_sql)

                # Generate INSERT statement
                insert_sql = f"INSERT INTO stations (name_en, name_ar, code, location_lat, location_long) VALUES ('{name_en}', '{name_ar}', NULL, {lat}, {lon});\n"
                f_insert.write(insert_sql)

    print(f"  Successfully created '{sql_update_file}'")
    print(f"  Successfully created '{sql_insert_file}'")


# --- Main Execution ---

if __name__ == "__main__":
    # 1. Read stations from the input CSV file
    # Ensure you have a file named 'input_stations.csv' in the same directory.
    stations_to_process = read_stations_from_csv("data-mining/stations_en_ar.csv")

    if stations_to_process:
        # 2. Fetch coordinates using the Google API
        google_results = get_station_coordinates_places(stations_to_process, Maps_API_KEY)

        # 3. Generate the output CSV and SQL files
        generate_output_files(google_results)

        print("\n--- ✅ Process Complete ---")