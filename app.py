from flask import Flask, jsonify, Response
import json
import shutil
from instagrapi import Client
import asyncio
import time
import re

INSTAGRAM_USERNAME = 'loopstar154'
INSTAGRAM_PASSWORD = 'Starbuzz123456@'

app = Flask(__name__)

proxy = "socks5://yoqytafd-6:2dng483b96qx@p.webshare.io:80"

def brand_name_usertag(reels_data):
    usernames = []
    for reel in reels_data:
        for user in reel.usertags:
            usernames.append(user.user.username)
    return usernames

def brand_name_user(reels_data):
    usernames = []
    for reel in reels_data:
            usernames.append(reel.user.username)
    return usernames

def calculate_engagement_rate(posts, count):
    if not posts:
        return 0
    visible_likes_comments = sum(post.like_count + post.comment_count for post in posts if post.like_count is not None and post.comment_count is not None)
    if visible_likes_comments == 0:
        return 0
    engagement_rate = (visible_likes_comments / len(posts)) / count * 100
    return engagement_rate

def calculate_engagement_rate_reels(reel_Data, count):
    if not reel_Data:
      return 0
    visible_likes_comments_reel = reel_Data.like_count + reel_Data.comment_count
    if visible_likes_comments_reel == 0:
        return 0
    engagement_rate = (visible_likes_comments_reel/1)/count * 100
    return engagement_rate


async def get_profile(username):
  try:
      cl = Client(proxy=proxy)
      cl.load_settings('session-loop.json')
      user_info = cl.user_info_by_username(username, use_cache=False)
  except Exception as e:
      cl = Client(proxy=proxy)
      cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)
      with open('session-loop.json', 'r') as file:
          data = json.load(file)
          data['authorization_data'] = cl.authorization_data
          modified_json = json.dumps(data)
      with open('session-loop1.json', 'w') as file:
          file.write(modified_json)
      shutil.copyfile('session-loop1.json', 'session-loop.json')
      user_info = cl.user_info_by_username(username, use_cache=False)

  try:
      if user_info.is_private:
          response = {
              'success': True,
              'message': 'User profile is private',
              'data': None
          }
          return jsonify(response)

      media = cl.user_medias(user_info.pk, amount=18)
      if not media:

        return {
            'success': False,
            'message': 'Failed to fetch reel data',
            'data': None
        }
      
      reels = [item for item in media if item.media_type == 2][:18]
      sorted_reels = sorted(reels, key=lambda x: x.taken_at, reverse=True)

      engagement_rate = calculate_engagement_rate(sorted_reels, user_info.follower_count) 
      latest_post = sorted_reels[0]
      latest_post_engagement_rate = calculate_engagement_rate([latest_post], user_info.follower_count)
      brand_name_usertag_reel =  brand_name_usertag([latest_post])
      brand_name_user_reel =  brand_name_user([latest_post])
      likes_count = latest_post.like_count
      comments_count = latest_post.comment_count
      caption_text = latest_post.caption_text
      view_count = latest_post.view_count
      thumbnail_urls = str(latest_post.thumbnail_url)
      hashtags = re.findall(r'#\w+', caption_text)
      mentions = re.findall(r'@\w+', caption_text)

      response =  {
          'success': True,
          'message': 'Data retrieved successfully',
          'username': username,
          'latest_post': {
              'likes_count': likes_count,
              'comments_count': comments_count,
              'view_count': view_count,
              'thumbnail_urls': thumbnail_urls,
              'engagement_rate_post': round(latest_post_engagement_rate, 2),
              'caption_text': caption_text,
              'hashtags': hashtags,
              'mentions': mentions,
              'brand_name_usertag': brand_name_usertag_reel,
              'brand_name_user': brand_name_user_reel
          },
          'engagement_rate': round(engagement_rate, 2)
      }
      json_data = json.dumps(response, ensure_ascii=False)
      return Response(json_data, content_type='application/json; charset=utf-8')

  except Exception as e:
      if "404 Client Error: Not Found" in str(e):
          response = {
              'success': False,
              'message': 'User not found',
              'data': None
          }
      elif "429" in str(e):
          time.sleep(10)
      else:
          response = {
              'success': False,
              'message': f"{e}",
              'data': None
          }

      return jsonify(response)


