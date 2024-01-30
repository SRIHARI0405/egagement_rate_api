import asyncio
from flask import Flask, jsonify, Response
import json
import time
from textblob import TextBlob
from instagrapi import Client
from googletrans import Translator
import nltk
from langdetect import detect
from datetime import datetime, timedelta, timezone
from instagrapi.types import User

app = Flask(__name__)

nltk.download('punkt')
translator = Translator()

INSTAGRAM_USERNAME = 'loopstar154'
INSTAGRAM_PASSWORD = 'Starbuzz1234@'

proxy = "socks5://yoqytafd-6:2dng483b96qx@p.webshare.io:80"
cl = Client(proxy=proxy)

try:
    cl.load_settings('session-loop.json')
    cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
except Exception as e:
    print(f"Instagram login failed: {e}")

async def fetch_last_n_days_posts(username, n=18):
    user_id = cl.user_id_from_username(username)
    posts = cl.user_medias(user_id, amount=n)
    return posts

async def fetch_last_n_days_reels(username, n=18):
    user_id = cl.user_id_from_username(username)
    media = cl.user_medias(user_id, amount=n)
    reels = [item for item in media if item.media_type == 2][:n]
    return reels

async def get_average_likes_and_comments(posts):
    if not posts:
        return 0, 0, 0

    visible_likes = [post.like_count for post in posts if post.like_count is not None]
    total_likes = sum(visible_likes)
    average_likes = total_likes / len(visible_likes) if visible_likes else 0

    visible_comments = [post.comment_count for post in posts if post.comment_count is not None]
    total_comments = sum(visible_comments)
    average_comments = total_comments / len(visible_comments) if visible_comments else 0

    ratio_per_100_likes = (total_comments / total_likes) * 100 if total_likes != 0 else 0

    return average_likes, average_comments, ratio_per_100_likes

async def get_average_likes_and_comments_reels(reels):
    if not reels:
        return 0, 0, 0
    total_likes_reels = sum(reel.like_count for reel in reels if reel.like_count is not None)
    average_likes_reels = total_likes_reels / len(reels) if reels else 0

    total_comments_reel = sum(reel.comment_count for reel in reels if reel.comment_count is not None)
    average_comments_reel = total_comments_reel / len(reels) if reels else 0

    ratio_per_100_likes_reel = (total_comments_reel / total_likes_reels) * 100 if total_likes_reels != 0 else 0

    return average_likes_reels, average_comments_reel, ratio_per_100_likes_reel

async def categorize_likes_comments_ratio(ratio):
    if ratio == 0:
      return "No Post"
    if 0.01 <= ratio < 1:
        return "Good"
    elif 1 <= ratio < 5:
        return "Average"
    elif 0.001 <= ratio < 0.01:
        return "Average"
    elif ratio < 0.001:
        return "Low"
    else:
        return "Low"

def format_number(value, is_percentage=False):
    formatted_value = None
    if value is not None:
        if is_percentage:
            formatted_value = f"{round(value, 2)}%"
        elif value < 1000:
            formatted_value = str(round(value, 2))
        elif value < 1000000:
            formatted_value = f"{round(value / 1000, 2)}K"
        else:
            formatted_value = f"{round(value / 1000000, 2)}M"
    return formatted_value

def estimate_post_price(follower_count):
    if follower_count < 3000:
        estimated_cost_range = "₹250 - ₹500"    
    elif 3000 <= follower_count < 10000:
        estimated_cost_range = "₹500 - ₹1000"  
    elif 10000 <= follower_count < 50000:
        estimated_cost_range = "₹4000 - ₹10k"  
    elif 50000 <= follower_count < 200000:
        estimated_cost_range = "₹10k - ₹40k"  
    elif 200000 <= follower_count < 1000000:
        estimated_cost_range = "₹25k - ₹60k"  
    elif 1000000 <= follower_count:
        estimated_cost_range = "₹75k - ₹1.25L"  
    return estimated_cost_range



