import os
from datetime import datetime, timedelta
import json
import time
from typing import List, Dict
import requests
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger

class InstagramStoryScheduler:
    def __init__(self):
        load_dotenv()
        self.access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.instagram_account_id = os.getenv('INSTAGRAM_ACCOUNT_ID')
        self.base_url = "https://graph.facebook.com/v18.0"
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        self.scheduled_stories = []
        self.load_scheduled_stories()

    def load_scheduled_stories(self) -> None:
        """Load previously scheduled stories from JSON file"""
        try:
            with open('scheduled_stories.json', 'r') as f:
                self.scheduled_stories = json.load(f)
        except FileNotFoundError:
            self.scheduled_stories = []

    def save_scheduled_stories(self) -> None:
        """Save scheduled stories to JSON file"""
        with open('scheduled_stories.json', 'w') as f:
            json.dump(self.scheduled_stories, f)

    def schedule_story(self, media_path: str, scheduled_time: datetime, caption: str = "") -> Dict:
        """Schedule a story for future posting"""
        if not os.path.exists(media_path):
            raise FileNotFoundError("Media file not found")

        story_data = {
            'id': len(self.scheduled_stories) + 1,
            'media_path': media_path,
            'scheduled_time': scheduled_time.isoformat(),
            'caption': caption,
            'status': 'scheduled'
        }

        self.scheduled_stories.append(story_data)
        self.save_scheduled_stories()

        # Schedule the job
        self.scheduler.add_job(
            func=self.post_story,
            trigger=DateTrigger(run_date=scheduled_time),
            args=[story_data],
            id=str(story_data['id'])
        )

        return story_data

    def post_story(self, story_data: Dict) -> None:
        """Post the story to Instagram"""
        try:
            # First, upload the media file
            media_response = self.upload_media(story_data['media_path'])
            
            if media_response.get('id'):
                # Create the story using the uploaded media
                story_url = f"{self.base_url}/{self.instagram_account_id}/stories"
                params = {
                    'access_token': self.access_token,
                    'media_type': 'STORY',
                    'media_id': media_response['id']
                }
                
                if story_data['caption']:
                    params['caption'] = story_data['caption']

                response = requests.post(story_url, params=params)
                response.raise_for_status()

                # Update story status
                story_data['status'] = 'posted'
                self.save_scheduled_stories()
                
        except Exception as e:
            story_data['status'] = 'failed'
            story_data['error'] = str(e)
            self.save_scheduled_stories()
            raise

    def upload_media(self, media_path: str) -> Dict:
        """Upload media file to Instagram"""
        media_url = f"{self.base_url}/{self.instagram_account_id}/media"
        
        with open(media_path, 'rb') as media_file:
            files = {
                'file': media_file
            }
            params = {
                'access_token': self.access_token,
                'media_type': 'STORY'
            }
            
            response = requests.post(media_url, params=params, files=files)
            response.raise_for_status()
            return response.json()

    def get_scheduled_stories(self) -> List[Dict]:
        """Get list of all scheduled stories"""
        return self.scheduled_stories

    def cancel_scheduled_story(self, story_id: int) -> bool:
        """Cancel a scheduled story"""
        for story in self.scheduled_stories:
            if story['id'] == story_id and story['status'] == 'scheduled':
                story['status'] = 'cancelled'
                self.scheduler.remove_job(str(story_id))
                self.save_scheduled_stories()
                return True
        return False

    def modify_scheduled_story(self, story_id: int, new_time: datetime = None, 
                             new_caption: str = None) -> Dict:
        """Modify a scheduled story"""
        for story in self.scheduled_stories:
            if story['id'] == story_id and story['status'] == 'scheduled':
                if new_time:
                    story['scheduled_time'] = new_time.isoformat()
                    # Reschedule the job
                    self.scheduler.reschedule_job(
                        job_id=str(story_id),
                        trigger=DateTrigger(run_date=new_time)
                    )
                
                if new_caption is not None:
                    story['caption'] = new_caption
                
                self.save_scheduled_stories()
                return story
        
        raise ValueError("Story not found or already posted/cancelled")

def main():
    """Example usage of the Instagram Story Scheduler"""
    scheduler = InstagramStoryScheduler()
    
    # Schedule a story
    story_data = scheduler.schedule_story(
        media_path="/media.jpg",
        scheduled_time=datetime.now() + timedelta(hours=1),
        caption="Check out our new product launch! #newproduct"
    )
    print(f"Scheduled story: {story_data}")
    
    # Get all scheduled stories
    scheduled_stories = scheduler.get_scheduled_stories()
    print(f"All scheduled stories: {scheduled_stories}")
    
    # Modify a scheduled story
    modified_story = scheduler.modify_scheduled_story(
        story_id=story_data['id'],
        new_time=datetime.now() + timedelta(hours=2),
        new_caption="Updated caption for our product launch! #newproduct"
    )
    print(f"Modified story: {modified_story}")
    
    # Cancel a scheduled story
    cancelled = scheduler.cancel_scheduled_story(story_data['id'])
    print(f"Story cancelled: {cancelled}")

if __name__ == "__main__":
    main()