from database import get_db
from datetime import datetime
import feedparser
import sqlite3
import logging

logger = logging.getLogger(__name__)

class Folder:
    @staticmethod
    def get_all():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM folders ORDER BY name')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def create(name):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO folders (name) VALUES (?)', (name,))
            return cursor.lastrowid
    
    @staticmethod
    def update(folder_id, name):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE folders SET name = ? WHERE id = ?', (name, folder_id))
    
    @staticmethod
    def delete(folder_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM folders WHERE id = ?', (folder_id,))

class Feed:
    @staticmethod
    def get_all():
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT f.*, 
                       fo.name as folder_name,
                       COUNT(CASE WHEN a.read = 0 THEN 1 END) as unread_count
                FROM feeds f
                LEFT JOIN folders fo ON f.folder_id = fo.id
                LEFT JOIN articles a ON f.id = a.feed_id
                WHERE f.deleted = 0
                GROUP BY f.id
                ORDER BY f.title
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_by_id(feed_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM feeds WHERE id = ?', (feed_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def create(url, folder_id=None):
        logger.info(f"Creating new feed: {url}")
        # Parse feed to get metadata
        feed_data = feedparser.parse(url)
        
        if feed_data.bozo and not feed_data.entries:
            logger.error(f"Invalid feed URL: {url} - {feed_data.bozo_exception}")
            raise ValueError(f'Invalid feed: {feed_data.bozo_exception}')
        
        title = feed_data.feed.get('title', 'Untitled Feed')
        description = feed_data.feed.get('description', feed_data.feed.get('subtitle', ''))
        link = feed_data.feed.get('link', '')
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO feeds (url, title, description, link, folder_id, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (url, title, description, link, folder_id, datetime.now()))
            feed_id = cursor.lastrowid
        
        logger.info(f"Feed created: {title} (ID: {feed_id})")
        
        # Fetch initial articles
        Article.fetch_for_feed(feed_id, url)
        
        return feed_id
    
    @staticmethod
    def update(feed_id, title=None, folder_id=None):
        logger.debug(f"Updating feed {feed_id}")
        with get_db() as conn:
            cursor = conn.cursor()
            if title is not None:
                cursor.execute('UPDATE feeds SET title = ? WHERE id = ?', (title, feed_id))
            if folder_id is not None:
                cursor.execute('UPDATE feeds SET folder_id = ? WHERE id = ?', (folder_id, feed_id))
    
    @staticmethod
    def delete(feed_id):
        """Soft delete a feed"""
        logger.info(f"Soft deleting feed: {feed_id}")
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE feeds SET deleted = 1 WHERE id = ?', (feed_id,))
        logger.info(f"Feed {feed_id} marked as deleted")
    
    @staticmethod
    def refresh(feed_id):
        logger.info(f"Refreshing feed: {feed_id}")
        feed = Feed.get_by_id(feed_id)
        if not feed:
            logger.warning(f"Feed {feed_id} not found for refresh")
            return
        
        Article.fetch_for_feed(feed_id, feed['url'])
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE feeds SET last_updated = ? WHERE id = ?', 
                         (datetime.now(), feed_id))
        
        logger.info(f"Feed {feed_id} refreshed successfully")

class Article:
    @staticmethod
    def get_all(feed_id=None, read=None, starred=None, search=None, limit=100):
        with get_db() as conn:
            cursor = conn.cursor()
            
            query = 'SELECT a.*, f.title as feed_title FROM articles a JOIN feeds f ON a.feed_id = f.id WHERE 1=1'
            params = []
            
            if feed_id is not None:
                query += ' AND a.feed_id = ?'
                params.append(feed_id)
            
            if read is not None:
                query += ' AND a.read = ?'
                params.append(1 if read else 0)
            
            if starred is not None:
                query += ' AND a.starred = ?'
                params.append(1 if starred else 0)
            
            if search:
                query += ' AND (a.title LIKE ? OR a.description LIKE ?)'
                search_term = f'%{search}%'
                params.extend([search_term, search_term])
            
            query += ' ORDER BY a.published DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    @staticmethod
    def get_by_id(article_id):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def mark_read(article_id, read=True):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE articles SET read = ? WHERE id = ?', 
                         (1 if read else 0, article_id))
    
    @staticmethod
    def mark_starred(article_id, starred=True):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE articles SET starred = ? WHERE id = ?', 
                         (1 if starred else 0, article_id))
    
    @staticmethod
    def mark_all_read(feed_id=None):
        with get_db() as conn:
            cursor = conn.cursor()
            if feed_id:
                cursor.execute('UPDATE articles SET read = 1 WHERE feed_id = ?', (feed_id,))
            else:
                cursor.execute('UPDATE articles SET read = 1')
    
    @staticmethod
    def fetch_for_feed(feed_id, feed_url):
        """Fetch articles from a feed - deletes old and inserts fresh"""
        logger.info(f"Fetching articles for feed {feed_id} from {feed_url}")
        feed_data = feedparser.parse(feed_url)
        
        if feed_data.bozo and not feed_data.entries:
            logger.warning(f"Feed parsing failed for {feed_url}: {feed_data.bozo_exception if hasattr(feed_data, 'bozo_exception') else 'Unknown error'}")
            return
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Delete all existing articles for this feed
            cursor.execute('DELETE FROM articles WHERE feed_id = ?', (feed_id,))
            deleted_count = cursor.rowcount
            logger.debug(f"Deleted {deleted_count} old articles for feed {feed_id}")
            
            # Insert all articles fresh
            inserted_count = 0
            for entry in feed_data.entries:
                guid = entry.get('id', entry.get('link', ''))
                title = entry.get('title', 'Untitled')
                link = entry.get('link', '')
                description = entry.get('description', entry.get('summary', ''))
                author = entry.get('author', '')
                
                # Parse published date
                published = None
                if 'published_parsed' in entry and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                elif 'updated_parsed' in entry and entry.updated_parsed:
                    try:
                        published = datetime(*entry.updated_parsed[:6])
                    except:
                        pass
                
                # Insert article
                cursor.execute('''
                    INSERT INTO articles (feed_id, guid, title, link, description, author, published)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (feed_id, guid, title, link, description, author, published))
                inserted_count += 1
            
            logger.info(f"Fetched {inserted_count} articles for feed {feed_id}")