def estimate_reel_price(follower_count):

    if follower_count < 3000:
        estimated_cost_range = "₹500 - ₹1000"    
    elif 3000 <= follower_count < 10000:
        estimated_cost_range = "₹1000 - ₹2000"  
    elif 10000 <= follower_count < 50000:
        estimated_cost_range = "₹8000 - ₹20k"  
    elif 50000 <= follower_count < 200000:
        estimated_cost_range = "₹20k - ₹80k"  
    elif 200000 <= follower_count < 1000000:
        estimated_cost_range = "₹50k - ₹1.2L"  
    elif 1000000 <= follower_count:
        estimated_cost_range = "₹1.5L - ₹2.5L"  
    return estimated_cost_range    

def estimated_reach(posts):
  reach_values = [post.view_count for post in posts if post.view_count is not None and post.view_count > 0]
  estimated_reach_low = min(reach_values) if reach_values else 0
  estimated_reach_high = max(reach_values) if reach_values else 0
  formatted_estimated_reach_low = format_number(estimated_reach_low, is_percentage=False)
  formatted_estimated_reach_high = format_number(estimated_reach_high, is_percentage=False)
  estimated_reach_post = f"{formatted_estimated_reach_low} to {formatted_estimated_reach_high}"
  return estimated_reach_post


def categorize_sentiment(polarity):
    if polarity > 0.03:
        return 'Positive'
    elif polarity < -0.03:
        return 'Negative'
    else:
        return 'Neutral'

def translate_and_analyze_sentiment(caption_text, source_language):
    translation = translator.translate(caption_text, dest='en', src=source_language).text
    blob = TextBlob(translation)
    sentiment_polarity = blob.sentiment.polarity
    sentiment_category = categorize_sentiment(sentiment_polarity)
    return sentiment_category


def analyze_sentiment_and_words(posts):
    sentiment_counts = {'Positive': 0, 'Negative': 0, 'Neutral': 0}
    
    for post in posts:
        caption_text = post.caption_text if post.caption_text else ""
        try:
            language = detect(caption_text)
        except:
            language = 'en'  

        if language != 'en':
            sentiment_category = translate_and_analyze_sentiment(caption_text, language)
        else:
            blob = TextBlob(caption_text)
            sentiment_polarity = blob.sentiment.polarity
            sentiment_category = categorize_sentiment(sentiment_polarity)

        sentiment_counts[sentiment_category] += 1

    most_frequent_sentiment = max(sentiment_counts, key=sentiment_counts.get)
    return most_frequent_sentiment

async def calculate_engagement_rate(posts):
  if posts == 0:
    return 0
  visible_likes_comments = sum(post.like_count + post.comment_count for post in posts if post.like_count is not None and post.comment_count is not None)

  if visible_likes_comments == 0:
    return 0

  user_info = cl.user_info_by_username(posts[0].user.username)
  engagement_rate = (visible_likes_comments / len(posts)) / user_info.follower_count * 100
  return engagement_rate

async def calculate_engagement_rate_reels(username,reels):
  if reels == 0:
    return 0
  visible_likes_comments = sum(reel.like_count + reel.comment_count for reel in reels if reel.like_count is not None and reel.comment_count is not None)

  if visible_likes_comments == 0:
    return 0

  follower_count = cl.user_info_by_username(username).follower_count
  engagement_rate_reels = (visible_likes_comments / len(reels)) / follower_count * 100
  return engagement_rate_reels

async def calculate_average_posts_per_week(username, last_n_days):
    try:
        user_id = cl.user_id_from_username(username)
        posts = cl.user_medias(user_id, amount=last_n_days)

        if not posts:
            return 0
        oldest_post_timestamp = posts[-1].taken_at
        oldest_post_timestamp = int(oldest_post_timestamp.replace(tzinfo=timezone.utc).timestamp())
        weeks_since_oldest_post = (datetime.utcnow().timestamp() - oldest_post_timestamp) / (7 * 24 * 3600)

        average_posts_per_week = len(posts) / weeks_since_oldest_post

        return average_posts_per_week

    except Exception as e:
        print(f"An error occurred while calculating average posts per week: {e}")
        return 0

