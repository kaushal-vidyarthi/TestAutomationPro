"""
Database manager for storing test cases, results, and metadata
"""

import sqlite3
import json
import logging
import time
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta
import threading
from contextlib import contextmanager

class DatabaseManager:
    """Manages SQLite database operations for the test automation tool"""
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Thread-local storage for connections
        self._local = threading.local()
        
        # Database schema version
        self.schema_version = 1
        
        # Initialize database
        self.initialize()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection"""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                str(self.db_path),
                check_same_thread=False,
                timeout=30.0
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable foreign keys
            self._local.connection.execute("PRAGMA foreign_keys = ON")
        
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Context manager for database transactions"""
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def initialize(self):
        """Initialize database schema"""
        try:
            with self.transaction() as conn:
                # Create tables
                self.create_tables(conn)
                
                # Create indexes
                self.create_indexes(conn)
                
                # Set up full-text search
                self.setup_full_text_search(conn)
                
                # Update schema version
                self.update_schema_version(conn)
                
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize database: {e}")
            raise
    
    def create_tables(self, conn: sqlite3.Connection):
        """Create database tables"""
        
        # Test cases table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                type TEXT DEFAULT 'Functional',
                priority TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Draft',
                tags TEXT,
                estimated_duration INTEGER DEFAULT 5,
                automation_enabled BOOLEAN DEFAULT TRUE,
                preconditions TEXT,
                steps TEXT, -- JSON array
                expected_result TEXT,
                assertions TEXT, -- JSON array
                environment TEXT DEFAULT 'Testing',
                browser TEXT DEFAULT 'Any',
                device_type TEXT DEFAULT 'Desktop',
                test_data TEXT, -- JSON object
                dependencies TEXT,
                author TEXT,
                source_url TEXT,
                generated_by TEXT,
                generation_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Test executions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_executions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_case_id INTEGER,
                execution_id TEXT, -- UUID for grouping parallel executions
                status TEXT DEFAULT 'Pending',
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                browser TEXT,
                environment TEXT,
                error_message TEXT,
                stack_trace TEXT,
                screenshots TEXT, -- JSON array of screenshot paths
                logs TEXT, -- JSON array of log entries
                performance_metrics TEXT, -- JSON object
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_case_id) REFERENCES test_cases (id) ON DELETE CASCADE
            )
        """)
        
        # Test execution steps table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_execution_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id INTEGER,
                step_number INTEGER,
                description TEXT,
                status TEXT DEFAULT 'Pending',
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                error_message TEXT,
                screenshot_path TEXT,
                notes TEXT,
                FOREIGN KEY (execution_id) REFERENCES test_executions (id) ON DELETE CASCADE
            )
        """)
        
        # Crawl results table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawl_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT UNIQUE, -- UUID for the crawl session
                start_url TEXT,
                config TEXT, -- JSON crawl configuration
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                duration REAL,
                pages_crawled INTEGER DEFAULT 0,
                pages_failed INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Running',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crawled pages table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS crawled_pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crawl_id TEXT,
                url TEXT,
                title TEXT,
                depth INTEGER,
                content_length INTEGER,
                elements_count INTEGER,
                forms_count INTEGER,
                links_count INTEGER,
                page_data TEXT, -- JSON page structure
                screenshot_path TEXT,
                error_message TEXT,
                crawl_time TIMESTAMP,
                FOREIGN KEY (crawl_id) REFERENCES crawl_results (crawl_id) ON DELETE CASCADE
            )
        """)
        
        # UI elements table for vector search
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ui_elements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER,
                element_type TEXT,
                selector TEXT,
                text_content TEXT,
                attributes TEXT, -- JSON object
                xpath TEXT,
                aria_label TEXT,
                description TEXT,
                embedding_id TEXT, -- Reference to vector store
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (page_id) REFERENCES crawled_pages (id) ON DELETE CASCADE
            )
        """)
        
        # Test reports table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS test_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                execution_id TEXT,
                report_type TEXT DEFAULT 'HTML',
                report_path TEXT,
                summary TEXT, -- JSON summary data
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Application settings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Database metadata table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS db_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    
    def create_indexes(self, conn: sqlite3.Connection):
        """Create database indexes for performance"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_test_cases_status ON test_cases(status)",
            "CREATE INDEX IF NOT EXISTS idx_test_cases_type ON test_cases(type)",
            "CREATE INDEX IF NOT EXISTS idx_test_cases_priority ON test_cases(priority)",
            "CREATE INDEX IF NOT EXISTS idx_test_cases_created_at ON test_cases(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_test_executions_status ON test_executions(status)",
            "CREATE INDEX IF NOT EXISTS idx_test_executions_test_case_id ON test_executions(test_case_id)",
            "CREATE INDEX IF NOT EXISTS idx_test_executions_start_time ON test_executions(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_crawled_pages_crawl_id ON crawled_pages(crawl_id)",
            "CREATE INDEX IF NOT EXISTS idx_crawled_pages_url ON crawled_pages(url)",
            "CREATE INDEX IF NOT EXISTS idx_ui_elements_page_id ON ui_elements(page_id)",
            "CREATE INDEX IF NOT EXISTS idx_ui_elements_type ON ui_elements(element_type)"
        ]
        
        for index_sql in indexes:
            conn.execute(index_sql)
    
    def setup_full_text_search(self, conn: sqlite3.Connection):
        """Setup full-text search for test cases"""
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS test_cases_fts USING fts5(
                title, description, steps, expected_result, tags,
                content='test_cases', content_rowid='id'
            )
        """)
        
        # Create triggers to keep FTS in sync
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS test_cases_fts_insert AFTER INSERT ON test_cases BEGIN
                INSERT INTO test_cases_fts(rowid, title, description, steps, expected_result, tags)
                VALUES (new.id, new.title, new.description, new.steps, new.expected_result, new.tags);
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS test_cases_fts_delete AFTER DELETE ON test_cases BEGIN
                INSERT INTO test_cases_fts(test_cases_fts, rowid, title, description, steps, expected_result, tags)
                VALUES ('delete', old.id, old.title, old.description, old.steps, old.expected_result, old.tags);
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS test_cases_fts_update AFTER UPDATE ON test_cases BEGIN
                INSERT INTO test_cases_fts(test_cases_fts, rowid, title, description, steps, expected_result, tags)
                VALUES ('delete', old.id, old.title, old.description, old.steps, old.expected_result, old.tags);
                INSERT INTO test_cases_fts(rowid, title, description, steps, expected_result, tags)
                VALUES (new.id, new.title, new.description, new.steps, new.expected_result, new.tags);
            END
        """)
    
    def update_schema_version(self, conn: sqlite3.Connection):
        """Update schema version in metadata"""
        conn.execute("""
            INSERT OR REPLACE INTO db_metadata (key, value)
            VALUES ('schema_version', ?)
        """, (str(self.schema_version),))
    
    # Test Cases Operations
    def create_test_case(self, test_case_data: Dict[str, Any]) -> int:
        """Create a new test case"""
        try:
            with self.transaction() as conn:
                # Serialize complex fields
                steps_json = json.dumps(test_case_data.get('steps', []))
                assertions_json = json.dumps(test_case_data.get('assertions', []))
                test_data_json = json.dumps(test_case_data.get('test_data', {}))
                
                cursor = conn.execute("""
                    INSERT INTO test_cases (
                        title, description, type, priority, status, tags,
                        estimated_duration, automation_enabled, preconditions,
                        steps, expected_result, assertions, environment,
                        browser, device_type, test_data, dependencies,
                        author, source_url, generated_by, generation_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    test_case_data.get('title', ''),
                    test_case_data.get('description', ''),
                    test_case_data.get('type', 'Functional'),
                    test_case_data.get('priority', 'Medium'),
                    test_case_data.get('status', 'Draft'),
                    test_case_data.get('tags', ''),
                    test_case_data.get('estimated_duration', 5),
                    test_case_data.get('automation_enabled', True),
                    test_case_data.get('preconditions', ''),
                    steps_json,
                    test_case_data.get('expected_result', ''),
                    assertions_json,
                    test_case_data.get('environment', 'Testing'),
                    test_case_data.get('browser', 'Any'),
                    test_case_data.get('device_type', 'Desktop'),
                    test_data_json,
                    test_case_data.get('dependencies', ''),
                    test_case_data.get('author', ''),
                    test_case_data.get('source_url', ''),
                    test_case_data.get('generated_by', ''),
                    test_case_data.get('generation_type', '')
                ))
                
                test_case_id = cursor.lastrowid
                
                # Update the updated_at timestamp
                conn.execute("""
                    UPDATE test_cases SET updated_at = CURRENT_TIMESTAMP WHERE id = ?
                """, (test_case_id,))
                
                logging.info(f"Created test case with ID: {test_case_id}")
                return test_case_id
                
        except Exception as e:
            logging.error(f"Failed to create test case: {e}")
            raise
    
    def get_test_case(self, test_case_id: int) -> Optional[Dict[str, Any]]:
        """Get a test case by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.execute("""
                SELECT * FROM test_cases WHERE id = ?
            """, (test_case_id,))
            
            row = cursor.fetchone()
            if row:
                return self._row_to_test_case_dict(row)
            return None
            
        except Exception as e:
            logging.error(f"Failed to get test case {test_case_id}: {e}")
            return None
    
    def get_test_cases(self, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get test cases with optional filters"""
        try:
            conn = self.get_connection()
            
            query = "SELECT * FROM test_cases"
            params = []
            
            if filters:
                conditions = []
                
                if filters.get('status'):
                    conditions.append("status = ?")
                    params.append(filters['status'])
                
                if filters.get('type'):
                    conditions.append("type = ?")
                    params.append(filters['type'])
                
                if filters.get('priority'):
                    conditions.append("priority = ?")
                    params.append(filters['priority'])
                
                if filters.get('search'):
                    conditions.append("""
                        id IN (SELECT rowid FROM test_cases_fts WHERE test_cases_fts MATCH ?)
                    """)
                    params.append(filters['search'])
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY created_at DESC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            return [self._row_to_test_case_dict(row) for row in rows]
            
        except Exception as e:
            logging.error(f"Failed to get test cases: {e}")
            return []
    
    def update_test_case(self, test_case_data: Dict[str, Any]) -> bool:
        """Update an existing test case"""
        try:
            test_case_id = test_case_data.get('id')
            if not test_case_id:
                raise ValueError("Test case ID is required for update")
            
            with self.transaction() as conn:
                # Serialize complex fields
                steps_json = json.dumps(test_case_data.get('steps', []))
                assertions_json = json.dumps(test_case_data.get('assertions', []))
                test_data_json = json.dumps(test_case_data.get('test_data', {}))
                
                conn.execute("""
                    UPDATE test_cases SET
                        title = ?, description = ?, type = ?, priority = ?, status = ?,
                        tags = ?, estimated_duration = ?, automation_enabled = ?,
                        preconditions = ?, steps = ?, expected_result = ?, assertions = ?,
                        environment = ?, browser = ?, device_type = ?, test_data = ?,
                        dependencies = ?, author = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (
                    test_case_data.get('title', ''),
                    test_case_data.get('description', ''),
                    test_case_data.get('type', 'Functional'),
                    test_case_data.get('priority', 'Medium'),
                    test_case_data.get('status', 'Draft'),
                    test_case_data.get('tags', ''),
                    test_case_data.get('estimated_duration', 5),
                    test_case_data.get('automation_enabled', True),
                    test_case_data.get('preconditions', ''),
                    steps_json,
                    test_case_data.get('expected_result', ''),
                    assertions_json,
                    test_case_data.get('environment', 'Testing'),
                    test_case_data.get('browser', 'Any'),
                    test_case_data.get('device_type', 'Desktop'),
                    test_data_json,
                    test_case_data.get('dependencies', ''),
                    test_case_data.get('author', ''),
                    test_case_id
                ))
                
                logging.info(f"Updated test case {test_case_id}")
                return True
                
        except Exception as e:
            logging.error(f"Failed to update test case: {e}")
            return False
    
    def delete_test_case(self, test_case_id: int) -> bool:
        """Delete a test case"""
        try:
            with self.transaction() as conn:
                cursor = conn.execute("DELETE FROM test_cases WHERE id = ?", (test_case_id,))
                
                if cursor.rowcount > 0:
                    logging.info(f"Deleted test case {test_case_id}")
                    return True
                else:
                    logging.warning(f"Test case {test_case_id} not found for deletion")
                    return False
                    
        except Exception as e:
            logging.error(f"Failed to delete test case {test_case_id}: {e}")
            return False
    
    def _row_to_test_case_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Convert database row to test case dictionary"""
        return {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'type': row['type'],
            'priority': row['priority'],
            'status': row['status'],
            'tags': row['tags'],
            'estimated_duration': row['estimated_duration'],
            'automation_enabled': bool(row['automation_enabled']),
            'preconditions': row['preconditions'],
            'steps': json.loads(row['steps'] or '[]'),
            'expected_result': row['expected_result'],
            'assertions': json.loads(row['assertions'] or '[]'),
            'environment': row['environment'],
            'browser': row['browser'],
            'device_type': row['device_type'],
            'test_data': json.loads(row['test_data'] or '{}'),
            'dependencies': row['dependencies'],
            'author': row['author'],
            'source_url': row['source_url'],
            'generated_by': row['generated_by'],
            'generation_type': row['generation_type'],
            'created_at': row['created_at'],
            'updated_at': row['updated_at']
        }
    
    # Test Execution Operations
    def create_test_execution(self, execution_data: Dict[str, Any]) -> int:
        """Create a new test execution record"""
        try:
            with self.transaction() as conn:
                cursor = conn.execute("""
                    INSERT INTO test_executions (
                        test_case_id, execution_id, status, start_time,
                        browser, environment
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    execution_data.get('test_case_id'),
                    execution_data.get('execution_id'),
                    execution_data.get('status', 'Running'),
                    execution_data.get('start_time', datetime.now().isoformat()),
                    execution_data.get('browser', 'chromium'),
                    execution_data.get('environment', 'Testing')
                ))
                
                execution_id = cursor.lastrowid
                logging.info(f"Created test execution with ID: {execution_id}")
                return execution_id
                
        except Exception as e:
            logging.error(f"Failed to create test execution: {e}")
            raise
    
    def update_test_execution(self, execution_id: int, update_data: Dict[str, Any]) -> bool:
        """Update test execution with results"""
        try:
            with self.transaction() as conn:
                # Serialize complex fields
                screenshots_json = json.dumps(update_data.get('screenshots', []))
                logs_json = json.dumps(update_data.get('logs', []))
                performance_json = json.dumps(update_data.get('performance_metrics', {}))
                
                conn.execute("""
                    UPDATE test_executions SET
                        status = ?, end_time = ?, duration = ?, error_message = ?,
                        stack_trace = ?, screenshots = ?, logs = ?, performance_metrics = ?
                    WHERE id = ?
                """, (
                    update_data.get('status'),
                    update_data.get('end_time'),
                    update_data.get('duration'),
                    update_data.get('error_message'),
                    update_data.get('stack_trace'),
                    screenshots_json,
                    logs_json,
                    performance_json,
                    execution_id
                ))
                
                return True
                
        except Exception as e:
            logging.error(f"Failed to update test execution {execution_id}: {e}")
            return False
    
    def get_test_results(self, status_filter: Optional[str] = None,
                        date_from: Optional[datetime] = None,
                        date_to: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Get test execution results with filters"""
        try:
            conn = self.get_connection()
            
            query = """
                SELECT e.*, tc.title as test_case_title
                FROM test_executions e
                LEFT JOIN test_cases tc ON e.test_case_id = tc.id
            """
            params = []
            conditions = []
            
            if status_filter and status_filter != "All":
                conditions.append("e.status = ?")
                params.append(status_filter)
            
            if date_from:
                conditions.append("e.start_time >= ?")
                params.append(date_from.isoformat())
            
            if date_to:
                conditions.append("e.start_time <= ?")
                params.append(date_to.isoformat())
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY e.start_time DESC"
            
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                result = dict(row)
                # Parse JSON fields
                result['screenshots'] = json.loads(row['screenshots'] or '[]')
                result['logs'] = json.loads(row['logs'] or '[]')
                result['performance_metrics'] = json.loads(row['performance_metrics'] or '{}')
                results.append(result)
            
            return results
            
        except Exception as e:
            logging.error(f"Failed to get test results: {e}")
            return []
    
    def get_test_result_details(self, execution_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed test execution results including steps"""
        try:
            conn = self.get_connection()
            
            # Get execution details
            cursor = conn.execute("""
                SELECT e.*, tc.title as test_case_title, tc.steps as test_case_steps
                FROM test_executions e
                LEFT JOIN test_cases tc ON e.test_case_id = tc.id
                WHERE e.id = ?
            """, (execution_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            result = dict(row)
            result['screenshots'] = json.loads(row['screenshots'] or '[]')
            result['logs'] = json.loads(row['logs'] or '[]')
            result['performance_metrics'] = json.loads(row['performance_metrics'] or '{}')
            result['test_case_steps'] = json.loads(row['test_case_steps'] or '[]')
            
            # Get execution steps
            cursor = conn.execute("""
                SELECT * FROM test_execution_steps
                WHERE execution_id = ?
                ORDER BY step_number
            """, (execution_id,))
            
            steps = cursor.fetchall()
            result['steps'] = [dict(step) for step in steps]
            
            return result
            
        except Exception as e:
            logging.error(f"Failed to get test result details for execution {execution_id}: {e}")
            return None
    
    def cleanup_old_results(self, days: int = 30) -> int:
        """Clean up old test results"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            with self.transaction() as conn:
                cursor = conn.execute("""
                    DELETE FROM test_executions
                    WHERE start_time < ?
                """, (cutoff_date.isoformat(),))
                
                deleted_count = cursor.rowcount
                logging.info(f"Cleaned up {deleted_count} old test results")
                return deleted_count
                
        except Exception as e:
            logging.error(f"Failed to cleanup old results: {e}")
            return 0
    
    # Crawl Results Operations
    def store_crawl_results(self, crawl_data: Dict[str, Any]) -> str:
        """Store crawl results and return crawl_id"""
        try:
            import uuid
            crawl_id = str(uuid.uuid4())
            
            with self.transaction() as conn:
                # Store crawl summary
                summary = crawl_data.get('crawl_summary', {})
                conn.execute("""
                    INSERT INTO crawl_results (
                        crawl_id, start_url, config, start_time, end_time,
                        duration, pages_crawled, pages_failed, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    crawl_id,
                    crawl_data.get('start_url', ''),
                    json.dumps(crawl_data.get('config', {})),
                    summary.get('start_time'),
                    summary.get('end_time'),
                    summary.get('duration'),
                    summary.get('pages_crawled', 0),
                    summary.get('pages_failed', 0),
                    'Completed'
                ))
                
                # Store individual pages
                for page in crawl_data.get('pages', []):
                    page_id = self._store_crawled_page(conn, crawl_id, page)
                    
                    # Store UI elements
                    for element in page.get('elements', []):
                        self._store_ui_element(conn, page_id, element)
                
                logging.info(f"Stored crawl results with ID: {crawl_id}")
                return crawl_id
                
        except Exception as e:
            logging.error(f"Failed to store crawl results: {e}")
            raise
    
    def _store_crawled_page(self, conn: sqlite3.Connection, crawl_id: str, page: Dict[str, Any]) -> int:
        """Store a single crawled page"""
        cursor = conn.execute("""
            INSERT INTO crawled_pages (
                crawl_id, url, title, depth, content_length,
                elements_count, forms_count, links_count,
                page_data, screenshot_path, crawl_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            crawl_id,
            page.get('url', ''),
            page.get('title', ''),
            page.get('depth', 0),
            page.get('content_length', 0),
            len(page.get('elements', [])),
            len(page.get('forms', [])),
            len(page.get('links', [])),
            json.dumps(page),
            page.get('screenshot_path'),
            page.get('crawl_time')
        ))
        
        return cursor.lastrowid
    
    def _store_ui_element(self, conn: sqlite3.Connection, page_id: int, element: Dict[str, Any]):
        """Store a UI element"""
        conn.execute("""
            INSERT INTO ui_elements (
                page_id, element_type, selector, text_content,
                attributes, xpath, aria_label, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            page_id,
            element.get('type', ''),
            element.get('css_selector', ''),
            element.get('text', ''),
            json.dumps(element.get('attributes', {})),
            element.get('xpath_selector', ''),
            element.get('aria_label', ''),
            element.get('description', '')
        ))
    
    def get_latest_crawl_results(self) -> Optional[Dict[str, Any]]:
        """Get the most recent crawl results"""
        try:
            conn = self.get_connection()
            
            # Get latest crawl
            cursor = conn.execute("""
                SELECT * FROM crawl_results
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            crawl_row = cursor.fetchone()
            if not crawl_row:
                return None
            
            crawl_data = dict(crawl_row)
            crawl_data['config'] = json.loads(crawl_row['config'] or '{}')
            
            # Get pages for this crawl
            cursor = conn.execute("""
                SELECT * FROM crawled_pages
                WHERE crawl_id = ?
                ORDER BY crawl_time
            """, (crawl_row['crawl_id'],))
            
            pages = []
            for page_row in cursor.fetchall():
                page_data = json.loads(page_row['page_data'] or '{}')
                pages.append(page_data)
            
            crawl_data['pages'] = pages
            return crawl_data
            
        except Exception as e:
            logging.error(f"Failed to get latest crawl results: {e}")
            return None
    
    # Settings Operations
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get application setting"""
        try:
            conn = self.get_connection()
            cursor = conn.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            
            if row:
                try:
                    return json.loads(row['value'])
                except json.JSONDecodeError:
                    return row['value']
            
            return default
            
        except Exception as e:
            logging.error(f"Failed to get setting {key}: {e}")
            return default
    
    def set_setting(self, key: str, value: Any, description: str = "") -> bool:
        """Set application setting"""
        try:
            value_str = json.dumps(value) if not isinstance(value, str) else value
            
            with self.transaction() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO app_settings (key, value, description)
                    VALUES (?, ?, ?)
                """, (key, value_str, description))
                
                return True
                
        except Exception as e:
            logging.error(f"Failed to set setting {key}: {e}")
            return False
    
    def backup_database(self, backup_path: Union[str, Path]) -> bool:
        """Create database backup"""
        try:
            import shutil
            backup_path = Path(backup_path)
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Close all connections to ensure clean backup
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
                delattr(self._local, 'connection')
            
            shutil.copy2(self.db_path, backup_path)
            logging.info(f"Database backed up to {backup_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to backup database: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        try:
            conn = self.get_connection()
            
            stats = {}
            
            # Table counts
            tables = [
                'test_cases', 'test_executions', 'crawl_results',
                'crawled_pages', 'ui_elements'
            ]
            
            for table in tables:
                cursor = conn.execute(f"SELECT COUNT(*) as count FROM {table}")
                stats[f"{table}_count"] = cursor.fetchone()['count']
            
            # Database size
            stats['database_size'] = self.db_path.stat().st_size
            
            # Recent activity
            cursor = conn.execute("""
                SELECT COUNT(*) as count FROM test_executions
                WHERE start_time >= datetime('now', '-7 days')
            """)
            stats['executions_last_7_days'] = cursor.fetchone()['count']
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get database stats: {e}")
            return {}
    
    def close(self):
        """Close database connections"""
        try:
            if hasattr(self._local, 'connection'):
                self._local.connection.close()
                delattr(self._local, 'connection')
        except Exception as e:
            logging.warning(f"Error closing database connection: {e}")
