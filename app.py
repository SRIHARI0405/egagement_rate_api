import asyncio
from flask import Flask, jsonify, Response, render_template
import json
from instagrapi import Client
from instagrapi.types import User
import re

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

def get_average_likes(username, batch_size=300):
    try:
        user_id = cl.user_id_from_username(username)
        all_posts = []

        count = 0
        while True:
            batch = cl.user_medias(user_id, amount=batch_size, sleep=0)
            if not batch:
                break
            all_posts.extend(batch)
            count += len(batch)
            if count >= batch_size:
                break

        total_likes = sum(post.like_count for post in all_posts)
        average_likes = total_likes / len(all_posts) if all_posts else 0

        return average_likes
    except Exception as e:
        print(f"An error occurred while calculating average likes: {e}")
        return None

def format_likes(likes):
    if likes < 1000:
        return str(round(likes, 2))
    elif likes < 1000000:
        return f"{round(likes / 1000, 2)}K"
    else:
        return f"{round(likes / 1000000, 2)}M"


async def calculate_engagement_rate(username, last_n_posts=10):
    try:
        user_id = cl.user_id_from_username(username)
        user_info = cl.user_info_by_username(username)
        followers_count = user_info.follower_count

        if followers_count == 0:
            return None

        posts = cl.user_medias(user_id, amount=last_n_posts)
        total_posts = len(posts)

        if total_posts == 0:
            return 0
        total_likes = sum(post.like_count for post in posts)
        total_comments = sum(post.comment_count for post in posts)
        total_interactions = total_likes + total_comments

        if total_interactions == 0:
            return 0

        engagement_rate = (total_interactions / total_posts) / followers_count * 100
        return engagement_rate

    except Exception as e:
        print(f"An error occurred while calculating engagement rate: {e}")
        return None

async def get_profile(username):
    try:
        user_info = cl.user_info_by_username(username)
        engagement_rate = await calculate_engagement_rate(username)
        average_likes = get_average_likes(username)

        if engagement_rate is not None and average_likes is not None:
            response = {
                'success': True,
                'message': 'Data retrieved successfully',
                'username': username,
                'engagement_rate': round(engagement_rate, 2) if isinstance(engagement_rate, (float, int)) else None,
                'followers': user_info.follower_count,
                'average_likes': format_likes(average_likes) if isinstance(engagement_rate, (float, int)) else None 
            }
            json_data = json.dumps(response, ensure_ascii=False)
            return Response(json_data, content_type='application/json; charset=utf-8')
        else:
            response = {
                'success': False,
                'message': 'User not found or error occurred',
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
        app.run(debug = False)
    except Exception as e:
        print(f"An error occurred: {e}")