async def calculate_average_reels_per_week(username, last_n_days):
    try:
        user_id = cl.user_id_from_username(username)
        media = cl.user_medias(user_id, amount=last_n_days)
        reels = [item for item in media if item.media_type == 2][:last_n_days]

        if not reels:
            return 0

        oldest_reel_timestamp = reels[-1].taken_at
        oldest_reel_timestamp = int(oldest_reel_timestamp.replace(tzinfo=timezone.utc).timestamp())
        weeks_since_oldest_reel = (datetime.utcnow().timestamp() - oldest_reel_timestamp) / (7 * 24 * 3600)

        average_reels_per_week = len(reels) / weeks_since_oldest_reel

        return average_reels_per_week

    except Exception as e:
        print(f"An error occurred while calculating average reels per week: {e}")
        return 0

async def fetch_last_30_days_posts(username, n=50):
    try:
        user_id = cl.user_id_from_username(username)
        all_posts = cl.user_medias(user_id, amount=n)
        current_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        last_30_days_posts = [post for post in all_posts if (current_timestamp - post.taken_at) < timedelta(days=30)]
        return last_30_days_posts

    except Exception as e:
        print(f"An error occurred while fetching posts: {e}")
        return []

async def fetch_last_30_days_reels(username, n=50):
    try:
        user_id = cl.user_id_from_username(username)
        all_media = cl.user_medias(user_id, amount=n)
        current_timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)
        last_30_days_reels = [media for media in all_media if media.media_type == 2 and (current_timestamp - media.taken_at) < timedelta(days=30)]
        return last_30_days_reels
    except Exception as e:
        print(f"An error occurred while fetching reels: {e}")
        return []


async def calculate_consistency_score(username, last_n_days=50):
    try:
        user_id = cl.user_id_from_username(username)
        if user_id is None:
          return 0

        posts = await fetch_last_30_days_posts(username, n=last_n_days)

        if not posts:
            return 0

        total_posts = len(posts)
        total_time_period_days = 30
        consistency_score_post = (total_posts / total_time_period_days) * 0.9 
        return consistency_score_post

    except Exception as e:
        print(f"An error occurred while calculating consistency score: {e}")
        return 0

async def calculate_consistency_score_reels(username, last_n_days=50):
    try:
        user_id = cl.user_id_from_username(username)
        if user_id is None:
            return 0

        reels = await fetch_last_30_days_reels(username, n=last_n_days)

        if not reels:
            return 0

        total_reels = len(reels)
        total_time_period_days = 30
        consistency_score_reels = (total_reels / total_time_period_days) * 0.9 

        return consistency_score_reels

    except Exception as e:
        print(f"An error occurred while calculating consistency score for reels: {e}")
        return 0

async def get_paid_posts(posts):
    if posts == 0:
      return 0

    paid_posts = [post for post in posts if has_paid_tags(post.caption_text)]
    return paid_posts

def has_paid_tags(caption_text):
    paid_tags = ['#ad', '#sponsored', '#partnership', '@sponsor', '@partnership', 'paid partnership with', 'in collaboration with', 'thanks to']
    return any(tag.lower() in caption_text.lower() for tag in paid_tags)

async def calculate_paid_engagement_rate(username, last_n_days=18):
    try:
        user_info = cl.user_info_by_username(username)
        if user_info.follower_count == 0:
            return 0, 0

        posts = await fetch_last_n_days_posts(username, n=last_n_days)
        paid_posts = await get_paid_posts(posts)

        paid_posts_len = len(paid_posts)

        if paid_posts_len == 0 or user_info.follower_count == 0:
            return 0, 0

        total_likes_comments = sum(post.like_count + post.comment_count for post in paid_posts if post.like_count is not None and post.comment_count is not None)
        engagement_rate = (total_likes_comments / paid_posts_len) / user_info.follower_count * 100

        return engagement_rate, paid_posts_len

    except Exception as e:
        print(f"An error occurred while calculating paid engagement rate: {e}")
        return 0, 0

