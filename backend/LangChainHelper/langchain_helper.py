import os
import asyncpg
import aiosqlite
from typing import Dict, Any, List, Tuple
import json
from datetime import datetime
import asyncio
from urllib.parse import urlparse

class LangChainHelper:
    """
    Database interaction helper for pollution analysis records.
    
    Handles data storage and basic SQL queries for pollution analysis records.
    Supports both PostgreSQL and SQLite without heavy LangChain dependencies.
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize database connection.
        
        Args:
            db_url: Database URL (PostgreSQL or SQLite)
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///./pollution_data.db")
        
        # Determine database type
        self.is_postgres = self.db_url.startswith(('postgresql', 'postgres'))
        self.is_sqlite = self.db_url.startswith('sqlite')
        
        # Extract connection details for PostgreSQL
        if self.is_postgres:
            parsed = urlparse(self.db_url)
            self.pg_config = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password
            }
        else:
            self.sqlite_path = self.db_url.replace("sqlite:///", "")
        
        self.db_initialized = False
        
        # Database schema for pollution records
        self.schema = {
            "pollution_records": """
                CREATE TABLE IF NOT EXISTS pollution_records (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    transcription TEXT NOT NULL,
                    recognition_service TEXT,
                    latitude REAL,
                    longitude REAL,
                    address TEXT,
                    pollution_type TEXT,
                    recommendation TEXT,
                    responsible_agency TEXT,
                    severity_level TEXT,
                    immediate_actions TEXT,
                    long_term_solution TEXT,
                    raw_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
            "location_index": """
                CREATE INDEX IF NOT EXISTS idx_location 
                ON pollution_records (latitude, longitude)
            """,
            "pollution_type_index": """
                CREATE INDEX IF NOT EXISTS idx_pollution_type 
                ON pollution_records (pollution_type)
            """,
            "timestamp_index": """
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON pollution_records (timestamp)
            """
        }
    
    async def initialize_db(self):
        """Initialize database with required tables and indexes."""
        
        try:
            if self.is_postgres:
                await self._initialize_postgres()
            else:
                await self._initialize_sqlite()
            
            self.db_initialized = True
            print(f"Database initialized: {self.db_url}")
            
        except Exception as e:
            raise RuntimeError(f"Database initialization failed: {str(e)}")
    
    async def _initialize_postgres(self):
        """Initialize PostgreSQL database."""
        
        conn = await asyncpg.connect(**self.pg_config)
        try:
            # Create tables and indexes
            for name, query in self.schema.items():
                await conn.execute(query)
        finally:
            await conn.close()
    
    async def _initialize_sqlite(self):
        """Initialize SQLite database."""
        
        # Adjust schema for SQLite
        sqlite_schema = {
            "pollution_records": self.schema["pollution_records"].replace("SERIAL", "INTEGER AUTOINCREMENT").replace("TIMESTAMP", "DATETIME"),
            "location_index": self.schema["location_index"],
            "pollution_type_index": self.schema["pollution_type_index"],
            "timestamp_index": self.schema["timestamp_index"]
        }
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            for name, query in sqlite_schema.items():
                await db.execute(query)
            await db.commit()
    
    async def add_to_db(self, analysis_data: Dict[str, Any]) -> int:
        """
        Add pollution analysis record to database.
        
        Args:
            analysis_data: Dictionary containing analysis results
            
        Returns:
            Record ID of inserted record
        """
        
        if not self.db_initialized:
            await self.initialize_db()
        
        try:
            # Extract location data
            location = analysis_data.get("location", {})
            
            # Prepare record data
            record_data = (
                analysis_data.get("transcription", ""),
                analysis_data.get("recognition_service", ""),
                self._safe_float(location.get("latitude")),
                self._safe_float(location.get("longitude")),
                location.get("address"),
                analysis_data.get("pollution_type", ""),
                analysis_data.get("recommendation", ""),
                analysis_data.get("responsible_agency", ""),
                analysis_data.get("severity_level", "medium"),
                analysis_data.get("immediate_actions", ""),
                analysis_data.get("long_term_solution", ""),
                json.dumps(analysis_data.get("raw_cohere_response", {})),
                datetime.now()
            )
            
            if self.is_postgres:
                return await self._add_to_postgres(record_data)
            else:
                return await self._add_to_sqlite(record_data)
                
        except Exception as e:
            raise RuntimeError(f"Failed to add record to database: {str(e)}")
    
    async def _add_to_postgres(self, record_data: tuple) -> int:
        """Add record to PostgreSQL database."""
        
        conn = await asyncpg.connect(**self.pg_config)
        try:
            record_id = await conn.fetchval("""
                INSERT INTO pollution_records 
                (transcription, recognition_service, latitude, longitude, address,
                 pollution_type, recommendation, responsible_agency, severity_level,
                 immediate_actions, long_term_solution, raw_response, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                RETURNING id
            """, *record_data)
            
            print(f"Record added to PostgreSQL with ID: {record_id}")
            return record_id
        finally:
            await conn.close()
    
    async def _add_to_sqlite(self, record_data: tuple) -> int:
        """Add record to SQLite database."""
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            cursor = await db.execute("""
                INSERT INTO pollution_records 
                (transcription, recognition_service, latitude, longitude, address,
                 pollution_type, recommendation, responsible_agency, severity_level,
                 immediate_actions, long_term_solution, raw_response, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, record_data)
            
            await db.commit()
            record_id = cursor.lastrowid
            print(f"Record added to SQLite with ID: {record_id}")
            return record_id
    
    async def query(self, natural_language_query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Convert natural language query to SQL and execute.
        
        Args:
            natural_language_query: Natural language question about the data
            
        Returns:
            Tuple of (SQL query, results)
        """
        
        if not self.db_initialized:
            await self.initialize_db()
        
        try:
            # Use predefined query patterns for common questions
            sql_query, results = await self._pattern_based_query(natural_language_query)
            return sql_query, results
            
        except Exception as e:
            # Return error information
            return f"ERROR: {str(e)}", []
    
    async def _pattern_based_query(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Handle queries using pattern matching."""
        
        query_lower = query.lower()
        
        # Predefined query patterns
        if "recent" in query_lower or "latest" in query_lower:
            sql = """
                SELECT * FROM pollution_records 
                ORDER BY created_at DESC 
                LIMIT 10
            """
        elif "count" in query_lower or "total" in query_lower:
            sql = """
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT pollution_type) as unique_pollution_types,
                    COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) as records_with_location
                FROM pollution_records
            """
        elif "type" in query_lower or "pollution" in query_lower:
            sql = """
                SELECT 
                    pollution_type,
                    COUNT(*) as count,
                    AVG(CASE 
                        WHEN severity_level = 'low' THEN 1
                        WHEN severity_level = 'medium' THEN 2  
                        WHEN severity_level = 'high' THEN 3
                        WHEN severity_level = 'critical' THEN 4
                        ELSE 2
                    END) as avg_severity
                FROM pollution_records 
                WHERE pollution_type IS NOT NULL AND pollution_type != ''
                GROUP BY pollution_type
                ORDER BY count DESC
            """
        elif "location" in query_lower or "address" in query_lower:
            sql = """
                SELECT address, pollution_type, created_at
                FROM pollution_records 
                WHERE address IS NOT NULL 
                ORDER BY created_at DESC
                LIMIT 20
            """
        elif "water" in query_lower:
            sql = """
                SELECT * FROM pollution_records 
                WHERE pollution_type LIKE '%water%'
                ORDER BY created_at DESC
                LIMIT 20
            """
        elif "air" in query_lower:
            sql = """
                SELECT * FROM pollution_records 
                WHERE pollution_type LIKE '%air%'
                ORDER BY created_at DESC
                LIMIT 20
            """
        elif "severe" in query_lower or "critical" in query_lower or "high" in query_lower:
            sql = """
                SELECT * FROM pollution_records 
                WHERE severity_level IN ('high', 'critical')
                ORDER BY created_at DESC
                LIMIT 20
            """
        else:
            # Default: return all records summary
            sql = """
                SELECT 
                    id, timestamp, pollution_type, address, severity_level
                FROM pollution_records 
                ORDER BY created_at DESC 
                LIMIT 50
            """
        
        results = await self._execute_sql(sql)
        return sql, results
    
    async def _execute_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as list of dictionaries."""
        
        try:
            if self.is_postgres:
                return await self._execute_postgres_sql(sql_query)
            else:
                return await self._execute_sqlite_sql(sql_query)
                
        except Exception as e:
            raise RuntimeError(f"SQL execution failed: {str(e)}")
    
    async def _execute_postgres_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query on PostgreSQL."""
        
        conn = await asyncpg.connect(**self.pg_config)
        try:
            rows = await conn.fetch(sql_query)
            # Convert asyncpg Records to dictionaries
            results = [dict(row) for row in rows]
            return results
        finally:
            await conn.close()
    
    async def _execute_sqlite_sql(self, sql_query: str) -> List[Dict[str, Any]]:
        """Execute SQL query on SQLite."""
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            db.row_factory = aiosqlite.Row  # Enable column access by name
            cursor = await db.execute(sql_query)
            rows = await cursor.fetchall()
            
            # Convert rows to dictionaries
            results = [dict(row) for row in rows]
            return results
    
    def _safe_float(self, value: Any) -> float:
        """Safely convert value to float, return None if conversion fails."""
        
        if value is None:
            return None
        
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics and summary information."""
        
        if not self.db_initialized:
            await self.initialize_db()
        
        try:
            if self.is_postgres:
                return await self._get_postgres_statistics()
            else:
                return await self._get_sqlite_statistics()
                
        except Exception as e:
            raise RuntimeError(f"Failed to get statistics: {str(e)}")
    
    async def _get_postgres_statistics(self) -> Dict[str, Any]:
        """Get statistics from PostgreSQL."""
        
        conn = await asyncpg.connect(**self.pg_config)
        try:
            # Total records
            total_records = await conn.fetchval("SELECT COUNT(*) FROM pollution_records")
            
            # Records by pollution type
            pollution_types = await conn.fetch("""
                SELECT pollution_type, COUNT(*) as count
                FROM pollution_records 
                WHERE pollution_type IS NOT NULL
                GROUP BY pollution_type
                ORDER BY count DESC
            """)
            
            # Records with location data
            records_with_location = await conn.fetchval("""
                SELECT COUNT(*) FROM pollution_records 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """)
            
            # Recent activity (last 7 days)
            recent_records = await conn.fetchval("""
                SELECT COUNT(*) FROM pollution_records 
                WHERE created_at > NOW() - INTERVAL '7 days'
            """)
            
            return {
                "total_records": total_records,
                "pollution_types": [{"type": row["pollution_type"], "count": row["count"]} for row in pollution_types],
                "records_with_location": records_with_location,
                "recent_activity": recent_records,
                "database_url": self.db_url,
                "database_type": "PostgreSQL"
            }
        finally:
            await conn.close()
    
    async def _get_sqlite_statistics(self) -> Dict[str, Any]:
        """Get statistics from SQLite."""
        
        async with aiosqlite.connect(self.sqlite_path) as db:
            # Total records
            cursor = await db.execute("SELECT COUNT(*) FROM pollution_records")
            total_records = (await cursor.fetchone())[0]
            
            # Records by pollution type
            cursor = await db.execute("""
                SELECT pollution_type, COUNT(*) as count
                FROM pollution_records 
                WHERE pollution_type IS NOT NULL
                GROUP BY pollution_type
                ORDER BY count DESC
            """)
            pollution_types = [{"type": row[0], "count": row[1]} for row in await cursor.fetchall()]
            
            # Records with location data
            cursor = await db.execute("""
                SELECT COUNT(*) FROM pollution_records 
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
            """)
            records_with_location = (await cursor.fetchone())[0]
            
            # Recent activity (last 7 days)
            cursor = await db.execute("""
                SELECT COUNT(*) FROM pollution_records 
                WHERE datetime(created_at) > datetime('now', '-7 days')
            """)
            recent_records = (await cursor.fetchone())[0]
            
            return {
                "total_records": total_records,
                "pollution_types": pollution_types,
                "records_with_location": records_with_location,
                "recent_activity": recent_records,
                "database_path": self.sqlite_path,
                "database_type": "SQLite"
            }