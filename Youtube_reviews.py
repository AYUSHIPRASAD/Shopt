import csv
#from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import pandas as pd

def get_keywords_from_excel(file_path):
    df = pd.read_excel(r"C:\Users\ayush\OneDrive\Desktop\Shopt\Codes\Stroller Keywords.xlsx")
    return df['Item'].tolist()

def get_youtube_videos(api_key, keywords, max_results=25):
    youtube = build('youtube', 'v3', developerKey=api_key)

    video_details = []
    for keyword in keywords:
        request = youtube.search().list(
            q=keyword,
            part='snippet',
            maxResults=max_results,
            type='video',
            order='relevance'
        )
        response = request.execute()

        for item in response['items']:
            video_data = {
                'keyword': keyword,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'videoId': item['id']['videoId'],
                'url': f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            }
            video_details.append(video_data)

    return video_details

def get_transcripts(video_ids):
    transcripts = {}
    for video_id in video_ids:
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([t['text'] for t in transcript])
            transcripts[video_id] = transcript_text
        except Exception as e:
            transcripts[video_id] = f"Transcript not available: {str(e)}"
    return transcripts

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)

if __name__ == "__main__":
    api_key = "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
    keywords_file = "keywords.xlsx"
    keywords = get_keywords_from_excel(keywords_file)

    videos = get_youtube_videos(api_key, keywords)

    video_ids = [video['videoId'] for video in videos]
    transcripts = get_transcripts(video_ids)

    for video in videos:
        video['transcript'] = transcripts.get(video['videoId'], "Transcript not available")

    save_to_csv(videos, "youtube_videos.csv")
    print("Data saved to youtube_videos.csv")