async def get_profile(username):
    try:
        user_info = cl.user_info_by_username(username)
        if user_info.is_private:
            response = {
                'success': True,
                'message': 'User profile is private',
                'data': None
            }
            return jsonify(response)
        posts = await fetch_last_n_days_posts(username)
        average_likes, average_comments, ratio_per_100_likes = await get_average_likes_and_comments(posts)
        engagement_rate = await calculate_engagement_rate(posts)
        most_frequent_sentiment = analyze_sentiment_and_words(posts)
        paid_engagement_rate, paid_posts_len = await calculate_paid_engagement_rate(username)
        category = await categorize_likes_comments_ratio(ratio_per_100_likes)
        average_posts_per_week = await calculate_average_posts_per_week(username, 30)
        consistency_score_value = await calculate_consistency_score(username,30)
        follower_count = cl.user_info_by_username(username).follower_count
        estimated_cost = estimate_post_price(follower_count)
        maximum_reach = estimated_reach(posts)
        reels = await fetch_last_n_days_reels(username)
        engagement_rate_reels = await calculate_engagement_rate_reels(username,reels)
        average_likes_reels, average_comments_reels, ratio_per_100_likes_reel =  await get_average_likes_and_comments_reels(reels)
        category_reels = await categorize_likes_comments_ratio(ratio_per_100_likes_reel)
        average_posts_per_week_reels = await calculate_average_reels_per_week(username, 30)
        consistency_score_value_reels = await calculate_consistency_score_reels(username,30)
        estimated_cost_reel = estimate_reel_price(follower_count)

        if all(v is not None for v in [engagement_rate, average_likes, average_comments, ratio_per_100_likes, paid_engagement_rate, paid_posts_len, category, average_posts_per_week, consistency_score_value, estimated_cost, maximum_reach, engagement_rate_reels, average_likes_reels, average_comments_reels, ratio_per_100_likes_reel, category_reels, average_posts_per_week_reels, consistency_score_value_reels, estimated_cost_reel]):
            response = {
                'success': True,
                'message': 'Data retrieved successfully',
                'username': username,
                'engagement_rate_post': format_number(round(engagement_rate, 2), is_percentage=True),
                'followers': format_number(follower_count),
                'average_likes_post': format_number(average_likes),
                'average_comments_post': format_number(average_comments),
                'likes_comments_ratio_post': format_number(round(ratio_per_100_likes, 2), is_percentage=True),
                'likes_comments_ratio_category_post': category,
                'paid_posts_len_post': paid_posts_len,
                'estimated_post_price': estimated_cost,
                'estimated_reach': maximum_reach,
                'post_frequency_post': format_number(round(average_posts_per_week,2), is_percentage=True),
                'consistency_score_post': round(consistency_score_value,2),
                'brand_safety':most_frequent_sentiment,
                'paid_post_engagement_rate_post': format_number(round(paid_engagement_rate, 2), is_percentage=True),
                'engagement_rate_reel': format_number(round(engagement_rate_reels,2 ),is_percentage = True),
                'average_likes_reel': format_number(average_likes_reels),
                'average_comments_reel': format_number(average_comments_reels),
                'likes_comment_ratio_reel': format_number(round(ratio_per_100_likes_reel, 2),is_percentage = True),
                'likes_comments_ratio_category_reels': category_reels,
                'post_frequency_reels': format_number(round(average_posts_per_week_reels, 2), is_percentage = True),
                'consistency_score_reels': round(consistency_score_value_reels, 2),
                'estimated_reel_price': estimated_cost_reel
            }
            json_data = json.dumps(response, ensure_ascii=False)
            return Response(json_data, content_type='application/json; charset=utf-8')
        else:
            response = {
                'success': False,
                'message': 'User not found or an error occurred',
                'data': None
            }
            return jsonify(response)
    except Exception as e:
        if "404 Client Error: Not Found" in str(e):
            response = {
                'success': False,
                'message': 'User not found',
                'data': None
            }
            return jsonify(response)
        elif "429" in str(e):
            time.sleep(10)
        else:
            response = {
            'success': False,
            'message': f"{e}",
            'data': None
            }
            return jsonify(response)

@app.route('/engagement_rate/<username>')
def get_profile_route(username):
    return asyncio.run(get_profile(username))

if __name__ == '__main__':
    try:
        app.run(debug = False)
    except Exception as e:
        print(f"An error occurred: {e}")