@app.route('/reel_info/<path:reel_url>')
def get_reel_info(reel_url):
    try:
        if not reel_url.startswith('https://www.instagram.com/reel/'):
            response = {
                'success': False,
                'message': 'Invalid reel URL format',
                'data': None
            }
            return jsonify(response)

        reel_id_match = re.search(r'/reel/([A-Za-z0-9_-]+)', reel_url)
        if reel_id_match:
            reel_id = reel_id_match.group(1)

            try:
              cl = Client(proxy=proxy)
              cl.load_settings('session-loop.json')
              reel_data_pk = cl.media_pk_from_code(reel_id)
            except Exception as e:
              cl = Client(proxy=proxy)
              cl.login(INSTAGRAM_USERNAME,INSTAGRAM_PASSWORD)
              with open('session-loop.json', 'r') as file:
                data = json.load(file)
                data['authorization_data'] = cl.authorization_data
                modified_json = json.dumps(data)
              with open('session-loop1.json', 'w') as file:
                file.write(modified_json)
              shutil.copyfile('session-loop1.json', 'session-loop.json')
              reel_data_pk = cl.media_pk_from_code(reel_id)
            
            if reel_data_pk is None:
                response = {
                    'success': False,
                    'message': 'Invalid reel URL',
                    'data': None
                }
                return jsonify(response)
            
            reel_data = cl.media_info(reel_data_pk, use_cache=False)
            if not reel_data:
                return {
                    'success': False,
                    'message': 'Failed to fetch reel data',
                    'data': None
                }
            
            likes_count = reel_data.like_count
            comments_count = reel_data.comment_count
            view_count = reel_data.view_count
            thumbnail_urls = str(reel_data.thumbnail_url)
            caption_text = reel_data.caption_text
            brand_name_usertag_reel =  brand_name_usertag([reel_data])
            brand_name_user_reel =  brand_name_user([reel_data])
            reel_username = reel_data.user.username

            user_id = cl.user_info_by_username(reel_username)
            media = cl.user_medias(user_id.pk, amount=18)
            reels = [item for item in media if item.media_type == 2][:18]
            sorted_reels = sorted(reels, key=lambda x: x.taken_at, reverse=True)  
                      
            user_info = cl.user_info_by_username(reel_username)
            engagement_rate_reel = calculate_engagement_rate(sorted_reels, user_info.follower_count)
            reel_username = reel_data.user.username
            user_info = cl.user_info_by_username(reel_username)
            engagement_rate_reel_url =  calculate_engagement_rate_reels(reel_data, user_info.follower_count)
            mentions = re.findall(r'@\w+', caption_text)
            hashtags = re.findall(r'#\w+', caption_text)

            response = {
                'success': True,
                'message': 'Reel data retrieved successfully',
                'reel_info': {
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'view_count': view_count,
                    'thumbnail_urls': thumbnail_urls,
                    'caption_text': caption_text,
                    'mentions': mentions,
                    'hashtags': hashtags,
                    'engagement_rate_reel': round(engagement_rate_reel_url, 2),
                    'brand_name_usertag': brand_name_usertag_reel,
                    'brand_name_user': brand_name_user_reel
                },
                'engagement_rate': round(engagement_rate_reel, 2)
            }
            json_data = json.dumps(response, ensure_ascii=False)
            return Response(json_data, content_type='application/json; charset=utf-8')
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
        elif "Invalid media_id" in str(e):
          response = {
              'success': False,
              'message': 'Invalid URL provided. Please provide a valid URL.',
              'data': None
          }
          return jsonify(response)
        else:
            response = {
                'success': False,
                'message': f"{e}",
                'data': None
            }
            return jsonify(response)

@app.route('/profile_info/<username>')
def get_profile_route(username):
    return asyncio.run(get_profile(username))

if __name__ == '__main__':
    try:
        app.run(debug = False)
    except Exception as e:
        print(f"An error occurred: {e}")