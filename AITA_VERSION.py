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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CLIENT_ID = 'XXXXX'
CLIENT_SECRET = 'XXXXX'
USER_AGENT = 'python:word-tracker-bot:v1.0 (by /u/oceanradioguy)'
REFRESH_TOKEN = 'XXXXX'
POST_USERNAME = 'XXXXX'
POST_PASSWORD = 'XXXXX'

IGNORED_WORDS = {} # Entire stop word list entered here

GIF_PATTERN = re.compile(r'\.gif(v)?|v\.redd\.it|gfycat|imgur\.com\/\w{5,7}', re.IGNORECASE)
EMOJI_PATTERN = re.compile(r':\w+:')

subreddit_to_pull_data_from = 'amitheasshole'
subreddit_to_post_data_to = 'dataisbeautiful'
number_of_posts_to_analyze = 200
depth_of_comments = None
how_many_bars_on_chart = 10
EXCLUDED_USERS = {'AutoModerator', 'Judgement_Bot_AITA'}

def get_access_token():
    auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    data = {'grant_type': 'refresh_token', 'refresh_token': REFRESH_TOKEN}
    headers = {'User-Agent': USER_AGENT}
    response = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to get access token, response: {response.text}")
    return response.json()['access_token']

def connect_to_reddit():
    access_token = get_access_token()
    return praw.Reddit(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, user_agent=USER_AGENT, access_token=access_token, username=POST_USERNAME, password=POST_PASSWORD)

def get_top_comments(reddit, num_posts):
    comments_by_judgment = {'asshole': [], 'not_asshole': []}
    judgment_pattern = re.compile(r'\b(?:NTA|YTA|NAH|ESH)\b', re.IGNORECASE)
    for submission in reddit.subreddit(subreddit_to_pull_data_from).hot(limit=num_posts):
        submission.comments.replace_more(limit=depth_of_comments)
        for comment in submission.comments.list():
            if comment.author and comment.author.name not in EXCLUDED_USERS:
                if not (GIF_PATTERN.search(comment.body) or EMOJI_PATTERN.search(comment.body)):
                    match = judgment_pattern.search(comment.body)
                    if not match:
                        continue
                    judgment = match.group(0).upper()
                    logging.info(f"Judgment found: {judgment}")
                    judgment_category = 'asshole' if judgment == 'YTA' else 'not_asshole' if judgment == 'NTA' else None
                    if judgment_category:
                        comments_by_judgment[judgment_category].append(comment.body)
    logging.info(f"Number of comments in each category: {len(comments_by_judgment['asshole'])} (asshole), {len(comments_by_judgment['not_asshole'])} (not_asshole)")
    return comments_by_judgment

def count_phrases(comments):
    phrase_count = Counter()
    word_pattern = re.compile(r'\b\w+\b')

    for comment in comments:
        words = word_pattern.findall(comment.lower())
        phrases = zip(words[:-1], words[1:])

        for phrase in phrases:
            if phrase[0] not in IGNORED_WORDS and phrase[1] not in IGNORED_WORDS:
                phrase_count[phrase] += 1

    return phrase_count

def plot_top_phrases(phrase_counts, num_phrases, labels):
    fig, axes = plt.subplots(2, 1, figsize=(10, 10))

    for i, (phrase_count, label) in enumerate(zip(phrase_counts, labels)):
        most_common = phrase_count.most_common(num_phrases)
        phrases, counts = zip(*most_common)
        phrases = [' '.join(phrase) for phrase in phrases]
        phrases = pd.Series(phrases)
        counts = pd.Series(counts)
        sns.set(style="whitegrid")
        sns.barplot(x=phrases, y=counts, palette="coolwarm", ax=axes[i])
        axes[i].set_xlabel('Phrases')
        axes[i].set_ylabel('# of times phrase appeared in comments')
        axes[i].set_title(f'Top 2-word Phrases for {label}')
        for idx, p in enumerate(axes[i].patches):
            height = p.get_height()
            axes[i].text(p.get_x() + p.get_width() / 2, height + 0.5, counts[idx], ha="center", va="bottom")
        axes[i].tick_params(axis='x', rotation=45)

    plt.tight_layout(h_pad=5)
    plt.savefig('top_phrases_combined.png')
    plt.close()

def main():
    try:
        reddit = connect_to_reddit()
        logging.info("Connected to Reddit")
        num_posts = number_of_posts_to_analyze
        subreddit_name = subreddit_to_pull_data_from
        subreddit_to_post_to = subreddit_to_post_data_to
        logging.info("Fetching top comments")
        comments_by_judgment = get_top_comments(reddit, num_posts)
        logging.info("Top comments fetched")

        phrase_counts = []
        labels = []

        for judgment_category, comments in comments_by_judgment.items():
            logging.info(f"Processing {judgment_category}")
            phrase_count = count_phrases(comments)
            if not phrase_count:
                logging.info(f"No phrases found for {judgment_category}")
                continue
            phrase_counts.append(phrase_count)
            labels.append(judgment_category.upper())

        plot_top_phrases(phrase_counts, how_many_bars_on_chart, labels)

        image_path = 'top_phrases_combined.png'
        analyzed_comments_count = sum(len(comments) for comments in comments_by_judgment.values())
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        title = (f"I've Analyzed {analyzed_comments_count} comments from the current top {num_posts} hot posts "
                 f"of r/{subreddit_name}. "
                 f"Here are the most frequently used 2-word phrases by NTA or YTA category [OC]")
        reddit.subreddit(subreddit_to_post_to).submit_image(title, image_path)
    except Exception as e:
        logging.exception("An error occurred:")

if __name__ == '__main__':
    main()
