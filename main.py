import requests
from bs4 import BeautifulSoup
from atproto import Client
import time
import random
from flask import Flask, render_template, jsonify  # Import jsonify
import threading
from time import sleep
import datetime
import pytz
import json
import hashlib

# Initialize Flask app
app = Flask(__name__)

# Route for the main page (currently just says "Bot is running!")
@app.route('/')
def home():
    return "Bot is running!"

# Function to run the Flask development server in a separate thread
def run_server():
    try:
        app.run(host='0.0.0.0', port=8000)  # Run on all interfaces, port 8000
    except OSError as e:
        print(f"Could not start server: {e}")
        exit(1)

# Start the Flask server in a separate thread
server_thread = threading.Thread(target=run_server)
server_thread.daemon = True  # Allow the main thread to exit even if the server is running
server_thread.start()

# Settings (X account, Nitter instances, headers, Bluesky credentials)
X_ACCOUNT = "cinemafundaj"
NITTER_INSTANCES = [
    # ... (Your Nitter instances)
]
HEADERS = {
    # ... (Your headers)
}
BSKY_HANDLE = "botcinemafundaj.bsky.social"
BSKY_APP_PASSWORD = "rhhu-xrcm-zegf-ry3i"

# File to store posted tweet IDs
POSTED_TWEETS_FILE = "posted_tweets.json"

# Function to load posted tweet IDs from the JSON file
def load_posted_tweets():
    try:
        with open(POSTED_TWEETS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# Function to save posted tweet IDs to the JSON file
def save_posted_tweets(tweet_ids):
    with open(POSTED_TWEETS_FILE, 'w') as f:
        json.dump(tweet_ids, f)

# Load posted tweets on startup
posted_tweets = load_posted_tweets()

# Function to get the latest tweet from Nitter
def get_latest_tweet():
    # ... (Your Nitter scraping logic - same as before)

# Function to verify Bluesky credentials
def verify_bluesky_credentials():
    # ... (Your Bluesky verification logic - same as before)

# Function to post to Bluesky
def post_to_bluesky(text, image_url=None, tweet_id=None):
    global bsky_client, posted_tweets  # Access global variables
    if bsky_client:
        try:
            # ... (Your Bluesky posting logic - same as before)

            if tweet_id:  # Save tweet ID after successful post
                posted_tweets.append(tweet_id)
                save_posted_tweets(posted_tweets)
                print(f"Saved tweet ID: {tweet_id}")

        except Exception as e:
            print(f"Error posting to Bluesky: {e}")
    else:
        print("Bluesky client not initialized.")

# Initialize Bluesky client outside the loop
bsky_client = None

# Timezone setup
brasilia_tz = pytz.timezone('America/Sao_Paulo')

# Global variables for fast interval
fast_interval = False  # Flag to indicate fast interval
fast_interval_end_time = None  # Time when fast interval should end

# Main loop function (runs in a separate thread)
def main_loop():
    global fast_interval, fast_interval_end_time  # Access global variables
    last_tweet = ""  # Keep track of the last posted tweet
    last_image_url = "" # keep track of the last image URL
    while True:
        now = datetime.datetime.now(brasilia_tz)
        hour = now.hour

        if 8 <= hour < 18:  # Check if it's between 8 AM and 6 PM Brasília time
            if not fast_interval:
                sleep_interval = 15 * 60  # 15 minutes in seconds
            else:
                sleep_interval = 30  # 30 seconds

            sleep(sleep_interval)

            tweet_data = get_latest_tweet()
            if tweet_data:
                tweet, image_url = tweet_data

                tweet_id = hashlib.md5(tweet.encode('utf-8')).hexdigest()  # Generate tweet ID

                if tweet and (tweet != last_tweet or image_url != last_image_url) and tweet_id not in posted_tweets:  # Check for new tweet and not a duplicate
                    post_to_bluesky(tweet, image_url, tweet_id)  # Post to Bluesky with tweet ID
                    print("Latest tweet fetched:", tweet, image_url)
                    last_tweet = tweet
                    last_image_url = image_url

                    if not fast_interval:  # Start fast interval if a new tweet is found
                        fast_interval = True
                        fast_interval_end_time = now + datetime.timedelta(minutes=50)
                        print("Switching to fast interval (30s) for 50 minutes.")

                elif tweet_id in posted_tweets:  # Check if the tweet is a duplicate
                    print("Duplicate Tweet Found. Skipping.")
                else:
                    print("No new unique tweets found.") # Helpful debug print

                if fast_interval and now >= fast_interval_end_time:  # End fast interval
                    fast_interval = False
                    fast_interval_end_time = None
                    print("Switching back to normal interval (15min).")

        else:  # Outside operating hours
            sleep(60 * 60)  # Sleep for 1 hour
            print("Outside of operating hours (8 AM - 6 PM Brasília). Sleeping for 1 hour.")


# Flask route to display posted tweets as JSON
@app.route('/posted_tweets')
def show_posted_tweets():
    return jsonify(posted_tweets)  # Return JSON data

# Start the main loop in a separate thread
main_thread = threading.Thread(target=main_loop)
main_thread.daemon = True # Allow the main thread to exit even if the bot is running
main_thread.start()

# This block ensures that the following code only runs when the script is executed directly
if __name__ == '__main__':
    if not verify_bluesky_credentials():  # Verify Bluesky credentials before starting
        print("Invalid Bluesky credentials. Please check BSKY_HANDLE and BSKY_APP_PASSWORD")
        exit(1)
    run_server()  # Start the Flask server
