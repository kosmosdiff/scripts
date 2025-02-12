import os
import requests
import shutil
import time
import re
import logging
import json

# Configuration
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "apis": ["jikan", "anilist", "mangadex", "kitsu"],
    "timeout": 45,
    "rate_limit_delay": 1,  # Delay in seconds between API requests
    "max_retries": 3,
    "log_file": "manga_organizer.log",
    "library_directory": "E:\\TOTOdeF\\books organized\\002unned\\OTHER-ORGANIZE",
    "target_directory": "E:\\TOTOdeF\\books organized\\002unned"
}

# Load or create config
def load_or_create_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                logging.info("Config file loaded successfully.")
        except json.JSONDecodeError:
            logging.error("Config file is empty or invalid. Creating a new one with default values.")
            config = DEFAULT_CONFIG
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
    else:
        logging.info("Config file not found. Creating a new one with default values.")
        config = DEFAULT_CONFIG
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)
    return config

config = load_or_create_config()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(config["log_file"]),
        logging.StreamHandler()
    ]
)

# Rate limiting implementation
last_api_call_time = 0

def rate_limited_call():
    global last_api_call_time
    elapsed = time.time() - last_api_call_time
    wait_time = config["rate_limit_delay"] - elapsed
    if wait_time > 0:
        time.sleep(wait_time)
    last_api_call_time = time.time()

# Jikan (MyAnimeList) API
def fetch_jikan_metadata(title):
    url = f"https://api.jikan.moe/v4/manga?q={title}"
    logging.info(f"Fetching metadata from Jikan for: {title}")
    for _ in range(config["max_retries"]):
        try:
            rate_limited_call()
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get('data'):
                return {"jikan": data['data'][0]}
        except Exception as e:
            logging.error(f"Error fetching metadata from Jikan: {e}")
            time.sleep(config["rate_limit_delay"])
    return None

# AniList API
def fetch_anilist_metadata(title):
    query = """
    query ($search: String) {
        Media(search: $search, type: MANGA) {
            title {
                romaji
                english
            }
            genres
            description
            status
            chapters
            volumes
            coverImage {
                large
            }
        }
    }
    """
    variables = {"search": title}
    url = "https://graphql.anilist.co"
    logging.info(f"Fetching metadata from AniList for: {title}")
    for _ in range(config["max_retries"]):
        try:
            rate_limited_call()
            response = requests.post(url, json={"query": query, "variables": variables})
            response.raise_for_status()
            data = response.json()
            if data.get('data', {}).get('Media'):
                return {"anilist": data['data']['Media']}
            else:
                logging.error(f"No data found for {title} in AniList response: {data}")
        except requests.exceptions.HTTPError as e:
            logging.error(f"HTTP Error fetching metadata from AniList: {e}")
            logging.error(f"Response content: {response.content}")
            time.sleep(config["rate_limit_delay"])
        except Exception as e:
            logging.error(f"Error fetching metadata from AniList: {e}")
            time.sleep(config["rate_limit_delay"])
    return None

# MangaDex API
def fetch_mangadex_metadata(title):
    url = f"https://api.mangadex.org/manga?title={title}"
    logging.info(f"Fetching metadata from MangaDex for: {title}")
    for _ in range(config["max_retries"]):
        try:
            rate_limited_call()
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get('data'):
                return {"mangadex": data['data'][0]}
        except Exception as e:
            logging.error(f"Error fetching metadata from MangaDex: {e}")
            time.sleep(config["rate_limit_delay"])
    return None

# Kitsu API
def fetch_kitsu_metadata(title):
    url = f"https://kitsu.io/api/edge/manga?filter[text]={title}"
    logging.info(f"Fetching metadata from Kitsu for: {title}")
    for _ in range(config["max_retries"]):
        try:
            rate_limited_call()
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get('data'):
                return {"kitsu": data['data'][0]}
        except Exception as e:
            logging.error(f"Error fetching metadata from Kitsu: {e}")
            time.sleep(config["rate_limit_delay"])
    return None

def fetch_manga_metadata(title):
    metadata = {}
    for api_name in config["apis"]:
        if api_name == "jikan":
            result = fetch_jikan_metadata(title)
            if result:
                metadata.update(result)
        elif api_name == "anilist":
            result = fetch_anilist_metadata(title)
            if result:
                metadata.update(result)
        elif api_name == "mangadex":
            result = fetch_mangadex_metadata(title)
            if result:
                metadata.update(result)
        elif api_name == "kitsu":
            result = fetch_kitsu_metadata(title)
            if result:
                metadata.update(result)
    return metadata if metadata else None

