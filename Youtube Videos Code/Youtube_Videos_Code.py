## FINAL

import csv
import time
import html
import re
import pandas as pd
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
from datetime import datetime, timedelta
from langdetect import detect, LangDetectException
import sys
sys.stdout.reconfigure(encoding='utf-8')

def clean_text(text):
    """
    Clean text by removing special characters, extra whitespace, and HTML entities.
    """
    text = html.unescape(text)  # Decode HTML entities
    text = re.sub(r'http\S+|www\.\S+', '', text)  # Remove URLs
    text = re.sub(r'[^\w\s.,!?-]', ' ', text)  # Remove special characters
    text = ' '.join(text.split())  # Remove extra whitespace
    return text.strip()

def get_keywords_from_excel(file_path):
    df = pd.read_excel(file_path)
    keywords = df['Product'].tolist()
    #keywords =['Babyzen YOYO2 Stroller']

    # Remove duplicates and append " Stroller"
    keywords = list(set(keyword + " Stroller" for keyword in keywords))

    return keywords

def get_youtube_videos(api_key, keywords, max_results=5, min_views=100, min_likes=50):
    

    def is_english(text):
        """Check if text is in English"""
        if not text or len(text.strip()) < 10:  # Skip very short texts
            return False
        try:
            return detect(text) == 'en'
        except LangDetectException:
            return False  # If detection fails, assume it's not English

    try:
        youtube = build('youtube', 'v3', developerKey=api_key)
    except Exception as e:
        print(f"Error building YouTube service: {str(e)}")
        return []

    video_details = []

    # Get the current date and calculate 30 days ago
    current_date = datetime.utcnow()
    thirty_days_ago = current_date - timedelta(days=30)
    published_after = thirty_days_ago.isoformat("T") + "Z"  # Convert to ISO 8601 format

    for keyword in keywords:
        print(f"Searching for: {keyword}...")
        keyword_videos = []  # Reset for each keyword
        seen_video_ids = set()  # Track IDs to avoid duplicates

        # First try: Search recent videos (last 30 days)
        try:
            # Try recent videos first
            print(f"Searching for recent videos (last 30 days) for: {keyword}")
            next_page_token = None
            recent_search_attempts = 0
            max_recent_attempts = 3  # Limit to prevent excessive API usage
            
            while len(keyword_videos) < max_results and recent_search_attempts < max_recent_attempts:
                request = youtube.search().list(
                    q=keyword,
                    part='snippet',
                    maxResults=50,  # Fetch more results at once
                    type='video',
                    order='relevance',
                    publishedAfter=published_after,
                    pageToken=next_page_token
                )
                response = request.execute()
                time.sleep(1)
                recent_search_attempts += 1
                
                if 'items' not in response or not response['items']:
                    print("No (more) recent videos found, moving to older videos.")
                    break
                
                # Get IDs for videos we haven't seen yet
                new_video_ids = []
                for item in response['items']:
                    vid_id = item['id']['videoId']
                    if vid_id not in seen_video_ids:
                        new_video_ids.append(vid_id)
                        seen_video_ids.add(vid_id)
                
                if not new_video_ids:
                    print("No new videos found in this page.")
                    break
                
                # Batch fetch video details
                video_stats_request = youtube.videos().list(
                    part="snippet,statistics,topicDetails",
                    id=",".join(new_video_ids)
                )
                video_stats_response = video_stats_request.execute()
                time.sleep(1)
                
                # Process video details
                for item in video_stats_response['items']:
                    vid_id = item['id']
                    
                    title = item['snippet']['title']
                    description = item['snippet'].get('description', '')
                    
                    # Check if title and description are in English
                    title_is_english = is_english(title)
                    desc_is_english = is_english(description)
                    
                    if not (title_is_english and desc_is_english):
                        print(f"Skipping non-English video: {title}")
                        continue
                    
                    stats = item.get('statistics', {})
                    topics = item.get('topicDetails', {}).get('topicCategories', [])
                    
                    views = int(stats.get('viewCount', 0))
                    likes = int(stats.get('likeCount', 0))
                    lang = item['snippet'].get('defaultAudioLanguage', '')
                    
                    if views >= min_views and likes >= min_likes:
                        video_data = {
                            'keyword': keyword,
                            'title': title,
                            'description': description,
                            'videoId': vid_id,
                            'url': f"https://www.youtube.com/watch?v={vid_id}",
                            'views': views,
                            'likes': likes,
                            'published_date': item['snippet']['publishedAt'],
                            'language': lang,
                            'title_language': 'en',
                            'description_language': 'en'
                        }
                        keyword_videos.append(video_data)
                        print(f"Added English video: {title}")
                    
                    if len(keyword_videos) >= max_results:
                        break
                
                # Check if we need to fetch more pages
                next_page_token = response.get('nextPageToken')
                if not next_page_token or len(keyword_videos) >= max_results:
                    break
            
            # If we still don't have enough videos, search older videos
            if len(keyword_videos) < max_results:
                remaining_slots = max_results - len(keyword_videos)
                print(f"Only found {len(keyword_videos)} recent English videos for '{keyword}'. Searching for older videos...")
                
                next_page_token = None
                older_search_attempts = 0
                max_older_attempts = 5  # More attempts for older videos 
                
                while len(keyword_videos) < max_results and older_search_attempts < max_older_attempts:
                    request = youtube.search().list(
                        q=keyword,
                        part='snippet',
                        maxResults=50,
                        type='video',
                        order='relevance',
                        pageToken=next_page_token
                        # No date filter for this search
                    )
                    response = request.execute()
                    time.sleep(1)
                    older_search_attempts += 1
                    
                    if 'items' not in response or not response['items']:
                        print("No (more) older videos found.")
                        break
                    
                    # Get IDs for videos not seen yet
                    new_video_ids = []
                    for item in response['items']:
                        vid_id = item['id']['videoId']
                        if vid_id not in seen_video_ids:
                            new_video_ids.append(vid_id)
                            seen_video_ids.add(vid_id)
                    
                    if not new_video_ids:
                        print("No new videos found in this page.")
                        break
                    
                    # Batch fetch video details
                    video_stats_request = youtube.videos().list(
                        part="snippet,statistics,topicDetails",
                        id=",".join(new_video_ids)
                    )
                    video_stats_response = video_stats_request.execute()
                    time.sleep(1)
                    
                    # Process video details
                    for item in video_stats_response['items']:
                        vid_id = item['id']
                        
                        title = item['snippet']['title']
                        description = item['snippet'].get('description', '')
                        
                        # Check if title and description are in English
                        title_is_english = is_english(title)
                        desc_is_english = is_english(description)
                        
                        if not (title_is_english and desc_is_english):
                            print(f"Skipping non-English video: {title}")
                            continue
                        
                        stats = item.get('statistics', {})
                        topics = item.get('topicDetails', {}).get('topicCategories', [])
                        
                        views = int(stats.get('viewCount', 0))
                        likes = int(stats.get('likeCount', 0))
                        lang = item['snippet'].get('defaultAudioLanguage', '')
                        
                        if views >= min_views and likes >= min_likes:
                            video_data = {
                                'keyword': keyword,
                                'title': title,
                                'description': description,
                                'videoId': vid_id,
                                'url': f"https://www.youtube.com/watch?v={vid_id}",
                                'views': views,
                                'likes': likes,
                                'published_date': item['snippet']['publishedAt'],
                                'language': lang,
                                'title_language': 'en',
                                'description_language': 'en'
                            }
                            keyword_videos.append(video_data)
                            print(f"Added English video: {title}")
                        
                        if len(keyword_videos) >= max_results:
                            break
                    
                    
                    next_page_token = response.get('nextPageToken')
                    if not next_page_token or len(keyword_videos) >= max_results:
                        break
            
            print(f"Found {len(keyword_videos)}/{max_results} English videos for keyword: {keyword}")
            video_details.extend(keyword_videos)

        except Exception as e:
            print(f"Error processing keyword '{keyword}': {str(e)}")
            continue

    print(f"Total English videos collected: {len(video_details)}")
    return video_details

