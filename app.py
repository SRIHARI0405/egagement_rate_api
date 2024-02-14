from flask import Flask, jsonify, Response
import json
import shutil
from instagrapi import Client
import asyncio
import time
import re

INSTAGRAM_USERNAME = 'loopstar154'
INSTAGRAM_PASSWORD = 'Starbuzz1234567@'

app = Flask(__name__)

proxy = "socks5://yoqytafd-6:2dng483b96qx@p.webshare.io:80"

def fetch_last_n_days_reels(cl, user_id, n):
  media = cl.user_medias(user_id, amount=n)
  reels = [item for item in media if item.media_type == 2][:n]
  reels.sort(key=lambda x: x.taken_at, reverse=True)
  return reels

def fetch_last_n_days_reels_url(cl, username, n):
  user_id = cl.user_info_by_username(username)
  media = cl.user_medias(user_id.pk, amount=n)
  reels = [item for item in media if item.media_type == 2][:n]
  reels.sort(key=lambda x: x.taken_at, reverse=True)
  return reels

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

def calculate_engagement_rate(cl,reel_Data, posts):
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

niches = ['cinema& Actor/actresses', 'Sports Person', 'Politics', 'Photographer', 'Art/Artist', 'Food', 'Fitness', 'Lifestyle', 'Fashion', 'Beauty', 'Health', 'Gaming', 'Travel', 'Sustentability', 'Parent', 'Finance', 'Animal', 'Tech','Cars & Motorbikes','Marketing']
hashtags = {
    'Lifestyle': ['#lifestyleinfluencer','#lifestyles','#lifestyle','#lifestylemodel', '#happiness','#lifestyleblogger','#lifestylephotography','#lifestyleblog','#lifestylechange','#luxurylifestyle','#lifestylechange'],
    'Fashion': ['#fashioninfluencer','#fashion', '#outfit', '#style', '#ootd', '#instaFashion', '#fashionBlogger', '#vintage', '#fashionista', '#streetStyle', '#stylish', '#instaStyle','#lifestyleinfluencer','#fashionblogger','#fashionstyle','#fashionweek','#fashiondesigner','#fashionnova','#fashionable','#fashionillustration','#fashiontrends','#fashioninspiration','#fashiongoals','#fashionsketch'],
    'Beauty': ['#beautyinfluencer', '#beauty', '#beautyandthebeast', '#beautytips', '#beautybloggers', '#beautyeditorial', '#beautybay', '#beautyobessed', '#beautyaddict', '#beautyblogs','#makeup','#Skincare','#beautyphotography','#beautymakeup','#beautytools','#beautystudio','#beautyofnature','#beautyroom','#beauty','#glowingskin','#beautyqueen','#beautynails','#beautypageant'],
    'Gaming': ['#gaminginfluncer','#gamingstation','#gaming', '#gamingcommunity','#gamer','#gamers','#gamingsetup','#gaminglife','#gamingmemes','#gamingsetups','#gamingposts','#gamingpc','#gamingroom','#gamingclips','#gamingphotography','#gamingchair','#gamingislife','#videogames', '#totalgaming','#pcgamers','#gamersetup','#gamersunite','#gamerslife','#games','#gamedev','#gamedesign','#gamer4life','#gamedevelopment','#gamesworkshop','#gamersonly'],
    'Fitness': ['#fitnessinfluencer','#fitness', '#fitnessmodel','#fitnessgirl','#fitnessjourney','#fitnessmotivation','#fitnesslife','#fitnessgoals','#fitnessfreak','#fitnessfood','#fitnessgear','#fitnesstips','#fitnessbody','#fitnessphysique','#fitnesscoach','#fitnesstransformation','#fitnesspageforall','#fitnesschallenge','#fitnesslove','#fitnessworkouts','#fitnessjunkie','#gym', '#fit', '#fitnessmotivation', '#workout', '#bodybuilding', '#training', '#fitfam','#protein','#gymmotivation','#gymrat','#gymgirl','#gymlifestyle','#gymnastics','#gymmemes'],
    'Health': ['#healthyinfluencer', '#healthy', '#healthyhair','#skincare','#healthylofestyle','#healthyfood','#healthyeating','#healthyreceipes','#healthylife','#healthyliving','#healthlifestyle','#healthrecipes','#healthbreakfast','#healthcoach','#healthybreakfast','#health','#healthcoach','#healthyeating','#healthylife','#healthyskin','#healthyhair','#mentalhealth'],
    'Travel': ['#travelinfluencer','#travelinfluencers','#travelinfluencers', '#traveltheworld','#travelphoto','#travelgram', '#travelblogger', '#travelphotography', '#travelling', '#travelblog','#traveltheworld','#travelphoto','travellife','#travelpics','#travelcouple','#travelmore','#travelers', '#travelguide','#traveldiaries','#travelphoto','#travelpic','#travelph','#travelislife','#travelwithme','#travelrealindia','#travelagent','#travelindia','#travelinspiration'],
    'Food': ['#foodinfluencer','foodinfluencers','#foodinfluencerph','#foodinfluencermarketing','#food', '#foodblogger','#foodblog','#foodlovers','#foodstyling','#foodie','#foodstyle','#foodheaven','#foodnetwork','#foodoftalkindia','#foodoftheday','#foodforlife','#foodfreedom', '#healthyfood','#foodlovers','#foodstylist','#foodlove','#foodart'],
    'Sustainability ': ['#sustainability','#sustainabilityinfluencer','#sustainabilitymatters', '#sustainabilitytips','#sustainabilityeducation','#sustainabilityblogger','#sustainabilityinfluncer' '#greenwashing', '#climatechange', '#ecofriendly', '#recycle', '##sustainablefashion', '#sustainableliving', '#zerowaste', '#nature', '#climatechange','#reuse','#environment','#eco','#reduce','#cleanenergy','#greenliving'],
    'Parent': ['#parentslove','#parentstips','#parentinghacks','#parentinganak','#parentinglife','#parentingmemes','#parentingquotes','#parents','#parentstobe','#parentslife','#parentingtips','#Childmonitoring','#smartparenting','#DigitalParenting','#childsafety','#parentssupportingparent','#parentsweekend','#momhealthcare','#mominfluencer','#mom', '#mother', '#momlife', '#parentslove','#parentsbelike','#parentsupport','#dad','#dadlife','#dadjokes','#dadbod'],
    'Finance': ['#finance','#financeinfluencer' '#financetips', '#financeiro', '#financefreedom', '#money', '#investing','#earnmoney','#financetips','#financegoals','#financecoach','#financeblogger','#financefreedom','#financememes','#insurance','#stockmarketindia','#stockmarket','#ipo','#shares','#stocks','#invest','#investing','#economy'],
    '#photography': ['#photographyinfluencer','#photographyeveryday','#photographylovers','#photographyart','#photographyislife','#photographysouls','#photographylife','#fashionphotography','#wildlifephotography','#mobilephotography','#dronephotography','#indianphotography', '#shoot','#photographers','#Photographerlife'],
    'Pets': ['#animalinfluence','#animalinfluencer','#animalinfluences','#animalinfluencers','#pet','#petinfluncer','#pets','#petslovers','petfriendly','petshop','petoftheday','petphotography','#petgrommer','#petshop','#petparent','#petoriginal','#cats', '#dogs', '#petsitting', '#petstore', '#petsarefamily', '#petsmart', '#petsitter', '#petslover'],
    'Tech': ['#techinfluncer','#tech','#gadgets', '#gadgetstore','#gadgetsnews','#amazongadgets','#coolgadgets''#techno','#techhouse','#technogadgets','#techstartup','#techsupport','#techcompany','#techjobs','#technologytrends' '#technology', '#innovation', '#technofamily', '#technolover', '#vettech', '#techsupport','#techgadgets','#techblogger','#technovibes'],
    'Cars & Motorbikes': ['#car','#cars','#carinfluncer','#cars247','#carsdaily','#carspotter','#carsofinsta','#carlovers','#carswithoutlimits','#carshow','#carcare','#carphotography','#carlifestyle','#carsforsale','#carsandcoffee','#carsofinstagram','#sportscar', '#sportscars', '#ride', '#rider', '#bikeinstagram', '#instabike','#motorcycle','#biker','#bikelife','#bikeride','#bike','#bikelife','#bikeride','#bikerlife','#bikergirls','#bikeparking','#biketour','#bikers','#bikelovers','#bikersofinstagram','#instamotorcycle','#sportbike','#superbike','#bikeinfluencer','#bikeinfluence','#speed', '#vehicle'],
    'Advertising/Marketing': ['#marketing','#marketingdigital','#marketingstrategy','#marketingtips','#marketingonline','#marketingagency','#marketingconsultant','#marketingconsultants','#marketingtools','#marketingideas',]
}

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
    with open('session-loop1.json', 'w') as file:
        json.dump(data, file, indent=4)
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

      reels_data =  fetch_last_n_days_reels(cl, user_info.pk, n=18)
      
      if not reels_data:
          return jsonify({
              'success': False,
              'message': 'No reels data available',
              'data': None
          })

      latest_post = reels_data[0]
      latest_post_engagement_rate = calculate_engagement_rate_reels(cl, latest_post)
      engagement_rate = calculate_engagement_rate(cl, latest_post, reels_data)
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
              user_info = cl.user_info(cl.user_id)
              if user_info.is_private:
                response = {
                  'success': True,
                  'message': 'User profile is private',
                  'data': None
                }
                return jsonify(response)
              reel_data_pk = cl.media_pk_from_code(reel_id)
            except Exception as e:
              cl = Client(proxy=proxy)
              cl.login(INSTAGRAM_USERNAME,INSTAGRAM_PASSWORD)
              with open('session-loop.json', 'r') as file:
                data = json.load(file)
                data['authorization_data'] = cl.authorization_data
              with open('session-loop1.json', 'w') as file:
                json.dump(data, file, indent=4)
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
            play_count = reel_data.play_count
            thumbnail_urls = str(reel_data.thumbnail_url)
            caption_text = reel_data.caption_text
            brand_name_usertag_reel =  brand_name_usertag([reel_data])
            brand_name_user_reel =  brand_name_user([reel_data])
            reel_username = reel_data.user.username
            reels_data1 = fetch_last_n_days_reels_url(cl, reel_username, n=18)
            engagement_rate_reel = calculate_engagement_rate(cl, reel_data, reels_data1)
            engagement_rate_reel_url =  calculate_engagement_rate_reels(cl, reel_data)
            mentions = re.findall(r'@\w+', caption_text)
            hashtags = re.findall(r'#\w+', caption_text)

            response = {
                'success': True,
                'message': 'Reel data retrieved successfully',
                'reel_info': {
                    'likes_count': likes_count,
                    'comments_count': comments_count,
                    'view_count': play_count,
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

@app.route('/user/<username>')
def get_user_niches(username):
  try:
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
      with open('session-loop1.json', 'w') as file:
          json.dump(data, file, indent=4)
      shutil.copyfile('session-loop1.json', 'session-loop.json')
      user_info = cl.user_info_by_username(username, use_cache=False)
    try:
        if user_info is None:
            return jsonify({"error": "User information not found."}), 404

        final_niches = []

        if user_info.full_name:
            fullname = user_info.full_name.lower()
            found_niches_fullname = [niche for niche in niches if niche.lower() in fullname]
            final_niches.extend(found_niches_fullname)

        if user_info.username:
            username_lower = user_info.username.lower()
            found_niches_username = [niche for niche in niches if niche.lower() in username_lower]
            final_niches.extend(found_niches_username)

        if user_info.category:
            category_lower = user_info.category.lower()
            if any(keyword in category_lower for keyword in ['actor', 'actress']):
                final_niches.append('cinema& Actor/actresses')
            elif any(keyword in category_lower for keyword in ['beauty', 'cosmetic & personal care', 'beauty, cosmetic & personal care']):
                final_niches.append('Beauty')
            elif any(keyword in category_lower for keyword in ['gamer', 'games/toys', 'toys', 'gaming video creator']):
                final_niches.append('Gaming')
            elif any(keyword in category_lower for keyword in ['athlete', 'sportsperson']):
                final_niches.append('Sports Person')
            elif any(keyword in category_lower for keyword in ['politician', 'political party']):
                final_niches.append('Politics')
            elif 'artist' in category_lower:
                final_niches.append('Art/Artist')
            elif any(keyword in category_lower for keyword in ['fashion', 'fashion model', 'fashion designer']):
                final_niches.append('Fashion')
            elif any(keyword in category_lower for keyword in ['health', 'nutritionist', 'doctor', 'hospital', 'medical center', 'medical school']):
                final_niches.append('Health')
            elif any(keyword in category_lower for keyword in ['finance']):
                final_niches.append('Finance')
            elif any(keyword in category_lower for keyword in ['Science & Tech']):
                final_niches.append('Tech')
            elif any(keyword in category_lower for keyword in ['photographer','videographer']):
                final_niches.append('Photographer')
            elif any(keyword in category_lower for keyword in ['cars','motorcycle dealership']):
                final_niches.append('Cars & Motorbikes')
            elif any(keyword in category_lower for keyword in ['advertising/marketing','advertising','marketing']):
                final_niches.append('Marketing')
            elif any(keyword in category_lower for keyword in ['chef']):
                final_niches.append('Food')
            elif 'bakery' in category_lower:
                final_niches.append('Food')

        if user_info.biography:
            bio = user_info.biography.lower()
            found_niches_bio = [niche for niche in niches if niche.lower() in bio]
            final_niches.extend(found_niches_bio)

        found_hashtags = {}
        if user_info.pk:
            recent_posts = cl.user_medias(user_info.pk, amount=50)
            for post in recent_posts:
                caption_text = post.caption_text.lower()
                post_hashtags = re.findall(r'#\w+', caption_text)[:16]
                for hashtag in post_hashtags:
                    for niche, niche_hashtags in hashtags.items():
                        if hashtag in niche_hashtags:
                            found_hashtags[niche] = found_hashtags.get(niche, 0) + 1
                            break

        all_niches_count = {niche: found_hashtags.get(niche, 0) for niche in niches}
        max_count = max(all_niches_count.values(), default=0)

        if max_count > 0:
            max_niches = [niche for niche, count in all_niches_count.items() if count == max_count]
            final_niches.extend(max_niches if max_niches else ['Lifestyle'])

        if not final_niches:
            final_niches.append('Lifestyle')

        final_niches = list(set(final_niches))

        response = {
           'success': True,
           'message': 'Reel data retrieved successfully',
           'data': {
              'username': username,
              'niches' : final_niches
           }
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
  except Exception as e:
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