def save_metadata(metadata, folder):
    metadata_file = os.path.join(folder, "metadata.json")
    with open(metadata_file, "w") as f:
        json.dump(metadata, f, indent=4)
    logging.info(f"Saved metadata to {metadata_file}")

def load_metadata(folder):
    metadata_file = os.path.join(folder, "metadata.json")
    if os.path.exists(metadata_file):
        with open(metadata_file, "r") as f:
            return json.load(f)
    return None

def clean_name(name):
    cleaned_name = re.sub(r"\([^)]*\)", "", name)
    cleaned_name = re.sub(r"\{[^}]*\}", "", cleaned_name)
    cleaned_name = re.sub(r"\[[^]]*\]", "", cleaned_name)
    cleaned_name = cleaned_name.strip(" -_")
    logging.info(f"Cleaned name: {cleaned_name}")
    return cleaned_name

def format_title(title):
    formatted_title = re.sub(r"(?<!^)([A-Z])", r" \1", title)
    formatted_title = re.sub(r"\s+", " ", formatted_title)
    logging.info(f"Formatted title: {formatted_title}")
    return formatted_title

def extract_base_title(filename):
    base_title = re.sub(r"[-_ ]*(v|vol|volume|ch|chapter)[0-9]*", "", filename, flags=re.IGNORECASE)
    base_title = re.sub(r"[-_ ]*[0-9]*", "", base_title)
    base_title = re.sub(r"\.(cbz|epub|zip)$", "", base_title, flags=re.IGNORECASE)
    base_title = base_title.strip(" -_")
    base_title = format_title(base_title)
    logging.info(f"Extracted base title from '{filename}': {base_title}")
    return base_title

def rename_files_and_folders(directory):
    logging.info(f"Renaming files and folders in: {directory}")
    for root, dirs, files in os.walk(directory, topdown=False):
        for filename in files:
            if filename.endswith(".cbz") or filename.endswith(".epub") or filename.endswith(".zip"):
                file_path = os.path.join(root, filename)
                new_filename = clean_name(filename)
                new_filename = format_title(new_filename)
                new_file_path = os.path.join(root, new_filename)
                if file_path != new_file_path:
                    try:
                        shutil.move(file_path, new_file_path)
                        logging.info(f"Renamed file: {filename} -> {new_filename}")
                    except Exception as e:
                        logging.error(f"Error renaming file {filename}: {e}")

        for dirname in dirs:
            dir_path = os.path.join(root, dirname)
            new_dirname = clean_name(dirname)
            new_dirname = format_title(new_dirname)
            new_dir_path = os.path.join(root, new_dirname)
            if dir_path != new_dir_path:
                try:
                    shutil.move(dir_path, new_dir_path)
                    logging.info(f"Renamed folder: {dirname} -> {new_dirname}")
                except Exception as e:
                    logging.error(f"Error renaming folder {dirname}: {e}")

