import requests
from bs4 import BeautifulSoup
from atproto import Client
import time
import random
from flask import Flask, render_template, jsonify
import threading
from time import sleep
import datetime
import pytz
import json
import hashlib

app = Flask(__name__)

# Settings (X account, Nitter instances, headers, Bluesky credentials)
X_ACCOUNT = "cinemafundaj"
NITTER_INSTANCES = [
    f"https://nitter.net/{X_ACCOUNT}/with_replies",
    f"https://nitter.cz/{X_ACCOUNT}/with_replies",
    f"https://nitter.unixfox.eu/{X_ACCOUNT}/with_replies",
    f"https://xcancel.com/{X_ACCOUNT}/with_replies",
    f"https://nitter.space/{X_ACCOUNT}/with_replies",
    f"https://lightbrd.com/{X_ACCOUNT}/with_replies",
    f"https://nitter.privacydev.net/{X_ACCOUNT}/with_replies",
    f"https://nitter.lunar.icu/{X_ACCOUNT}/with_replies",
    f"https://nitter.moomoo.me/{X_ACCOUNT}/with_replies",
]
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
    shuffled_instances = NITTER_INSTANCES[:]
    random.shuffle(shuffled_instances)

    for instance_url_base in shuffled_instances:
        try:
            print(f"Trying Nitter instance: {instance_url_base}")
            response = requests.get(instance_url_base, headers=HEADERS, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            tweets = soup.find_all('div', class_='tweet-content media-body')

            if tweets:
                tweet = tweets[0]
                tweet_text = tweet.text.strip()
                print(f"Raw tweet content: {tweet_text}")

                image_element = tweet.find('a', class_='tweet-media-link')
                image_url = None

                if image_element:
                    image_url = image_element['href']
                elif tweet.find('img', class_='tweet-media-image'):
                    image_url = tweet.find('img', class_='tweet-media-image')['src']

                if image_url:
                    if not image_url.startswith("http"):
                        domain = instance_url_base.split("/")[2]
                        image_url = f"https://{domain}{image_url}"
                    print(f"Found Image URL: {image_url}")

                return tweet_text, image_url

            print("No tweets found on this instance.")

        except requests.exceptions.RequestException as e:
            print(f"Error connecting to {instance_url_base}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    print("All Nitter instances failed")
    return None, None

# Function to verify Bluesky credentials
def verify_bluesky_credentials():
    global bsky_client
    try:
        bsky_client = Client()
        bsky_client.login(BSKY_HANDLE, BSKY_APP_PASSWORD)
        print("Bluesky credentials verified successfully!")
        return True
    except Exception as e:
        print("Error verifying Bluesky credentials:", str(e))
        return False

# Function to post to Bluesky
def post_to_bluesky(text, image_url=None, tweet_id=None):
    global bsky_client, posted_tweets
    if bsky_client:
        try:
            if image_url:
                text_with_image_link = f"{text}\n\nImage: {image_url}"
                bsky_client.send_post(text_with_image_link)
                print("Posted to Bluesky with image link:", text_with_image_link)
            else:
                bsky_client.send_post(text)
                print("Posted to Bluesky:", text)

            if tweet_id:
                posted_tweets.append(tweet_id)
                save_posted_tweets(posted_tweets)
                print(f"Saved tweet ID: {tweet_id}")

        except Exception as e:
            print(f"Error posting to Bluesky: {e}")
    else:
        print("Bluesky client not initialized.")

# Initialize Bluesky client
bsky_client = None

# Timezone setup
brasilia_tz = pytz.timezone('America/Sao_Paulo')

# Global variables for fast interval
fast_interval = False
fast_interval_end_time = None
last_tweet_check_time = None  # Track the time of the last tweet check
last_tweet = ""
last_image_url = ""

# Main loop function (runs in a separate thread)
def main_loop():
    global fast_interval, fast_interval_end_time, last_tweet_check_time, last_tweet, last_image_url

    while True:
        now = datetime.datetime.now(brasilia_tz)
        hour = now.hour

        if 8 <= hour < 18:  # Check if it's between 8 AM and 6 PM Brasília time
            if not fast_interval:
                sleep_interval = 15 * 60  # 15 minutes in seconds
            else:
                sleep_interval = 30  # 30 seconds

            sleep(sleep_interval)
            last_tweet_check_time = datetime.datetime.now(brasilia_tz)  # Update last tweet check time

            tweet_data = get_latest_tweet()
            if tweet_data:
                tweet, image_url = tweet_data
                tweet_id = hashlib.md5(tweet.encode('utf-8')).hexdigest()

                if tweet and (tweet != last_tweet or image_url != last_image_url) and tweet_id not in posted_tweets:
                    post_to_bluesky(tweet, image_url, tweet_id)
                    print("Latest tweet fetched:", tweet, image_url)
                    last_tweet = tweet
                    last_image_url = image_url

                    if not fast_interval:
                        fast_interval = True
                        fast_interval_end_time = now + datetime.timedelta(minutes=50)
                        print("Switching to fast interval (30s) for 50 minutes.")

                elif tweet_id in posted_tweets:
                    print("Duplicate Tweet Found. Skipping.")
                else:
                    print("No new unique tweets found.")

                if fast_interval and now >= fast_interval_end_time:  # Check if 50 minutes have passed
                    fast_interval = False
                    fast_interval_end_time = None
                    print("Switching back to normal interval (15min).")

            elif last_tweet_check_time and (now - last_tweet_check_time) >= datetime.timedelta(minutes=12) and fast_interval:  # Check if 12 minutes have passed without new tweets
                fast_interval = False
                fast_interval_end_time = None
                print("No new tweets for 12 minutes. Switching back to normal interval (15min).")

        else:  # Outside operating hours
            sleep(60 * 60)
            print("Outside of operating hours (8 AM - 6 PM Brasília). Sleeping for 1 hour.")

# Flask route to display posted tweets as JSON
@app.route
