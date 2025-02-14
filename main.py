import requests
from bs4 import BeautifulSoup
from atproto import Client
import time
import random
from flask import Flask, render_template
import threading
from time import sleep
import datetime
import pytz
import json
import hashlib

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

def run_server():
    try:
        app.run(host='0.0.0.0', port=8000)
    except OSError as e:
        print(f"Could not start server: {e}")
        exit(1)

server_thread = threading.Thread(target=run_server)
server_thread.start()

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

POSTED_TWEETS_FILE = "posted_tweets.json"

def load_posted_tweets():
    try:
        with open(POSTED_TWEETS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_posted_tweets(tweet_ids):
    with open(POSTED_TWEETS_FILE, 'w') as f:
        json.dump(tweet_ids, f)

posted_tweets = load_posted_tweets()

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


if not verify_bluesky_credentials():
    print("Invalid Bluesky credentials. Please check BSKY_HANDLE and BSKY_APP_PASSWORD")
    exit(1)

brasilia_tz = pytz.timezone('America/Sao_Paulo')
bsky_client = None # Initialize bsky_client outside the loop

while True:
    now = datetime.datetime.now(brasilia_tz)
    hour = now.hour

    if 8 <= hour < 18:
        if not fast_interval:
            sleep_interval = 15 * 60
        else:
            sleep_interval = 30

        sleep(sleep_interval)

        tweet_data = get_latest_tweet()
        if tweet_data:
            tweet, image_url = tweet_data

            import hashlib
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

            if fast_interval and now >= fast_interval_end_time:
                fast_interval = False
                fast_interval_end_time = None
                print("Switching back to normal interval (15min).")

    else:
        sleep(60 * 60)
        print("Outside of operating hours (8 AM - 6 PM Brasília). Sleeping for 1 hour.")

@app.route('/posted_tweets')
def show_posted_tweets():
    return render_template('posted_tweets.html', tweets=posted_tweets)

# Create templates/posted_tweets.html:
"""
<!DOCTYPE html>
<html>
<head>
    <title>Posted Tweets</title>
</head>
<body>
    <h1>Posted Tweets</h1>
    <ul>
        {% for tweet_id in tweets %}
            <li>{{ tweet_id }}</li>
        {% endfor %}
    </ul>
</body>
</html>
"""
