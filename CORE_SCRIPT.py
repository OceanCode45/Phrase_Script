import praw
import os
import re
from collections import Counter
import matplotlib.pyplot as plt
import logging
import requests
import datetime
import seaborn as sns
import numpy as np
import pandas as pd

# Logging configuration
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Reddit App credentials
CLIENT_ID = 'XXXX'
CLIENT_SECRET = 'XXXX'
USER_AGENT = 'python:word-tracker-bot:v1.0 (by /u/oceanradioguy)'
REFRESH_TOKEN = 'XXXX'
POST_USERNAME = 'XXXX'
POST_PASSWORD = 'XXXX'

# Ignored Stop Words
IGNORED_WORDS = {} # Entire stop word list enetered here


# Configuration variables
GIF_PATTERN = re.compile(r'\.gif(v)?|v\.redd\.it|gfycat|imgur\.com\/\w{5,7}', re.IGNORECASE)
EMOJI_PATTERN = re.compile(r':\w+:')

subreddit_to_pull_data_from = 'conservative'
subreddit_to_post_data_to = 'dataisbeautiful'
number_of_posts_to_analyze = 100
depth_of_comments = None
how_many_bars_on_chart = 10
EXCLUDED_USERS = {'AutoModerator'}

# Function to get the access token
def get_access_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': REFRESH_TOKEN
    }
    headers = {'User-Agent': USER_AGENT}

    response = requests.post('https://www.reddit.com/api/v1/access_token',
                             auth=auth,
                             data=data,
                             headers=headers)

    if response.status_code != 200:
        raise Exception(f"Failed to get access token, response: {response.text}")

    return response.json()['access_token']

# Function to connect to Reddit
def connect_to_reddit():
    access_token = get_access_token()
    return praw.Reddit(client_id=CLIENT_ID,
                       client_secret=CLIENT_SECRET,
                       user_agent=USER_AGENT,
                       access_token=access_token,
                       username=POST_USERNAME,
                       password=POST_PASSWORD)

# Function to get top comments from the specified subreddit
def get_top_comments(reddit, num_posts):
    comments = []
    for submission in reddit.subreddit(subreddit_to_pull_data_from).hot(limit=num_posts):
        submission.comments.replace_more(limit=depth_of_comments)
        for comment in submission.comments.list():
            if comment.author and comment.author.name not in EXCLUDED_USERS:
                if not (GIF_PATTERN.search(comment.body) or EMOJI_PATTERN.search(comment.body)):
                    comments.append(comment.body)
                    print(comment)
    return comments

# Function to count phrases in the comments
def count_phrases(comments):
    phrase_count = Counter()
    word_pattern = re.compile(r'\b\w+\b')

    for comment in comments:
        words = word_pattern.findall(comment.lower())
        phrases = zip(words[:-1], words[1:])

        for phrase in phrases:
            if phrase[0] not in IGNORED_WORDS and phrase[1] not in IGNORED_WORDS:
                print(phrase)
                phrase_count[phrase] += 1

    return phrase_count

# Function to plot the top phrases
def plot_top_phrases(phrase_count, num_phrases):
    most_common = phrase_count.most_common(num_phrases)
    phrases, counts = zip(*most_common)
    phrases = [' '.join(phrase) for phrase in phrases]

    # Convert the input data to Pandas Series
    phrases = pd.Series(phrases)
    counts = pd.Series(counts)

    plt.figure(figsize=(10, 5))  # Adjust the figure size

    # Use Seaborn to create the bar chart
    sns.set(style="whitegrid")
    sns.barplot(x=phrases, y=counts, palette="coolwarm")

    plt.xlabel('Phrases')
    plt.ylabel('# of times phrase appeared in comments')
    plt.title('Top 2-word Phrases')

    # Display the frequency values above each bar
    ax = plt.gca()
    for idx, p in enumerate(ax.patches):
        height = p.get_height()
        ax.text(p.get_x() + p.get_width() / 2, height + 0.5, counts[idx], ha="center", va="bottom")

    plt.xticks(rotation=45)  # Rotate the x-axis labels
    plt.tight_layout()  # Adjust the layout to fit the labels properly

    plt.savefig('top_phrases.png')
    plt.close()

# Main function
def main():
    try:
        reddit = connect_to_reddit()
        print("connected")
        num_posts = number_of_posts_to_analyze
        subreddit_name = subreddit_to_pull_data_from
        subreddit_to_post_to = subreddit_to_post_data_to
        comments = get_top_comments(reddit, num_posts)
        phrase_count = count_phrases(comments)
        plot_top_phrases(phrase_count, how_many_bars_on_chart)

        image_path = 'top_phrases.png'
        analyzed_comments_count = len(comments)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = f"I've Analyzed {analyzed_comments_count} comments from the current top {num_posts} hot posts of r/{subreddit_name}. Here are the most frequently used 2-word phrases [OC]"
        reddit.subreddit(subreddit_to_post_to).submit_image(title, image_path)
    except Exception as e:
        logging.exception("An error occurred:")

if __name__ == '__main__':
    main()
