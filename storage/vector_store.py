"""
Vector store for semantic search of UI elements and test cases
"""

import json
import logging
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import sqlite3
import pickle
from datetime import datetime

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logging.warning("sentence-transformers not available. Vector search will be limited.")

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("chromadb not available. Using fallback vector store.")

from storage.database import DatabaseManager

class VectorStore:
    """Vector store for semantic search and similarity matching"""
    
    def __init__(self, db_manager: DatabaseManager, persist_directory: Optional[str] = None):
        self.db_manager = db_manager
        self.persist_directory = Path(persist_directory or "data/vector_store")
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize embedding model
        self.embedding_model = None
        self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
        
        # Initialize vector database
        self.chroma_client = None
        self.chroma_collection = None
        
        # Fallback storage
        self.fallback_db_path = self.persist_directory / "fallback_vectors.db"
        
        self.initialize()
    
    def initialize(self):
        """Initialize vector store components"""
        try:
            # Initialize embedding model
            self._initialize_embedding_model()
            
            # Initialize vector database
            self._initialize_vector_db()
            
            logging.info("Vector store initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize vector store: {e}")
            # Initialize fallback storage
            self._initialize_fallback_storage()
    
    def _initialize_embedding_model(self):
        """Initialize sentence transformer model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            logging.warning("Sentence transformers not available")
            return
        
        try:
            # Use a lightweight model for fast inference
            model_name = "all-MiniLM-L6-v2"
            self.embedding_model = SentenceTransformer(model_name)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            
            logging.info(f"Loaded embedding model: {model_name}")
            
        except Exception as e:
            logging.error(f"Failed to load embedding model: {e}")
            self.embedding_model = None
    
    def _initialize_vector_db(self):
        """Initialize ChromaDB vector database"""
        if not CHROMADB_AVAILABLE:
            logging.warning("ChromaDB not available")
            return
        
        try:
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.persist_directory / "chroma"),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            collection_name = "test_automation_vectors"
            try:
                self.chroma_collection = self.chroma_client.get_collection(collection_name)
            except:
                self.chroma_collection = self.chroma_client.create_collection(
                    name=collection_name,
                    metadata={"description": "Test automation UI elements and test cases"}
                )
            
            logging.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logging.error(f"Failed to initialize ChromaDB: {e}")
            self.chroma_client = None
            self.chroma_collection = None
    
    def _initialize_fallback_storage(self):
        """Initialize fallback SQLite storage for vectors"""
        try:
            conn = sqlite3.connect(self.fallback_db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vectors (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    embedding BLOB,
                    metadata TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_vectors_id ON vectors(id)")
            conn.close()
            
            logging.info("Fallback vector storage initialized")
            
        except Exception as e:
            logging.error(f"Failed to initialize fallback storage: {e}")
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for text"""
        if not self.embedding_model:
            return None
        
        try:
            # Clean and normalize text
            text = text.strip()
            if not text:
                return None
            
            # Generate embedding
            embedding = self.embedding_model.encode(text, normalize_embeddings=True)
            return embedding.tolist()
            
        except Exception as e:
            logging.error(f"Failed to generate embedding: {e}")
            return None
    
    def store_ui_element(self, element_id: str, element_data: Dict[str, Any]) -> bool:
        """Store UI element with semantic embedding"""
        try:
            # Create embedding text from element data
            embedding_text = self._create_element_embedding_text(element_data)
            
            if not embedding_text:
                return False
            
            # Generate embedding
            embedding = self.generate_embedding(embedding_text)
            if not embedding:
                logging.warning(f"Could not generate embedding for element {element_id}")
                return False
            
            # Store in vector database
            if self.chroma_collection:
                self._store_in_chroma(element_id, embedding_text, embedding, {
                    'type': 'ui_element',
                    'element_type': element_data.get('type', ''),
                    'selector': element_data.get('css_selector', ''),
                    'text': element_data.get('text', ''),
                    'page_url': element_data.get('page_url', ''),
                    'stored_at': datetime.now().isoformat()
                })
            else:
                self._store_in_fallback(element_id, embedding_text, embedding, {
                    'type': 'ui_element',
                    'element_data': element_data
                })
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to store UI element {element_id}: {e}")
            return False
    
    def store_test_case(self, test_id: str, embedding_text: str, metadata: Dict[str, Any]) -> bool:
        """Store test case with semantic embedding"""
        try:
            # Generate embedding
            embedding = self.generate_embedding(embedding_text)
            if not embedding:
                logging.warning(f"Could not generate embedding for test case {test_id}")
                return False
            
            # Add type to metadata
            metadata['type'] = 'test_case'
            metadata['stored_at'] = datetime.now().isoformat()
            
            # Store in vector database
            if self.chroma_collection:
                self._store_in_chroma(test_id, embedding_text, embedding, metadata)
            else:
                self._store_in_fallback(test_id, embedding_text, embedding, metadata)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to store test case {test_id}: {e}")
            return False
    
    def _create_element_embedding_text(self, element_data: Dict[str, Any]) -> str:
        """Create embedding text from element data"""
        text_parts = []
        
        # Element type
        if element_data.get('type'):
            text_parts.append(f"Element type: {element_data['type']}")
        
        # Text content
        if element_data.get('text'):
            text_parts.append(f"Text: {element_data['text']}")
        
        # ARIA label
        if element_data.get('aria_label'):
            text_parts.append(f"Label: {element_data['aria_label']}")
        
        # Attributes
        if element_data.get('attributes'):
            attrs = element_data['attributes']
            if attrs.get('placeholder'):
                text_parts.append(f"Placeholder: {attrs['placeholder']}")
            if attrs.get('title'):
                text_parts.append(f"Title: {attrs['title']}")
            if attrs.get('name'):
                text_parts.append(f"Name: {attrs['name']}")
        
        # ID and class
        if element_data.get('id'):
            text_parts.append(f"ID: {element_data['id']}")
        if element_data.get('class'):
            text_parts.append(f"Class: {element_data['class']}")
        
        return " | ".join(text_parts)
    
    def _store_in_chroma(self, doc_id: str, content: str, embedding: List[float], metadata: Dict[str, Any]):
        """Store document in ChromaDB"""
        try:
            self.chroma_collection.upsert(
                ids=[doc_id],
                documents=[content],
                embeddings=[embedding],
                metadatas=[metadata]
            )
        except Exception as e:
            logging.error(f"Failed to store in ChromaDB: {e}")
            # Fallback to local storage
            self._store_in_fallback(doc_id, content, embedding, metadata)
    
    def _store_in_fallback(self, doc_id: str, content: str, embedding: List[float], metadata: Dict[str, Any]):
        """Store document in fallback SQLite database"""
        try:
            conn = sqlite3.connect(self.fallback_db_path)
            
            # Serialize embedding and metadata
            embedding_blob = pickle.dumps(embedding)
            metadata_json = json.dumps(metadata)
            
            conn.execute("""
                INSERT OR REPLACE INTO vectors (id, content, embedding, metadata)
                VALUES (?, ?, ?, ?)
            """, (doc_id, content, embedding_blob, metadata_json))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Failed to store in fallback database: {e}")
    
    def find_similar_elements(self, query: str, element_type: Optional[str] = None, 
                            limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar UI elements using semantic search"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                return []
            
            # Prepare filters
            where_filter = {"type": "ui_element"}
            if element_type:
                where_filter["element_type"] = element_type
            
            # Search in ChromaDB
            if self.chroma_collection:
                return self._search_in_chroma(query_embedding, where_filter, limit)
            else:
                return self._search_in_fallback(query_embedding, where_filter, limit)
                
        except Exception as e:
            logging.error(f"Failed to find similar elements: {e}")
            return []
    
    def find_similar_tests(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Find similar test cases using semantic search"""
        try:
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                return []
            
            # Search for test cases
            where_filter = {"type": "test_case"}
            
            if self.chroma_collection:
                return self._search_in_chroma(query_embedding, where_filter, limit)
            else:
                return self._search_in_fallback(query_embedding, where_filter, limit)
                
        except Exception as e:
            logging.error(f"Failed to find similar tests: {e}")
            return []
    
    def _search_in_chroma(self, query_embedding: List[float], where_filter: Dict[str, Any], 
                         limit: int) -> List[Dict[str, Any]]:
        """Search in ChromaDB"""
        try:
            results = self.chroma_collection.query(
                query_embeddings=[query_embedding],
                where=where_filter,
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            similar_items = []
            if results['ids'] and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    item = {
                        'id': doc_id,
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'similarity_score': 1 - results['distances'][0][i]  # Convert distance to similarity
                    }
                    similar_items.append(item)
            
            return similar_items
            
        except Exception as e:
            logging.error(f"Failed to search in ChromaDB: {e}")
            return []
    
    def _search_in_fallback(self, query_embedding: List[float], where_filter: Dict[str, Any], 
                          limit: int) -> List[Dict[str, Any]]:
        """Search in fallback SQLite database using cosine similarity"""
        try:
            conn = sqlite3.connect(self.fallback_db_path)
            cursor = conn.execute("SELECT id, content, embedding, metadata FROM vectors")
            
            similar_items = []
            query_vec = np.array(query_embedding)
            
            for row in cursor.fetchall():
                try:
                    # Deserialize embedding and metadata
                    stored_embedding = pickle.loads(row[2])
                    metadata = json.loads(row[3])
                    
                    # Check filter
                    if not self._matches_filter(metadata, where_filter):
                        continue
                    
                    # Calculate cosine similarity
                    stored_vec = np.array(stored_embedding)
                    similarity = np.dot(query_vec, stored_vec) / (
                        np.linalg.norm(query_vec) * np.linalg.norm(stored_vec)
                    )
                    
                    similar_items.append({
                        'id': row[0],
                        'content': row[1],
                        'metadata': metadata,
                        'similarity_score': float(similarity)
                    })
                    
                except Exception as e:
                    logging.debug(f"Error processing vector row: {e}")
                    continue
            
            conn.close()
            
            # Sort by similarity and return top results
            similar_items.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_items[:limit]
            
        except Exception as e:
            logging.error(f"Failed to search in fallback database: {e}")
            return []
    
    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria"""
        for key, value in filter_dict.items():
            if metadata.get(key) != value:
                return False
        return True
    
    def find_element_by_description(self, description: str, page_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Find UI element by natural language description"""
        try:
            # Create filter
            where_filter = {"type": "ui_element"}
            if page_url:
                where_filter["page_url"] = page_url
            
            # Search for similar elements
            similar_elements = self.find_similar_elements(description, limit=1)
            
            if similar_elements and similar_elements[0]['similarity_score'] > 0.7:
                return similar_elements[0]
            
            return None
            
        except Exception as e:
            logging.error(f"Failed to find element by description: {e}")
            return None
    
    def get_element_recommendations(self, element_data: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """Get recommendations for similar elements"""
        try:
            # Create embedding text
            embedding_text = self._create_element_embedding_text(element_data)
            if not embedding_text:
                return []
            
            # Find similar elements
            similar_elements = self.find_similar_elements(
                embedding_text, 
                element_data.get('type'),
                limit + 1  # +1 to exclude self if present
            )
            
            # Filter out self if present
            element_id = element_data.get('id', '')
            recommendations = [
                elem for elem in similar_elements 
                if elem['id'] != element_id
            ]
            
            return recommendations[:limit]
            
        except Exception as e:
            logging.error(f"Failed to get element recommendations: {e}")
            return []
    
    def update_element_usage(self, element_id: str, usage_data: Dict[str, Any]) -> bool:
        """Update element usage statistics"""
        try:
            # This could be used to track which elements are most commonly tested
            # For now, we'll store usage data in metadata
            if self.chroma_collection:
                # ChromaDB doesn't support direct metadata updates
                # Would need to retrieve, modify, and re-store
                pass
            else:
                # Update fallback database
                conn = sqlite3.connect(self.fallback_db_path)
                cursor = conn.execute("SELECT metadata FROM vectors WHERE id = ?", (element_id,))
                row = cursor.fetchone()
                
                if row:
                    metadata = json.loads(row[0])
                    metadata.update(usage_data)
                    metadata['last_used'] = datetime.now().isoformat()
                    
                    conn.execute("""
                        UPDATE vectors SET metadata = ? WHERE id = ?
                    """, (json.dumps(metadata), element_id))
                    
                    conn.commit()
                
                conn.close()
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to update element usage: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            stats = {
                'total_vectors': 0,
                'ui_elements': 0,
                'test_cases': 0,
                'embedding_model': None,
                'vector_db_type': 'none'
            }
            
            # Get embedding model info
            if self.embedding_model:
                stats['embedding_model'] = {
                    'name': 'all-MiniLM-L6-v2',
                    'dimension': self.embedding_dim
                }
            
            # Get counts from ChromaDB
            if self.chroma_collection:
                stats['vector_db_type'] = 'chromadb'
                try:
                    collection_count = self.chroma_collection.count()
                    stats['total_vectors'] = collection_count
                    
                    # Get type-specific counts (would require querying)
                    # For now, estimate from database
                    
                except Exception as e:
                    logging.debug(f"Error getting ChromaDB stats: {e}")
            
            # Get counts from fallback database
            else:
                stats['vector_db_type'] = 'fallback'
                try:
                    conn = sqlite3.connect(self.fallback_db_path)
                    
                    cursor = conn.execute("SELECT COUNT(*) FROM vectors")
                    stats['total_vectors'] = cursor.fetchone()[0]
                    
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM vectors 
                        WHERE json_extract(metadata, '$.type') = 'ui_element'
                    """)
                    stats['ui_elements'] = cursor.fetchone()[0]
                    
                    cursor = conn.execute("""
                        SELECT COUNT(*) FROM vectors 
                        WHERE json_extract(metadata, '$.type') = 'test_case'
                    """)
                    stats['test_cases'] = cursor.fetchone()[0]
                    
                    conn.close()
                    
                except Exception as e:
                    logging.debug(f"Error getting fallback stats: {e}")
            
            return stats
            
        except Exception as e:
            logging.error(f"Failed to get vector store statistics: {e}")
            return {}
    
    def cleanup_old_vectors(self, days: int = 90) -> int:
        """Clean up old vectors"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_iso = cutoff_date.isoformat()
            
            deleted_count = 0
            
            if self.chroma_collection:
                # ChromaDB doesn't have direct date-based deletion
                # Would need to query and delete individually
                pass
            else:
                # Clean up fallback database
                conn = sqlite3.connect(self.fallback_db_path)
                cursor = conn.execute("""
                    DELETE FROM vectors 
                    WHERE json_extract(metadata, '$.stored_at') < ?
                """, (cutoff_iso,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                conn.close()
            
            logging.info(f"Cleaned up {deleted_count} old vectors")
            return deleted_count
            
        except Exception as e:
            logging.error(f"Failed to cleanup old vectors: {e}")
            return 0
    
    def is_available(self) -> bool:
        """Check if vector store is available and functional"""
        return (
            self.embedding_model is not None and 
            (self.chroma_collection is not None or self.fallback_db_path.exists())
        )
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check of vector store"""
        health = {
            'embedding_model_available': self.embedding_model is not None,
            'vector_db_available': False,
            'vector_db_type': 'none',
            'total_vectors': 0,
            'last_error': None
        }
        
        try:
            # Check vector database
            if self.chroma_collection:
                health['vector_db_available'] = True
                health['vector_db_type'] = 'chromadb'
                health['total_vectors'] = self.chroma_collection.count()
            elif self.fallback_db_path.exists():
                health['vector_db_available'] = True
                health['vector_db_type'] = 'fallback'
                
                conn = sqlite3.connect(self.fallback_db_path)
                cursor = conn.execute("SELECT COUNT(*) FROM vectors")
                health['total_vectors'] = cursor.fetchone()[0]
                conn.close()
            
        except Exception as e:
            health['last_error'] = str(e)
        
        return health
