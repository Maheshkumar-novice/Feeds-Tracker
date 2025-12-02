from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import feedparser
import os
import logging
from datetime import datetime

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

# ===== Legacy Parse Feed Endpoint =====
@app.route('/api/parse-feed', methods=['POST'])
def parse_feed():
    """Legacy endpoint for parsing a feed (kept for compatibility)"""
    try:
        data = request.get_json()
        feed_url = data.get('url')
        
        if not feed_url:
            return jsonify({'error': 'Feed URL is required'}), 400
        
        feed = feedparser.parse(feed_url)
        
        if feed.bozo and not feed.entries:
            error_msg = str(feed.bozo_exception) if hasattr(feed, 'bozo_exception') else 'Invalid feed format'
            return jsonify({'error': f'Failed to parse feed: {error_msg}'}), 400
        
        feed_info = {
            'title': feed.feed.get('title', 'Untitled Feed'),
            'description': feed.feed.get('description', feed.feed.get('subtitle', '')),
            'link': feed.feed.get('link', ''),
            'updated': feed.feed.get('updated', ''),
        }
        
        entries = []
        for entry in feed.entries[:50]:
            entries.append({
                'title': entry.get('title', 'Untitled'),
                'link': entry.get('link', ''),
                'description': entry.get('description', entry.get('summary', '')),
                'published': entry.get('published', entry.get('updated', '')),
                'author': entry.get('author', ''),
            })
        
        return jsonify({
            'feed': feed_info,
            'entries': entries
        })
    
    except Exception as e:
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

# ===== Feed Management =====
@app.route('/api/feeds', methods=['GET'])
def get_feeds():
    """Get all subscribed feeds"""
    try:
        feeds = Feed.get_all()
        return jsonify(feeds)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feeds', methods=['POST'])
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

@app.route('/api/feeds/<int:feed_id>', methods=['PUT'])
def update_feed(feed_id):
    """Update feed details"""
    try:
        data = request.get_json()
        title = data.get('title')
        folder_id = data.get('folder_id')
        
        Feed.update(feed_id, title=title, folder_id=folder_id)
        return jsonify({'message': 'Feed updated successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feeds/<int:feed_id>', methods=['DELETE'])
def delete_feed(feed_id):
    """Unsubscribe from a feed"""
    try:
        Feed.delete(feed_id)
        return jsonify({'message': 'Feed deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/feeds/<int:feed_id>/refresh', methods=['POST'])
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

@app.route('/api/articles/<int:article_id>', methods=['GET'])
def get_article(article_id):
    """Get a single article"""
    try:
        article = Article.get_by_id(article_id)
        if not article:
            return jsonify({'error': 'Article not found'}), 404
        return jsonify(article)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles/<int:article_id>/read', methods=['PUT'])
def mark_article_read(article_id):
    """Mark article as read/unread"""
    try:
        data = request.get_json()
        read = data.get('read', True)
        Article.mark_read(article_id, read)
        return jsonify({'message': 'Article updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles/<int:article_id>/star', methods=['PUT'])
def mark_article_starred(article_id):
    """Star/unstar an article"""
    try:
        data = request.get_json()
        starred = data.get('starred', True)
        Article.mark_starred(article_id, starred)
        return jsonify({'message': 'Article updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/articles/mark-all-read', methods=['POST'])
def mark_all_read():
    """Mark all articles as read (optionally for a specific feed)"""
    try:
        data = request.get_json() or {}
        feed_id = data.get('feed_id')
        Article.mark_all_read(feed_id)
        return jsonify({'message': 'Articles marked as read'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== Folder Management =====
@app.route('/api/folders', methods=['GET'])
def get_folders():
    """Get all folders"""
    try:
        folders = Folder.get_all()
        return jsonify(folders)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders', methods=['POST'])
def create_folder():
    """Create a new folder"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Folder name is required'}), 400
        
        folder_id = Folder.create(name)
        return jsonify({'id': folder_id, 'message': 'Folder created successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders/<int:folder_id>', methods=['PUT'])
def update_folder(folder_id):
    """Rename a folder"""
    try:
        data = request.get_json()
        name = data.get('name')
        
        if not name:
            return jsonify({'error': 'Folder name is required'}), 400
        
        Folder.update(folder_id, name)
        return jsonify({'message': 'Folder updated successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders/<int:folder_id>', methods=['DELETE'])
def delete_folder(folder_id):
    """Delete a folder"""
    try:
        Folder.delete(folder_id)
        return jsonify({'message': 'Folder deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== OPML Import/Export =====
@app.route('/api/opml/export', methods=['GET'])
def export_opml():
    """Export feeds as OPML"""
    try:
        feeds = Feed.get_all()
        
        opml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        opml += '<opml version="2.0">\n'
        opml += '  <head>\n'
        opml += f'    <title>RSS Reader Export</title>\n'
        opml += f'    <dateCreated>{datetime.now().isoformat()}</dateCreated>\n'
        opml += '  </head>\n'
        opml += '  <body>\n'
        
        # Group by folder
        folders = {}
        for feed in feeds:
            folder_name = feed.get('folder_name') or 'Uncategorized'
            if folder_name not in folders:
                folders[folder_name] = []
            folders[folder_name].append(feed)
        
        for folder_name, folder_feeds in folders.items():
            opml += f'    <outline text="{folder_name}" title="{folder_name}">\n'
            for feed in folder_feeds:
                opml += f'      <outline type="rss" text="{feed["title"]}" title="{feed["title"]}" xmlUrl="{feed["url"]}" htmlUrl="{feed["link"]}"/>\n'
            opml += '    </outline>\n'
        
        opml += '  </body>\n'
        opml += '</opml>'
        
        return opml, 200, {'Content-Type': 'application/xml', 'Content-Disposition': 'attachment; filename=feeds.opml'}
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/opml/import', methods=['POST'])
def import_opml():
    """Import feeds from OPML"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.opml'):
            return jsonify({'error': 'File must be an OPML file'}), 400
        
        import xml.etree.ElementTree as ET
        tree = ET.parse(file)
        root = tree.getroot()
        
        imported = 0
        errors = []
        
        # Find all outline elements with xmlUrl (actual feeds)
        for outline in root.findall('.//outline[@xmlUrl]'):
            url = outline.get('xmlUrl')
            
            try:
                Feed.create(url)
                imported += 1
            except Exception as e:
                errors.append(f"{url}: {str(e)}")
        
        return jsonify({
            'message': f'Imported {imported} feeds',
            'imported': imported,
            'errors': errors
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000, host="0.0.0.0")
