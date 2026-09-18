import os
import time
import asyncio
import re
import urllib.request
import feedparser
import yt_dlp
from telethon import TelegramClient
from telethon.sessions import StringSession
from PIL import Image
import streamlit as st

st.title("🤖 RSS Downloader Bot")
st.success("Bot သည် နောက်ကွယ်တွင် 24/7 အောင်မြင်စွာ Run နေပါပြီ။")

API_ID = 36740762                   
API_HASH = '0b57d4e8b9708863562c53a969a33d48'    
PHONE = '+959883836676'            
MY_CHANNEL = '@triplex3333' 
SESSION_STRING = 'သင်၏_TELEGRAM_STRING_SESSION_ကို_ဒီမှာထည့်ပါ'
RSS_FEED_URL = 'https://mmhdhub.com' 

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# --- [အသစ်ပြင်ဆင်ချက်] DATABASE မလိုဘဲ CHANNEL ထဲမှာ ရှိမရှိ လှမ်းစစ်သည့် စနစ် ---
async def is_already_sent(video_title):
    try:
        # Channel ထဲက နောက်ဆုံးပို့ထားတဲ့ Message အပုဒ် ၁၀၀ ထဲမှာ ဒီခေါင်းစဉ် ပါပြီးသားလား ရှာဖွေခြင်း
        async for message in client.iter_messages(MY_CHANNEL, limit=100):
            if message.text and video_title in message.text:
                return True
    except Exception as e:
        print(f"Channel History စစ်ဆေးရာတွင် အမှားရှိသည်: {e}")
    return False

def extract_thumbnail(entry):
    if 'media_content' in entry and len(entry.media_content) > 0:
        return entry.media_content[0]['url']
    if 'links' in entry:
        for link in entry.links:
            if 'image' in link.get('type', ''):
                return link.get('href')
    html_content = entry.get('summary', '') + entry.get('description', '')
    img_urls = re.findall(r'<img [^>]*src="([^"]+)"', html_content)
    if img_urls:
        for url in img_urls:
            if not any(bad in url.lower() for bad in ['ads', 'banner', 'pixel', 'logo']):
                return url
    return None

def get_videos_from_feed():
    video_data = []
    BAD_KEYWORDS = ['googleads', 'adsterra', 'banner', 'click', 'promo', 'register', 'adsense', 'popunder', 'ad-link']
    try:
        feed = feedparser.parse(RSS_FEED_URL)
        for entry in feed.entries:
            video_url = entry.link
            video_title = entry.title if 'title' in entry else "ခေါင်းစဉ်မရှိသော ဗီဒီယို"
            if any(keyword in video_url.lower() for keyword in BAD_KEYWORDS) or any(keyword in video_title.lower() for keyword in BAD_KEYWORDS):
                continue
            thumbnail_url = extract_thumbnail(entry)
            video_data.append({'url': video_url, 'title': video_title, 'thumb_url': thumbnail_url})
    except Exception as e:
        print(f"Feed ကို ဖတ်ရတာ အမှားရှိနေပါတယ်: {e}")
    return video_data

def download_video(video_page_url):
    output_filename = 'temp_downloaded_video.mp4'
    ydl_opts = {
        'outtmpl': output_filename,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'quiet': True,
        'buffersize': '1024K'
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_page_url, download=True)
            duration = info.get('duration', 0)
        if os.path.exists(output_filename):
            return output_filename, int(duration)
    except Exception as e:
        print(f"yt-dlp ဖြင့် ဒေါင်းလုဒ်ဆွဲရာတွင် အမှားရှိပါတယ်: {e}")
    return None, 0

def download_thumbnail(url):
    if not url:
        return None
    temp_raw_path = 'temp_raw_thumb'
    final_jpg_path = 'temp_thumb.jpg'
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response, open(temp_raw_path, 'wb') as out_file:
            out_file.write(response.read())
        with Image.open(temp_raw_path) as img:
            if img.mode in ('RGBA', 'LA'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split())
                background.save(final_jpg_path, 'JPEG')
            else:
                img.convert('RGB').save(final_jpg_path, 'JPEG')
        if os.path.exists(temp_raw_path):
            os.remove(temp_raw_path)
        return final_jpg_path
    except Exception as e:
        print(f"Thumbnail ပြုပြင်ရတာ အဆင်မပြေပါ: {e}")
        if os.path.exists(temp_raw_path):
            os.remove(temp_raw_path)
        return None

async def main_bot_process():
    await client.start(phone=PHONE)
    print("Streamlit Background Bot စတင်နေပါပြီ...")
    
    while True:
        current_videos = get_videos_from_feed()
        for video in current_videos:
            video_url = video['url']
            video_title = video['title']
            thumb_url = video['thumb_url']
            
            # txt ဖိုင်အစား Channel ထဲမှာ တိုက်ရိုက်စစ်ဆေးခြင်း
            already_sent = await is_already_sent(video_title)
            
            if not already_sent:
                print(f"ဗီဒီယိုအသစ် တွေ့ရှိသည်: {video_title}")
                file_path, duration = download_video(video_url)
                thumb_path = download_thumbnail(thumb_url)
                
                if file_path and os.path.exists(file_path):
                    try:
                        telegram_caption = f"🎬 **{video_title}**"
                        await client.send_file(
                            MY_CHANNEL, 
                            file_path, 
                            caption=telegram_caption,
                            thumb=thumb_path,
                            duration=duration,          
                            supports_streaming=True    
                        )
                        print("Telegram ပေါ်သို့ တင်ပြီးပါပြီ။")
                    except Exception as upload_error:
                        print(f"Telegram ပေါ်သို့ တင်ရာတွင် အမှားရှိသည်: {upload_error}")
                    finally:
                        if os.path.exists(file_path):
                            os.remove(file_path)
                        if thumb_path and os.path.exists(thumb_path):
                            os.remove(thumb_path)
                await asyncio.sleep(5)
                
        print("Feed အား ထပ်မံစစ်ဆေးရန် စောင့်ဆိုင်းနေပါသည်...")
        await asyncio.sleep(300)

if __name__ == '__main__':
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_bot_process())
    except Exception as e:
        st.error(f"Bot တွင် အမှားတစ်ခုတက်သွားပါသည်: {e}")
