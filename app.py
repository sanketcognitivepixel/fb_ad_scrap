from flask import Flask, jsonify, request
from celery import Celery
import os
import platform
import json
from datetime import datetime
from main import scrape_facebook_ads
from celery_config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_USERNAME,
    REDIS_PASSWORD,
    broker_url,
    result_backend
)
import redis
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Create output directory if it doesn't exist
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Celery configuration with Redis Cloud settings
app.config['CELERY_BROKER_URL'] = f'redis://default:rJ6H8vLmMhJ9b304Nq85k3oBsEdl8Njj@redis-13971.c246.us-east-1-4.ec2.redns.redis-cloud.com:13971'
app.config['CELERY_RESULT_BACKEND'] = f'redis://default:rJ6H8vLmMhJ9b304Nq85k3oBsEdl8Njj@redis-13971.c246.us-east-1-4.ec2.redns.redis-cloud.com:13971'

# Initialize Celery with Windows-specific settings if needed
celery = Celery(
    app.name,
    broker=app.config['CELERY_BROKER_URL'],
    backend=app.config['CELERY_RESULT_BACKEND']
)

# Load the Celery config
celery.conf.update(
    broker_connection_retry_on_startup=True,
    worker_pool_restarts=True,
    worker_pool='solo' if platform.system() == 'Windows' else 'prefork'
)

# Test Redis connection on startup
def test_redis_connection():
    try:
        # Create Redis client with configuration matching the working C# example
        redis_client = redis.Redis(
            host='redis-10575.c14.us-east-1-3.ec2.redns.redis-cloud.com',
            port=10575,
            decode_responses=True,
            username="default",
            password="jXXK6aQaaYmfEMSfXWwQx8hXmJOQ7tS1",
        )
        
        # Test connection by setting and getting a value
        test_key = "foo"
        test_value = "bar"
        redis_client.set(test_key, test_value)
        result = redis_client.get(test_key)
        
        if result == test_value:
            logger.info("✅ Redis connection test successful!")
            logger.info(f"Test value retrieved successfully: {result}")
        else:
            logger.error("❌ Redis connection test failed - Value mismatch")
            
        # Clean up test key
        redis_client.delete(test_key)
        
    except Exception as e:
        logger.error(f"❌ Redis connection test failed: {str(e)}")
        logger.error("Make sure your Redis Cloud credentials and SSL settings are correct")
        raise

# Run Redis connection test when app starts
test_redis_connection()

@app.route('/')
def index():
    return 'Hello from Render!'

@celery.task(bind=True)
def scrape_task(self, url, output_file=None, headless=True):
    """
    Celery task to run the Facebook Ads scraping
    """
    try:
        # Update task state to started
        self.update_state(state='STARTED', meta={'status': 'Task is running...'})
        
        # Generate default output file name if none provided
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(OUTPUT_DIR, f'ads_data_{timestamp}.json')
        elif not os.path.isabs(output_file):
            # If relative path is provided, make it relative to OUTPUT_DIR
            output_file = os.path.join(OUTPUT_DIR, output_file)
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Run the scraping function
        result = scrape_facebook_ads(
            url=url,
            output_file=output_file,  # Now we always pass an output file
            headless=headless
        )
        
        # Double-check file creation
        if not os.path.exists(output_file):
            # If file wasn't created by scrape_facebook_ads, create it here
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving JSON file: {str(e)}")
        
        return {
            'status': 'SUCCESS',
            'data': result,
            'output_file': output_file
        }
    except Exception as e:
        # Update task state to failed
        error_msg = str(e)
        self.update_state(state='FAILURE', meta={'error': error_msg})
        print(f"Task failed: {error_msg}")
        raise

@app.route('/scrape', methods=['POST'])
def scrape_ads():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
            
        # Optional parameters
        output_file = data.get('output_file')
        headless = data.get('headless', True)
        
        # Launch Celery task
        task = scrape_task.delay(url, output_file, headless)
        
        return jsonify({
            'task_id': task.id,
            'status': 'Task started',
            'status_url': f'/status/{task.id}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status/<task_id>')
def get_task_status(task_id):
    """
    Get the status of a running task
    """
    task = scrape_task.AsyncResult(task_id)
    
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': 'Task is pending...'
        }
    elif task.state == 'STARTED':
        response = {
            'state': task.state,
            'status': 'Task is in progress...',
            'info': task.info
        }
    elif task.state == 'FAILURE':
        response = {
            'state': task.state,
            'status': 'Task failed',
            'error': str(task.info.get('error', str(task.info)))
        }
    elif task.state == 'SUCCESS':
        response = {
            'state': task.state,
            'status': 'Task completed successfully',
            'result': task.info,
            'output_file': task.info.get('output_file') if task.info else None
        }
    else:
        response = {
            'state': task.state,
            'status': 'Task is in progress...',
            'info': task.info
        }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