def organize_folder(directory, target_directory):
    logging.info(f"Organizing folder: {directory}")
    manga_groups = {}

    # Check if the directory has no subfolders
    has_subfolders = any(os.path.isdir(os.path.join(directory, d)) for d in os.listdir(directory))

    if not has_subfolders:
        # Treat the folder as a single entity
        folder_name = os.path.basename(directory)
        base_title = extract_base_title(folder_name)
        logging.info(f"Processing folder with no subfolders: {folder_name}")

        # Check if metadata already exists
        target_folder = os.path.join(target_directory, "Unorganized", base_title)
        metadata = load_metadata(target_folder)
        if not metadata:
            metadata = fetch_manga_metadata(base_title)

        if metadata:
            logging.info(f"Metadata found: {metadata}")
            genre = metadata.get("anilist", {}).get("genres", ["Unknown"])[0]
            logging.info(f"Genre: {genre}")
            target_folder = os.path.join(target_directory, genre, base_title)
            os.makedirs(target_folder, exist_ok=True)
            save_metadata(metadata, target_folder)
        else:
            logging.info(f"No metadata found for {base_title} after timeout.")
            target_folder = os.path.join(target_directory, "Unorganized", base_title)
            os.makedirs(target_folder, exist_ok=True)

        # Move all files in the folder to the target folder
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) and (filename.endswith(".cbz") or filename.endswith(".epub") or filename.endswith(".zip") or filename.lower().endswith((".jpg", ".jpeg", ".png"))):
                try:
                    shutil.move(file_path, os.path.join(target_folder, filename))
                    logging.info(f"Moved {filename} to {target_folder}")
                except Exception as e:
                    logging.error(f"Error moving file {filename}: {e}")
        return  # Exit the function after processing the folder

    # If the directory has subfolders, process files as before
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".cbz") or filename.endswith(".epub") or filename.endswith(".zip"):
                logging.info(f"\nProcessing file: {filename}")
                file_path = os.path.join(root, filename)
                base_title = extract_base_title(filename)

                if base_title not in manga_groups:
                    manga_groups[base_title] = []
                manga_groups[base_title].append((file_path, filename))

    for base_title, files in manga_groups.items():
        logging.info(f"\nOrganizing files for: {base_title}")
        target_folder = os.path.join(target_directory, "Unorganized", base_title)
        metadata = load_metadata(target_folder)
        if not metadata:
            metadata = fetch_manga_metadata(base_title)

        if metadata:
            logging.info(f"Metadata found: {metadata}")
            genre = metadata.get("anilist", {}).get("genres", ["Unknown"])[0]
            logging.info(f"Genre: {genre}")
            target_folder = os.path.join(target_directory, genre, base_title)
            os.makedirs(target_folder, exist_ok=True)
            save_metadata(metadata, target_folder)
        else:
            logging.info(f"No metadata found for {base_title} after timeout.")
            target_folder = os.path.join(target_directory, "Unorganized", base_title)
            os.makedirs(target_folder, exist_ok=True)

        for file_path, filename in files:
            try:
                shutil.move(file_path, os.path.join(target_folder, filename))
                logging.info(f"Moved {filename} to {target_folder}")
            except Exception as e:
                logging.error(f"Error moving file {filename}: {e}")

    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".cbz") or filename.endswith(".epub") or filename.endswith(".zip"):
                file_path = os.path.join(root, filename)
                base_title = extract_base_title(filename)

                if base_title not in manga_groups:
                    logging.info(f"\nOrganizing lone file: {filename}")
                    target_folder = os.path.join(target_directory, "Unorganized", base_title)
                    metadata = load_metadata(target_folder)
                    if not metadata:
                        metadata = fetch_manga_metadata(base_title)

                    if metadata:
                        logging.info(f"Metadata found: {metadata}")
                        genre = metadata.get("anilist", {}).get("genres", ["Unknown"])[0]
                        logging.info(f"Genre: {genre}")
                        target_folder = os.path.join(target_directory, genre, base_title)
                        os.makedirs(target_folder, exist_ok=True)
                        save_metadata(metadata, target_folder)
                    else:
                        logging.info(f"No metadata found for {base_title} after timeout.")
                        target_folder = os.path.join(target_directory, "Unorganized", base_title)
                        os.makedirs(target_folder, exist_ok=True)

                    try:
                        shutil.move(file_path, os.path.join(target_folder, filename))
                        logging.info(f"Moved {filename} to {target_folder}")
                    except Exception as e:
                        logging.error(f"Error moving file {filename}: {e}")

def delete_empty_folders(directory):
    logging.info(f"Deleting empty folders in: {directory}")
    for root, dirs, files in os.walk(directory, topdown=False):
        for dirname in dirs:
            dir_path = os.path.join(root, dirname)
            try:
                if not os.listdir(dir_path):  # Check if the folder is empty
                    os.rmdir(dir_path)
                    logging.info(f"Deleted empty folder: {dir_path}")
            except Exception as e:
                logging.error(f"Error deleting folder {dir_path}: {e}")

def organize_manga(directory, target_directory):
    logging.info(f"Scanning directory: {directory}")
    for root, dirs, files in os.walk(directory):
        if any(filename.endswith(".cbz") or filename.endswith(".epub") or filename.endswith(".zip") for filename in files):
            logging.info(f"\nOrganizing folder: {root}")
            organize_folder(root, target_directory)

def main():
    manga_directory = config["library_directory"]
    target_directory = config["target_directory"]

    while True:
        rename_files_and_folders(manga_directory)
        organize_manga(manga_directory, target_directory)
        delete_empty_folders(manga_directory)

        # Check for new folders
        new_folders = [d for d in os.listdir(manga_directory) if os.path.isdir(os.path.join(manga_directory, d))]
        if not new_folders:
            break

        logging.info("New folders found. Re-running organization...")

    logging.info("Manga organization complete!")

if __name__ == "__main__":
    main()