from flask import Flask, jsonify, request
import datetime
import json
import pytz
import shutil
from instagrapi import Client
import asyncio
import time
import re

INSTAGRAM_USERNAME = 'starbuzz286'
INSTAGRAM_PASSWORD = 'Starbuzz123@'

app = Flask(__name__)

proxy = "socks5://yoqytafd-6:2dng483b96qx@p.webshare.io:80"

url_queue = asyncio.Queue(maxsize=30)

def fetch_last_n_days_posts(cl, username, n):
    user_id = cl.user_id_from_username(username)
    media = cl.user_medias(user_id, amount=n)
    reels = [item for item in media if item.media_type == 2 or item.media_type !=2][:n]
    reels.sort(key=lambda x: x.taken_at, reverse=True)
    return reels

def brand_name_usertag(media_data):
    usernames = []
    for item in media_data:
        for user in item.usertags:
            usernames.append(user.user.username)
    return usernames

def brand_name_user(media_data):
    usernames = []
    for item in media_data:
        usernames.append(item.user.username)
    return usernames

def calculate_engagement_rate(cl, reel_Data, posts):
    if not posts:
        return 0
    visible_likes_comments = sum(post.like_count + post.comment_count for post in posts if post.like_count is not None and post.comment_count is not None)
    if visible_likes_comments == 0:
        return 0
    reel_username = reel_Data.user.username
    user_info = cl.user_info_by_username(reel_username)
    engagement_rate = (visible_likes_comments / len(posts)) / user_info.follower_count * 100
    return engagement_rate

def calculate_engagement_rate_reels(cl, reel_Data):
    if not reel_Data:
        return 0
    visible_likes_comments_reel = reel_Data.like_count + reel_Data.comment_count 
    if visible_likes_comments_reel == 0:
        return 0
    reel_username = reel_Data.user.username
    user_info = cl.user_info_by_username(reel_username)
    engagement_rate = (visible_likes_comments_reel/1)/user_info.follower_count * 100
    return engagement_rate

async def process_urls(urls):
    results = []
    try:
        cl = Client(proxy=proxy)
        cl.load_settings('session-loop.json')
        for url_data in urls:
            id = url_data['id']
            url = url_data['link']
            utc_now = datetime.datetime.now(pytz.utc)
            utc_datetime_str = utc_now.strftime("%Y-%m-%d %H:%M:%S.%f")[:23] + utc_now.strftime("%z")
            if 'instagram.com/p/' in url:
                result = await get_post_info(id, url, cl, utc_datetime_str)
            elif 'instagram.com/reel/' in url:
                result = await get_reel_info(id, url, cl, utc_datetime_str)
            else:
                result = {
                    'success': False,
                    'message': 'Unsupported media type',
                    'data': None
                }
            results.append(result)
    except Exception as e:
        results.append({
            'success': False,
            'message': str(e),
            'data': None
        })
    return results

async def get_post_info(id, post_url, cl, timestamp):
    try:
        if not post_url.startswith('https://www.instagram.com'):
            response = {
                'success': False,
                'message': 'Invalid post URL format',
                'data': None
            }
            return response

        post_id_match = re.search(r'/p/([A-Za-z0-9_-]+)',  post_url.split('?')[0])
        if post_id_match:
            post_id = post_id_match.group(1)
            try:
                post_data_pk = cl.media_pk_from_code(post_id)
            except Exception as e:
                cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                with open('session-loop.json', 'r') as file:
                    data = json.load(file)
                    data['authorization_data'] = cl.authorization_data
                with open('session-loop1.json', 'w') as file:
                    json.dump(data, file, indent=4)
                shutil.copyfile('session-loop1.json', 'session-loop.json')
                post_data_pk = cl.media_pk_from_code(post_id)

            if post_data_pk is None:
                response = {
                    'success': False,
                    'message': 'Invalid post URL',
                    'data': None
                }
                return response

            post_data = cl.media_info(post_data_pk, use_cache=False)
            await asyncio.sleep(5) 
            if not post_data:
                return {
                    'success': False,
                    'message': 'Failed to fetch post data',
                    'data': None
                }

            likes_count = post_data.like_count
            comments_count = post_data.comment_count
            play_count = post_data.play_count  
            if play_count is None:
                await asyncio.sleep(8) 
                reel_data = cl.media_info(post_data_pk, use_cache=False)
                play_count = reel_data.play_count 

                if play_count is None:
                    await asyncio.sleep(8) 
                    reel_data = cl.media_info(post_data_pk, use_cache=False)
                    play_count = reel_data.play_count 

                    if play_count is None:
                        await asyncio.sleep(8) 
                        reel_data = cl.media_info(post_data_pk, use_cache=False)
                        play_count = reel_data.play_count 

            caption_text = post_data.caption_text
            brand_name_usertag_post = brand_name_usertag([post_data])
            brand_name_user_post = brand_name_user([post_data])
            post_username = post_data.user.username
            post_data1 = fetch_last_n_days_posts(cl, post_username, n=18)
            engagement_rate_post = calculate_engagement_rate(cl, post_data, post_data1)
            engagement_rate_post_url = calculate_engagement_rate_reels(cl, post_data)
            mentions = re.findall(r'@\w+', caption_text)
            hashtags = re.findall(r'#\w+', caption_text)

            response = {
                'post_info': {
                    'likes': likes_count,
                    'coments': comments_count,
                    'views': play_count,
                    'caption_text': caption_text,
                    'mentions': mentions,
                    'hashtags': hashtags,
                    'engagement_rate_post': round(engagement_rate_post_url, 2),
                    'brand_name_usertag': brand_name_usertag_post,
                    'brand_name_user': brand_name_user_post
                },
                'engagement_rate': round(engagement_rate_post, 2),
                'postId': id,
                'timestamp': timestamp
            }
            return response
    except Exception as e:
        if "404 Client Error: Not Found" in str(e):
            response = {
                'success': False,
                'message': 'User not found',
                'data': None
            }
            return response
        elif "429" in str(e):
            time.sleep(10)
        elif "Invalid media_id" in str(e):
            response = {
                'success': False,
                'message': 'Invalid URL provided. Please provide a valid URL.',
                'data': None
            }
            return response
        else:
            response = {
                'success': False,
                'message': f"{e}",
                'data': None
            }
            return response

