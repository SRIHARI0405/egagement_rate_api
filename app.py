import asyncio
from flask import Flask, jsonify, Response, render_template
import json
from instagrapi import Client
from datetime import datetime, timedelta
from instagrapi.types import User

app = Flask(__name__)

INSTAGRAM_USERNAME = 'loopstar154'
INSTAGRAM_PASSWORD = 'Starbuzz123@'

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

async def categorize_likes_comments_ratio(ratio):

    if ratio == 0:
      return "No Post"

    if ratio < 1:
        return "Good"
    elif 1 <= ratio < 5:
        return "Average"
    else:
        return "Low"

async def calculate_engagement_rate(posts):
  if posts == 0:
    return 0
  visible_likes_comments = sum(post.like_count + post.comment_count for post in posts if post.like_count is not None and post.comment_count is not None)

  if visible_likes_comments == 0:
    return 0

  user_info = cl.user_info_by_username(posts[0].user.username)
  engagement_rate = (visible_likes_comments / len(posts)) / user_info.follower_count * 100
  return engagement_rate

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

# async def calculate_post_reachability(posts):
#     if not posts or len(posts) == 0:
#         return 0

#     total_views = sum(post.view_count for post in posts)
#     followers_count = cl.user_info_by_username(posts[0].user.username).follower_count

#     if total_views == 0 or followers_count == 0:
#         return 0

#     post_reachability_percent = (total_views / followers_count) * 100
#     return post_reachability_percent

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
        paid_engagement_rate, paid_posts_len = await calculate_paid_engagement_rate(username)
        category = await categorize_likes_comments_ratio(ratio_per_100_likes)
        average_posts_per_week = await calculate_average_posts_per_week(username, 30)
        follower_count = cl.user_info_by_username(username).follower_count

        if all(v is not None for v in [engagement_rate, average_likes, average_comments, ratio_per_100_likes, paid_engagement_rate, paid_posts_len, category, average_posts_per_week]):
            response = {
                'success': True,
                'message': 'Data retrieved successfully',
                'username': username,
                'engagement_rate': format_number(round(engagement_rate, 2), is_percentage=True),
                'followers': format_number(follower_count),
                'average_likes': format_number(average_likes),
                'average_comments': format_number(average_comments),
                'likes_comments_ratio': format_number(round(ratio_per_100_likes, 2), is_percentage=True),
                'likes_comments_ratio_category': category,
                'paid_posts_len': paid_posts_len,
                'post_frequency': format_number(round(average_posts_per_week,2), is_percentage=True),
                'paid_post_engagement_rate': format_number(round(paid_engagement_rate, 2), is_percentage=True)
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
        response = {
            'success': False,
            'message': f"An error occurred: {e}",
            'data': None
        }
        return jsonify(response)

@app.route('/engagement_rate/<username>')
def get_profile_route(username):
    return asyncio.run(get_profile(username))

if __name__ == '__main__':
    try:
        app.run(port=5003)
    except Exception as e:
        print(f"An error occurred: {e}")