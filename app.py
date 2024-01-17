import time
from flask import Flask, jsonify, Response, render_template
import json
from instagrapi import Client
from instagrapi.types import User
import re

app = Flask(__name__)

INSTAGRAM_USERNAME = 'loopstar154'
INSTAGRAM_PASSWORD = 'Starbuzz6@'

proxy = "socks5://yoqytafd-6:2dng483b96qx@p.webshare.io:80"
cl = Client(proxy=proxy)

try:
    cl.load_settings('session-loop.json')
    cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
except Exception as e:
    print(f"Instagram login failed: {e}")
def calculate_engagement_rate(username, last_n_posts=10):
    try:
        user_id = cl.user_id_from_username(username)
        user_info = cl.user_info_by_username(username)
        followers_count = user_info.follower_count

        if followers_count == 0:
            return None

        posts = cl.user_medias(user_id)
        total_posts = len(posts)
        print(total_posts)

        if total_posts == 0:
            return 0  

        if total_posts > last_n_posts:
            posts_to_consider = posts[:last_n_posts]  
        else:
            posts_to_consider = posts

        total_likes = sum(post.like_count for post in posts_to_consider)
        total_comments = sum(post.comment_count for post in posts_to_consider)
        total_interactions = total_likes + total_comments

        if total_interactions == 0:
            return 0  

        engagement_rate = (total_interactions / len(posts_to_consider)) / followers_count * 100
        return engagement_rate

    except Exception as e:
        print(f"An error occurred while calculating engagement rate: {e}")
        return None




@app.route('/engagement_rate/<username>')
def get_profile(username):
    max_retries = 3
    retry_delay = 5

    for retry_number in range(1, max_retries + 1):
        try:
            engagement_rate = calculate_engagement_rate(username)
            if engagement_rate is not None:
                response = {
                    'success': True,
                    'message': 'Data retrieved successfully',
                    'username': username,
                    'engagement_rate': round(engagement_rate, 2)
                }
                json_data = json.dumps(response, ensure_ascii=False)
                return Response(json_data, content_type='application/json; charset=utf-8')
            else:
                response = {
                    'success': False,
                    'message': 'User not found',
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
                print(f"Rate limit exceeded. Retrying in {retry_delay} seconds (Retry {retry_number}/{max_retries}).")
                time.sleep(retry_delay)
            else:
                response = {
                    'success': False,
                    'message': f"{e}",
                    'data': None
                }
                return jsonify(response)

    response = {
        'success': False,
        'message': 'Max retries reached. Unable to fetch profile.',
        'data': None
    }
    return jsonify(response)

if __name__ == '__main__':
    try:
        app.run(debug= False)
    except Exception as e:
        print(f"An error occurred: {e}")