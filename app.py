from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import feedparser
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from database import init_db, add_default_feeds
from models import Feed, Article, Folder

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)

from functools import wraps

# Auth Configuration
ADMIN_TOKEN = os.environ.get('ADMIN_TOKEN')

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not ADMIN_TOKEN:
            return f(*args, **kwargs) # No auth configured, allow all
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid token'}), 401
        
        token = auth_header.split(' ')[1]
        if token != ADMIN_TOKEN:
            return jsonify({'error': 'Invalid token'}), 401
            
        return f(*args, **kwargs)
    return decorated

# Initialize database
logger.info("Initializing database...")
init_db()
add_default_feeds()
logger.info("Application initialized successfully")

# ===== Static Files =====
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

# ===== Feed Management =====
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        'auth_required': bool(ADMIN_TOKEN)
    })

@app.route('/api/auth/verify', methods=['POST'])
@require_auth
def verify_token():
    """Verify if the provided token is valid"""
    return jsonify({'valid': True})

@app.route('/api/feeds', methods=['GET'])
def get_feeds():
    """Get all subscribed feeds"""
    feeds = Feed.get_all()
    return jsonify(feeds)

@app.route('/api/feeds', methods=['POST'])
@require_auth
def add_feed():
    """Subscribe to a new feed"""
    try:
        data = request.get_json()
        url = data.get('url')
        folder_id = data.get('folder_id')
        
        if not url:
            return jsonify({'error': 'URL is required'}), 400
        
        feed_id = Feed.create(url, folder_id)
        return jsonify({'id': feed_id, 'message': 'Feed added successfully'})
    
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'Failed to add feed: {str(e)}'}), 500

@app.route('/api/feeds/<int:feed_id>', methods=['DELETE'])
@require_auth
def delete_feed(feed_id):
    """Unsubscribe from a feed"""
    try:
        Feed.delete(feed_id)
        return jsonify({'message': 'Feed deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feeds/<int:feed_id>/refresh', methods=['POST'])
@require_auth
def refresh_feed(feed_id):
    """Manually refresh a feed"""
    try:
        Feed.refresh(feed_id)
        return jsonify({'message': 'Feed refreshed successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== Article Management =====
@app.route('/api/articles', methods=['GET'])
def get_articles():
    """Get articles with optional filters"""
    try:
        feed_id = request.args.get('feed_id', type=int)
        read = request.args.get('read', type=lambda x: x.lower() == 'true' if x else None)
        starred = request.args.get('starred', type=lambda x: x.lower() == 'true' if x else None)
        search = request.args.get('search')
        limit = request.args.get('limit', default=100, type=int)
        
        articles = Article.get_all(
            feed_id=feed_id,
            read=read,
            starred=starred,
            search=search,
            limit=limit
        )
        return jsonify(articles)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500







if __name__ == '__main__':
    # Use environment variable for debug mode, default to False for safety
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode, port=5002, host="0.0.0.0")
