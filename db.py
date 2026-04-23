# db.py
import sqlite3
import logging
from flask import g
from config import config
from datetime import datetime


def _ensure_column(conn, table_name, column_name, column_ddl):
    cursor = conn.cursor()
    cursor.execute(f'PRAGMA table_info({table_name})')
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {column_ddl}')


def _infer_flair(board, title, content):
    text = f"{title} {content}"
    if any(keyword in text for keyword in ['속보', '재난', '시위', '폭로', '논란', '갈등']):
        return '속보'
    if any(keyword in text for keyword in ['ㅋㅋ', '밈', '짤', '유머', '뻘글', '드립']):
        return '유머'
    if any(keyword in text for keyword in ['질문', '도움', '문의', '어떻게']):
        return '질문'
    if any(keyword in text for keyword in ['정보', '정리', '공유', '후기']):
        return '정보'
    if board in ['정치']:
        return '토론'
    if board in ['주식/경제']:
        return '시장'
    if board in ['과학/학문']:
        return '연구'
    if board in ['여행/문화']:
        return '후기'
    return '일반'


def _seed_post_metrics(board, title, content):
    base = 0
    hot_keywords = ['속보', '논란', '갈등', '재난', '시위', '밈', '짤', '유머', '토론']
    for keyword in hot_keywords:
        if keyword in title:
            base += 4
        if keyword in content:
            base += 2
    if board in ['정치', '주식/경제']:
        base += 3
    upvote_count = max(0, min(base + len(title) // 10, 99))
    downvote_count = 0
    view_count = max(5, upvote_count * 12 + len(content) // 20)
    return upvote_count, downvote_count, view_count

def get_db():
    """
    데이터베이스 연결을 가져오는 함수
    """
    if 'db' not in g:
        g.db = sqlite3.connect('chat_history.db')
        g.db.row_factory = sqlite3.Row  # 딕셔너리 형태로 가져오기 위해 추가
    return g.db

def close_db(error):
    """
    애플리케이션 컨텍스트 종료 시 데이터베이스 연결을 닫는 함수
    """
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    """
    데이터베이스를 초기화하는 함수
    """
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_message TEXT,
                bot_response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS community_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                board TEXT NOT NULL,
                author_name TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                source_topic TEXT,
                flair TEXT,
                upvote_count INTEGER DEFAULT 0,
                downvote_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                region_code INTEGER,
                citizen_type INTEGER,
                sumin_job TEXT,
                influence INTEGER DEFAULT 0,
                activity_freq REAL DEFAULT 0.5,
                active_start INTEGER DEFAULT 0,
                active_end INTEGER DEFAULT 23,
                status INTEGER DEFAULT 1,
                persona_json TEXT,
                batch_id TEXT,
                created_from TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_relations (
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relation_type INTEGER,
                affinity_score REAL DEFAULT 0.0,
                reason TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_id, target_id),
                FOREIGN KEY (source_id) REFERENCES agents(id),
                FOREIGN KEY (target_id) REFERENCES agents(id)
            )
        ''')
        _ensure_column(conn, 'community_posts', 'flair', 'TEXT')
        _ensure_column(conn, 'community_posts', 'upvote_count', 'INTEGER DEFAULT 0')
        _ensure_column(conn, 'community_posts', 'downvote_count', 'INTEGER DEFAULT 0')
        _ensure_column(conn, 'community_posts', 'view_count', 'INTEGER DEFAULT 0')
        conn.commit()
    except Exception as e:
        logging.error(f"데이터베이스 초기화 중 오류 발생: {e}")
    finally:
        conn.close()

def save_chat_history(user_message, bot_response):
    """
    채팅 기록을 데이터베이스에 저장하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            INSERT INTO chat_history (user_message, bot_response, timestamp)
            VALUES (?, ?, ?)
        ''', (user_message, bot_response, timestamp))
        db.commit()
    except Exception as e:
        logging.error(f"채팅 기록 저장 중 오류 발생: {e}")


def save_community_post(board, author_name, title, content, source_topic=None):
    """
    커뮤니티 게시글을 저장하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        flair = _infer_flair(board, title, content)
        upvote_count, downvote_count, view_count = _seed_post_metrics(board, title, content)
        cursor.execute(
            '''
            INSERT INTO community_posts (board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count),
        )
        db.commit()
        return cursor.lastrowid
    except Exception as e:
        logging.error(f"커뮤니티 게시글 저장 중 오류 발생: {e}")
        return None


def get_recent_community_posts(limit=30, board=None, sort='latest'):
    """
    최근 커뮤니티 게시글을 조회하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        order_clause = 'ORDER BY created_at DESC, id DESC'
        if sort == 'best':
            order_clause = 'ORDER BY upvote_count DESC, view_count DESC, created_at DESC, id DESC'
        if board:
            if board == '자유':
                query = f'''
                    SELECT id, board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count, created_at
                    FROM community_posts
                    WHERE board IN ('자유', '통합 광장')
                    {order_clause}
                    LIMIT ?
                    '''
                cursor.execute(query, (limit,))
            else:
                query = f'''
                    SELECT id, board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count, created_at
                    FROM community_posts
                    WHERE board = ?
                    {order_clause}
                    LIMIT ?
                    '''
                cursor.execute(
                    query,
                    (board, limit),
                )
        else:
            query = f'''
                SELECT id, board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count, created_at
                FROM community_posts
                {order_clause}
                LIMIT ?
                '''
            cursor.execute(
                query,
                (limit,),
            )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"커뮤니티 게시글 조회 중 오류 발생: {e}")
        return []


