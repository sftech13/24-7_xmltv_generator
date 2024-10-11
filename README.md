# XMLTV EPG Generator

This repository contains a Python script for generating XMLTV format Electronic Program Guides (EPGs) based on data fetched from the TMDB API. The script manages caching for data requests, stores configurations, and creates XMLTV files for TV shows and movies.

## Table of Contents
1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [Usage](#usage)
6. [Logging](#logging)
7. [Database](#database)
8. [Cache Management](#cache-management)
9. [EPG Generation](#epg-generation)
10. [Error Handling](#error-handling)
11. [License](#license)

---

## Features
- Fetches TV and movie data from TMDB API
- Generates XMLTV EPG files for TV shows and movies
- Maintains a cache for previously fetched data
- Supports logging for actions and errors
- Offers interactive and non-interactive modes

## Requirements
- Python 3.x
- Required Libraries: `requests`, `json`, `sqlite3`, `xml.etree.ElementTree`

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/sftech13/xmltv-epg-generator.git
   cd xmltv-epg-generator
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **API Key**: Store your TMDB API key in `api_info.json` within the script directory:
   ```json
   {
       "tmdb_api_key": "YOUR_TMDB_API_KEY"
   }
   ```
2. **Log File**: Update the log file path as needed in `xmltv.py`:
   ```python
   LOG_FILE_PATH = '/24-7_xmltv_generator.log'
   ```

## Usage

Run the script using the following command:
```bash
python xmltv.py
```

### Command Options
- **1** - Sync and generate EPG for TV shows
- **2** - Sync and generate EPG for movies
- **3** - Sync and generate EPG for both TV shows and movies (default)
- **4** - Delete the cache for all items
- **5** - Delete a specific cache item

## Logging
- Logs are stored in a file specified by `LOG_FILE_PATH` and record script actions, data fetches, errors, and cache updates.

## Database
- Cached data is stored in `cache.db`, which is automatically created in the script directory.
- Cache entries have a 14-day expiration by default.

## Cache Management
- **save_cache**: Saves data with a name, type, and timestamp.
- **load_cache**: Retrieves data if it exists and hasn't expired.
- **delete_cache_item**: Removes data from the cache.
- **list_cache_items**: Lists cached items by type.

## EPG Generation
- The `create_epg` function generates an XMLTV file for specified shows or movies.
- XMLTV files are saved with owner and permissions updated as per the script’s configuration.

## Error Handling
- Errors in API requests and file operations are logged, and the script provides default selections for user prompts in non-interactive environments.

## License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