def get_transcripts(video_ids):
    transcripts = {}
    for video_id in video_ids:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([t['text'] for t in transcript])
            transcripts[video_id] = transcript_text
        except Exception as e:
            print(f"Transcript error for video {video_id}: {str(e)}")
            transcripts[video_id] = "Transcript not available"

        time.sleep(0.5)  

    return transcripts

def clean_video_data(videos, transcripts):
    """
    Clean all collected data at once.

    """
    cleaned_videos = []
    for video in videos:
        cleaned_video = {
            'keyword': clean_text(video['keyword']),
            'title': clean_text(video['title']),
            'description': clean_text(video['description']),
            'videoId': video['videoId'],
            'url': video['url'],
            'views': video['views'],
            'likes': video['likes'],
            'published_date': video['published_date'],
            'transcript': clean_text(transcripts.get(video['videoId'], "Transcript not available"))
        }
        cleaned_videos.append(cleaned_video)
    return cleaned_videos

def save_to_csv(data, filename):
    """
    Save data to a CSV file.

    """
    try:
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        print(f"Data successfully saved to {filename}")
    except Exception as e:
        print(f"Error saving data to CSV: {str(e)}")


if __name__ == "__main__":
    api_key = "my_api_key"
    keywords_file = "Stroller Keywords.xlsx"
    keywords = get_keywords_from_excel(keywords_file)
    #keywords =['Babyzen YOYO2 Stroller']
    

    print("Collecting video data...")
    videos = get_youtube_videos(api_key, keywords)

    print("Collecting transcripts...")
    video_ids = [video['videoId'] for video in videos]
    transcripts = get_transcripts(video_ids)

    print("Cleaning collected data...")
    cleaned_videos = clean_video_data(videos, transcripts)

    print("Saving cleaned data to CSV...")
    save_to_csv(cleaned_videos, "youtube_videos_filtered.csv")
    print("Data saved to youtube_videos_filtered.csv")
