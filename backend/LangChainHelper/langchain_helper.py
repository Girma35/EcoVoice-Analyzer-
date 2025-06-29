import os
import asyncpg
import aiosqlite
from typing import Dict, Any, List, Tuple
import json
from datetime import datetime
import asyncio
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.llms import Cohere
from langchain.agents.agent_types import AgentType
from urllib.parse import urlparse

class LangChainHelper:
    """
    Database interaction helper using LangChain for natural language queries.
    
    Handles data storage and natural language to SQL conversion for
    pollution analysis records. Supports both PostgreSQL and SQLite.
    """
    
    def __init__(self, db_url: str = None):
        """
        Initialize database connection and LangChain components.
        
        Args:
            db_url: Database URL (PostgreSQL or SQLite)
        """
        self.db_url = db_url or os.getenv("DATABASE_URL", "sqlite:///./pollution_data.db")
        self.cohere_api_key = os.getenv("COHERE_API_KEY")
        
        if not self.cohere_api_key:
            raise ValueError("COHERE_API_KEY environment variable is required")
        
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
            # Remove asyncpg from URL for LangChain
            self.langchain_db_url = self.db_url.replace('+asyncpg', '')
        else:
            self.sqlite_path = self.db_url.replace("sqlite:///", "")
            self.langchain_db_url = self.db_url
        
        self.db_initialized = False
        self.agent = None
        
        # Database schema for pollution records (PostgreSQL compatible)
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
            
            # Initialize LangChain agent
            await self._initialize_langchain_agent()
            
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
    
    async def _initialize_langchain_agent(self):
        """Initialize LangChain SQL agent for natural language queries."""
        
        try:
            # Create SQLDatabase connection for LangChain
            db = SQLDatabase.from_uri(self.langchain_db_url)
            
            # Initialize Cohere LLM
            llm = Cohere(
                cohere_api_key=self.cohere_api_key,
                temperature=0.1,
                max_tokens=500
            )
            
            # Create SQL toolkit and agent
            toolkit = SQLDatabaseToolkit(db=db, llm=llm)
            
            self.agent = create_sql_agent(
                llm=llm,
                toolkit=toolkit,
                agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=False,
                handle_parsing_errors=True
            )
            
            print("LangChain SQL agent initialized")
            
        except Exception as e:
            print(f"Warning: LangChain agent initialization failed: {str(e)}")
            self.agent = None
    
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
            if self.agent:
                # Use LangChain agent for natural language to SQL conversion
                result = await asyncio.to_thread(
                    self.agent.run,
                    natural_language_query
                )
                
                # Parse agent response to extract SQL and results
                sql_query, results = self._parse_agent_response(result)
                
            else:
                # Fallback to predefined query patterns
                sql_query, results = await self._fallback_query(natural_language_query)
            
            return sql_query, results
            
        except Exception as e:
            # Return error information
            return f"ERROR: {str(e)}", []
    
    def _parse_agent_response(self, agent_result: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Parse LangChain agent response to extract SQL and results."""
        
        try:
            # Agent response typically includes the final answer
            # For now, we'll execute a direct query to get structured results
            
            # Extract potential SQL from agent response
            import re
            sql_pattern = r'SELECT.*?FROM.*?(?:WHERE.*?)?(?:GROUP BY.*?)?(?:ORDER BY.*?)?(?:LIMIT.*?)?;?'
            sql_matches = re.findall(sql_pattern, agent_result, re.IGNORECASE | re.DOTALL)
            
            if sql_matches:
                sql_query = sql_matches[0].strip()
                # Execute the extracted SQL to get structured results
                results = asyncio.run(self._execute_sql(sql_query))
                return sql_query, results
            else:
                # If no SQL found, return the agent's natural language response
                return "Natural language response", [{"response": agent_result}]
                
        except Exception as e:
            return f"Agent parsing error: {str(e)}", []
    
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
    
    async def _fallback_query(self, query: str) -> Tuple[str, List[Dict[str, Any]]]:
        """Fallback query handling when LangChain agent is unavailable."""
        
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
        elif "type" in query_lower:
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
        elif "location" in query_lower:
            sql = """
                SELECT address, pollution_type, created_at
                FROM pollution_records 
                WHERE address IS NOT NULL 
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
                "database_type": "PostgreSQL",
                "langchain_available": self.agent is not None
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
                "database_type": "SQLite",
                "langchain_available": self.agent is not None
            }
    
    async def cleanup_old_records(self, days_old: int = 365):
        """Clean up records older than specified days."""
        
        try:
            if self.is_postgres:
                conn = await asyncpg.connect(**self.pg_config)
                try:
                    deleted_count = await conn.fetchval("""
                        DELETE FROM pollution_records 
                        WHERE created_at < NOW() - INTERVAL '%s days'
                        RETURNING COUNT(*)
                    """, days_old)
                finally:
                    await conn.close()
            else:
                async with aiosqlite.connect(self.sqlite_path) as db:
                    cursor = await db.execute("""
                        DELETE FROM pollution_records 
                        WHERE datetime(created_at) < datetime('now', '-' || ? || ' days')
                    """, (days_old,))
                    
                    await db.commit()
                    deleted_count = cursor.rowcount
            
            print(f"Cleaned up {deleted_count} records older than {days_old} days")
            return deleted_count
            
        except Exception as e:
            raise RuntimeError(f"Cleanup failed: {str(e)}")