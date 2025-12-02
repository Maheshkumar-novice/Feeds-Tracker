import sqlite3
import logging
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)
DATABASE_PATH = 'rss_reader.db'

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def add_default_feeds():
    """Add default feeds if database is empty"""
    from models import Feed
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM feeds WHERE deleted = 0')
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("No feeds found, adding default feeds...")
            default_feeds = [
                'https://jvns.ca/atom.xml',
                'https://simonwillison.net/atom/everything/',
                'https://lucumr.pocoo.org/feed.atom',
                'https://samwho.dev/rss.xml',
                'https://blog.miguelgrinberg.com/feed',
                'https://world.hey.com/dhh/feed.atom',
                'https://herman.bearblog.dev/feed/',
                'https://harper.blog/index.xml'
            ]
            
            success_count = 0
            for url in default_feeds:
                try:
                    Feed.create(url)
                    logger.info(f"Added default feed: {url}")
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to add default feed {url}: {e}")
            
            logger.info(f"Default feeds initialization complete: {success_count}/{len(default_feeds)} added")

def init_db():
    """Initialize the database with schema"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Create folders table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            )
        ''')
        
        # Create feeds table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                description TEXT,
                link TEXT,
                folder_id INTEGER,
                last_updated TIMESTAMP,
                deleted INTEGER DEFAULT 0,
                FOREIGN KEY (folder_id) REFERENCES folders(id) ON DELETE SET NULL
            )
        ''')
        
        # Create articles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                guid TEXT NOT NULL,
                title TEXT,
                link TEXT,
                description TEXT,
                author TEXT,
                published TIMESTAMP,
                read BOOLEAN DEFAULT 0,
                starred BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES feeds(id) ON DELETE CASCADE,
                UNIQUE(feed_id, guid)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles(feed_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_read ON articles(read)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_starred ON articles(starred)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(published DESC)')
        
        conn.commit()