def save_agent(agent_id, nickname, region_code, citizen_type, sumin_job, persona_json, batch_id=None, created_from='manual'):
    """
    에이전트를 저장하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            '''
            INSERT OR REPLACE INTO agents 
            (id, nickname, region_code, citizen_type, sumin_job, persona_json, batch_id, created_from, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (agent_id, nickname, region_code, citizen_type, sumin_job, persona_json, batch_id, created_from, datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
        )
        db.commit()
        return agent_id
    except Exception as e:
        logging.error(f"에이전트 저장 중 오류 발생: {e}")
        return None


def get_agent(agent_id):
    """
    에이전트를 조회하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM agents WHERE id = ?', (agent_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"에이전트 조회 중 오류 발생: {e}")
        return None


def get_agents_by_batch(batch_id):
    """
    배치 ID로 에이전트 목록을 조회하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM agents WHERE batch_id = ? ORDER BY created_at DESC', (batch_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"배치 에이전트 조회 중 오류 발생: {e}")
        return []


def get_all_agents(status=1):
    """
    모든 에이전트를 조회하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM agents WHERE status = ? ORDER BY created_at DESC LIMIT 100', (status,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except Exception as e:
        logging.error(f"에이전트 목록 조회 중 오류 발생: {e}")
        return []


def delete_agents_by_batch(batch_id):
    """
    배치 ID로 에이전트를 일괄 삭제하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('DELETE FROM agents WHERE batch_id = ?', (batch_id,))
        db.commit()
        return True
    except Exception as e:
        logging.error(f"배치 에이전트 삭제 중 오류 발생: {e}")
        return False


def save_agent_relation(source_id, target_id, relation_type, affinity_score, reason=None):
    """
    에이전트 간 관계를 저장하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            '''
            INSERT OR REPLACE INTO agent_relations (source_id, target_id, relation_type, affinity_score, reason)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (source_id, target_id, relation_type, affinity_score, reason),
        )
        db.commit()
        return True
    except Exception as e:
        logging.error(f"에이전트 관계 저장 중 오류 발생: {e}")
        return False


def get_agent_relation(source_id, target_id):
    """
    에이전트 간 관계를 조회하는 함수
    """
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT * FROM agent_relations WHERE source_id = ? AND target_id = ?', (source_id, target_id))
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"에이전트 관계 조회 중 오류 발생: {e}")
        return None


def get_community_post(post_id):
    """단일 커뮤니티 게시글 조회"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            '''
            SELECT id, board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count, created_at
            FROM community_posts
            WHERE id = ?
            ''',
            (post_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"커뮤니티 게시글 단건 조회 중 오류 발생: {e}")
        return None


def increment_community_post_view(post_id):
    """게시글 조회수를 1 증가"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE community_posts SET view_count = COALESCE(view_count, 0) + 1 WHERE id = ?', (post_id,))
        db.commit()
        return True
    except Exception as e:
        logging.error(f"커뮤니티 게시글 조회수 증가 중 오류 발생: {e}")
        return False


def vote_community_post(post_id, vote_type):
    """게시글 추천/비추천 반영"""
    try:
        db = get_db()
        cursor = db.cursor()
        if vote_type == 'up':
            cursor.execute('UPDATE community_posts SET upvote_count = COALESCE(upvote_count, 0) + 1 WHERE id = ?', (post_id,))
        else:
            cursor.execute('UPDATE community_posts SET downvote_count = COALESCE(downvote_count, 0) + 1 WHERE id = ?', (post_id,))
        db.commit()
        return True
    except Exception as e:
        logging.error(f"커뮤니티 게시글 투표 반영 중 오류 발생: {e}")
        return False


def get_community_post(post_id):
    """단일 커뮤니티 게시글 조회"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            '''
            SELECT id, board, author_name, title, content, source_topic, flair, upvote_count, downvote_count, view_count, created_at
            FROM community_posts
            WHERE id = ?
            ''',
            (post_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None
    except Exception as e:
        logging.error(f"커뮤니티 게시글 단건 조회 중 오류 발생: {e}")
        return None


def increment_community_post_view(post_id):
    """게시글 조회수를 1 증가"""
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute('UPDATE community_posts SET view_count = COALESCE(view_count, 0) + 1 WHERE id = ?', (post_id,))
        db.commit()
        return True
    except Exception as e:
        logging.error(f"커뮤니티 게시글 조회수 증가 중 오류 발생: {e}")
        return False


def vote_community_post(post_id, vote_type):
    """게시글 추천/비추천 반영"""
    try:
        db = get_db()
        cursor = db.cursor()
        if vote_type == 'up':
            cursor.execute('UPDATE community_posts SET upvote_count = COALESCE(upvote_count, 0) + 1 WHERE id = ?', (post_id,))
        else:
            cursor.execute('UPDATE community_posts SET downvote_count = COALESCE(downvote_count, 0) + 1 WHERE id = ?', (post_id,))
        db.commit()
        return True
    except Exception as e:
        logging.error(f"커뮤니티 게시글 투표 반영 중 오류 발생: {e}")
        return False
