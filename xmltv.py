#version1.1
import requests
import json
import xml.etree.ElementTree as ET
import os
import sqlite3
from datetime import datetime, timedelta
import signal
import sys
import pwd
import grp

# Variables
LOG_FILE_PATH = '/24-7_xmltv_generator.log'  # Update this path as needed
CACHE_EXPIRATION_DAYS = 14  # Cache expiration time (2 weeks)
script_dir = os.path.dirname(os.path.abspath(__file__))  # Script directory
db_path = os.path.join(script_dir, 'cache.db')

# Logging
def log_message(message):
    with open(LOG_FILE_PATH, 'a') as log_file:
        log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")

# Load API Key
def load_api_key():
    api_info_path = os.path.join(script_dir, 'api_info.json')
    try:
        with open(api_info_path, 'r') as api_file:
            api_data = json.load(api_file)
            return api_data['tmdb_api_key']
    except Exception as e:
        log_message(f"Error loading API key: {str(e)}")
        sys.exit(1)

TMDB_API_KEY = load_api_key()

# SQLite cache setup
def create_cache_table():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache (
                name TEXT PRIMARY KEY,
                type TEXT,
                data TEXT,
                timestamp TEXT
            )
        ''')
        conn.commit()

# Cache helper functions
def save_cache(name, type, data):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO cache (name, type, data, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (name, type, json.dumps(data), timestamp))
        conn.commit()

def load_cache(name, type):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM cache WHERE name = ? AND type = ?', (name, type))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
    return None

def delete_cache_item(name, type):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM cache WHERE name = ? AND type = ?', (name, type))
        conn.commit()

# Function to list cached items by type (tv or movie)
def list_cache_items(type):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM cache WHERE type = ?', (type,))
        return cursor.fetchall()

# Function to delete specific cache item
def delete_specific_cache_item():
    tv_items = list_cache_items('tv')
    movie_items = list_cache_items('movie')

    if not tv_items and not movie_items:
        print("No items in cache.")
        return

    # List TV shows
    if tv_items:
        print("TV Shows in cache:")
        for idx, (name,) in enumerate(tv_items, 1):
            print(f"{idx}. {name} (tv)")
    
    # List Movies
    if movie_items:
        print("\nMovies in cache:")
        for idx, (name,) in enumerate(movie_items, len(tv_items) + 1):
            print(f"{idx}. {name} (movie)")
    
    user_input = input("\nEnter the number of the item to delete or 'skip' to skip: ").strip().lower()
    if user_input and user_input != 'skip':
        try:
            selected_index = int(user_input) - 1
            if selected_index < len(tv_items):
                name, = tv_items[selected_index]
                delete_cache_item(name, 'tv')
                print(f"Deleted {name} from TV cache.")
                log_message(f"Deleted {name} from TV cache.")
            elif selected_index - len(tv_items) < len(movie_items):
                name, = movie_items[selected_index - len(tv_items)]
                delete_cache_item(name, 'movie')
                print(f"Deleted {name} from Movie cache.")
                log_message(f"Deleted {name} from Movie cache.")
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number or 'skip'.")

# TMDB Search Logic
def get_tmdb_info(name, type="tv"):
    search_url = f"https://api.themoviedb.org/3/search/{type}?api_key={TMDB_API_KEY}&query={requests.utils.quote(name)}"
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()

        if not data['results']:
            log_message(f"No results found for {name}")
            return None
        return data['results']
    except Exception as e:
        log_message(f"Error fetching TMDB info for {name}: {str(e)}")
        return None

def get_tmdb_collection(name):
    search_url = f"https://api.themoviedb.org/3/search/collection?api_key={TMDB_API_KEY}&query={requests.utils.quote(name)}"
    try:
        response = requests.get(search_url)
        response.raise_for_status()
        data = response.json()

        if not data['results']:
            log_message(f"No collection found for {name}")
            return None
        return data['results']
    except Exception as e:
        log_message(f"Error fetching TMDB collection info for {name}: {str(e)}")
        return None

# Timeout handler
def timeout_handler(signum, frame):
    raise TimeoutError

# Function to handle user input with a 3-second timeout
def timed_input(prompt, timeout=3):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout)
    try:
        user_input = input(prompt)
        signal.alarm(0)  # Reset the alarm
        return user_input
    except TimeoutError:
        print("\nNo input provided. Default option 3 selected.")
        return "3"

# Prompt user to select item from TMDB results, with colored output and proper key handling
def select_item(items, name, type="tv"):
    print(f"Results found for {name}:")

    # Choose color codes (you can modify or rotate them as needed)
    color_codes = ["\033[31m", "\033[32m", "\033[33m", "\033[34m", "\033[35m", "\033[36m"]
    reset_code = "\033[0m"

    # Ensure the correct key is fetched based on the type or collection
    key = 'title' if type == "movie" else 'name'
    
    for idx, item in enumerate(items, 1):
        # Handle both movies and collections by checking if 'name' exists
        title = item.get('title') or item.get('name') or "Unknown"
        year = item.get('release_date', '')[:4] if 'release_date' in item else item.get('first_air_date', '')[:4]
        
        # Apply color (cycling through the color codes)
        color = color_codes[idx % len(color_codes)]
        colored_title = f"{color}{title}{reset_code}"
        
        print(f"{idx}. {colored_title} ({year})")

    user_choice = input(f"Enter the number of the correct match for {name} or hit Enter for default (1): ").strip()
    if not user_choice:
        user_choice = "1"

    try:
        selected_index = int(user_choice) - 1
        if 0 <= selected_index < len(items):
            selected_item = items[selected_index]
            title = selected_item.get('title') or selected_item.get('name') or "Unknown"
            description = selected_item.get('overview', 'No description available.')
            poster_path = selected_item.get('poster_path', '')
            poster = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else 'No image available.'

            return {
                "json_title": name,
                "title": title,
                "description": description,
                "logo": poster
            }
    except (ValueError, IndexError):
        print("Invalid input. Using default selection.")
        return select_item(items, name, type)

# JSON and Cache Synchronization
def sync_json_with_cache(json_data, type="tv"):
    cached_names = {row[0] for row in list_cache_items(type)}

    # Detect additions
    json_names = {show for show in json_data}
    added_items = json_names - cached_names
    deleted_items = cached_names - json_names

    # Handle additions
    for name in added_items:
        log_message(f"New show detected in JSON: {name}")
        print(f"Fetching information for new {type}: {name}")
        collections = get_tmdb_collection(name) if type == "movie" else None
        if collections:
            info = select_item(collections, name, "movie")
        else:
            info = select_item(get_tmdb_info(name, type=type), name, type)
        if info:
            save_cache(name, type, info)
    
    # Handle deletions
    for name in deleted_items:
        user_input = input(f"{name} was removed from the JSON file. Do you want to remove it from the cache? (y/n): ").strip().lower()
        if user_input == 'y':
            delete_cache_item(name, type)
            log_message(f"Deleted {name} from cache.")
        else:
            log_message(f"Kept {name} in cache.")

# EPG Generation
def create_epg(xml_filename, json_data, type="tv", slot_duration_hours=1):
    root = ET.Element("tv", attrib={"source-info-name": "SFTech EPG Generator"})
    start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    for name in json_data:
        item = load_cache(name, type)
        if not item:
            continue

        channel_id = item["json_title"].replace(" ", "_").lower()
        channel = ET.SubElement(root, "channel", id=channel_id)
        ET.SubElement(channel, "display-name").text = item["title"]

        if item.get("logo") and item["logo"] != 'No image available.':
            ET.SubElement(channel, "icon", src=item["logo"])

        num_slots = 48 // slot_duration_hours
        for slot in range(num_slots):
            start_time = (start_date + timedelta(hours=slot * slot_duration_hours)).strftime('%Y%m%d%H0000 +0000')
            stop_time = (start_date + timedelta(hours=(slot + 1) * slot_duration_hours)).strftime('%Y%m%d%H0000 +0000')
            programme = ET.SubElement(root, "programme", start=start_time, stop=stop_time, channel=channel_id)
            ET.SubElement(programme, "title", lang="en").text = item["title"]
            ET.SubElement(programme, "desc", lang="en").text = item["description"]
            ET.SubElement(programme, "category", lang="en").text = "Series" if type == "tv" else "Movie"
            
            if item.get("logo") and item["logo"] != 'No image available.':
                ET.SubElement(programme, "icon", src=item["logo"])

    tree = ET.ElementTree(root)
    xmltv_path = os.path.join(script_dir, xml_filename)
    tree.write(xmltv_path, encoding="UTF-8", xml_declaration=True)
    log_message(f"EPG file generated: {xmltv_path}")

    # Change file ownership and permissions
    try:
        uid = pwd.getpwnam("sftech13").pw_uid
        gid = grp.getgrnam("www-data").gr_gid
        os.chown(xmltv_path, uid, gid)
        os.chmod(xmltv_path, 0o775)
        log_message(f"File ownership changed to sftech13:www-data and permissions set to 775 for {xmltv_path}")
    except KeyError as e:
        log_message(f"Error changing file ownership or permissions: {str(e)}")

import sys
import os

# Main Script Execution
if __name__ == "__main__":
    create_cache_table()

    # Load the JSON files
    with open(os.path.join(script_dir, 'tv_shows.json'), 'r') as json_file:
        tv_data = json.load(json_file)["shows"]

    with open(os.path.join(script_dir, 'movies.json'), 'r') as json_file:
        movie_data = json.load(json_file)["movies"]

    # Automatically choose "3" for both when running in a non-interactive environment
    if not sys.stdin.isatty():
        user_choice = "3"
    else:
        user_choice = timed_input(
            "Enter 1 for TV shows, 2 for movies, 3 for both, 4 to delete cache, or 5 to delete specific item from cache (default: 3 for both): ",
            timeout=3
        )

    if user_choice == "1":
        sync_json_with_cache(tv_data, type="tv")
        create_epg("tv.xml", tv_data, type="tv")
    elif user_choice == "2":
        sync_json_with_cache(movie_data, type="movie")
        create_epg("movies.xml", movie_data, type="movie")
    elif user_choice == "3":
        sync_json_with_cache(tv_data, type="tv")
        create_epg("tv.xml", tv_data, type="tv")
        sync_json_with_cache(movie_data, type="movie")
        create_epg("movies.xml", movie_data, type="movie")
    elif user_choice == "4":
        delete_cache_item()
    elif user_choice == "5":
        delete_specific_cache_item()