async def get_reel_info(id, reel_url, cl, timestamp):
    try:
        if not reel_url.startswith('https://www.instagram.com'):
            response = {
                'success': False,
                'message': 'Invalid reel URL format',
                'data': None
            }
            return response

        reel_id_match = re.search(r'/reel/([A-Za-z0-9_-]+)', reel_url)
        if reel_id_match:
            reel_id = reel_id_match.group(1)
            try:
                reel_data_pk = cl.media_pk_from_code(reel_id)
            except Exception as e:
                print("hello")
                cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
                print("done")
                with open('session-loop.json', 'r') as file:
                    data = json.load(file)
                    print(cl.authorization_data)
                    data['authorization_data'] = cl.authorization_data
                with open('session-loop1.json', 'w') as file:
                    json.dump(data, file, indent=4)
                    print(cl.authorization_data)
                shutil.copyfile('session-loop1.json', 'session-loop.json')
                reel_data_pk = cl.media_pk_from_code(reel_id)

            if reel_data_pk is None:
                response = {
                    'success': False,
                    'message': 'Invalid reel URL',
                    'data': None
                }
                return response

            reel_data = cl.media_info(reel_data_pk, use_cache=False)
            if not reel_data:
                return {
                    'success': False,
                    'message': 'Failed to fetch reel data',
                    'data': None
                }

            likes_count = reel_data.like_count
            comments_count = reel_data.comment_count
            play_count = reel_data.play_count

            if play_count is None:
                await asyncio.sleep(8) 
                reel_data = cl.media_info(reel_data_pk, use_cache=False)
                play_count = reel_data.play_count 

                if play_count is None:
                    await asyncio.sleep(8) 
                    reel_data = cl.media_info(reel_data_pk, use_cache=False)
                    play_count = reel_data.play_count 

                    if play_count is None:
                        await asyncio.sleep(8) 
                        reel_data = cl.media_info(reel_data_pk, use_cache=False)
                        play_count = reel_data.play_count 

            caption_text = reel_data.caption_text
            brand_name_usertag_reel = brand_name_usertag([reel_data])
            brand_name_user_reel = brand_name_user([reel_data])
            reel_username = reel_data.user.username
            reels_data1 = fetch_last_n_days_posts(cl, reel_username, n=18)
            engagement_rate_reel = calculate_engagement_rate(cl, reel_data, reels_data1)
            engagement_rate_reel_url = calculate_engagement_rate_reels(cl, reel_data)
            mentions = re.findall(r'@\w+', caption_text)
            hashtags = re.findall(r'#\w+', caption_text)

            response = {
                'reel_info': {
                    'likes': likes_count,
                    'coments': comments_count,
                    'views': play_count,
                    'caption_text': caption_text,
                    'mentions': mentions,
                    'hashtags': hashtags,
                    'engagement_rate_reel': round(engagement_rate_reel_url, 2),
                    'brand_name_usertag': brand_name_usertag_reel,
                    'brand_name_user': brand_name_user_reel
                },
                'engagement_rate': round(engagement_rate_reel, 2),
                'postId': id,
                'timestamp': timestamp
            }
            return response
    except Exception as e:
        if "404 Client Error: Not Found" in str(e):
            response = {
                'success': False,
                'message': 'User not found',
                'data': None
            }
            return response
        elif "429" in str(e):
            time.sleep(10)
        elif "Invalid media_id" in str(e):
            response = {
                'success': False,
                'message': 'Invalid URL provided. Please provide a valid URL.',
                'data': None
            }
            return response
        else:
            response = {
                'success': False,
                'message': f"{e}",
                'data': None
            }
            return response

@app.route('/media_info', methods=['POST'])
def get_media_info_route():
    try:
        data = request.json
        if len(data) > 30:
            return jsonify({'success': False, 'message': 'URL list exceeds processing limit'})
        results = asyncio.run(process_urls(data))
        return jsonify(results)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    try:
        app.run(debug = False)
    except Exception as e:
        print(f"An error occurred: {e}")