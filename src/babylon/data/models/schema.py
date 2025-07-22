"""Database schema initialization and migration utilities.

This module provides utilities for creating and managing the
database schema for the Babylon game.
"""

from typing import Any, Dict, List, Optional
import logging
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from ..database import Base, engine
# Import models individually to avoid circular imports
from .core import Game, Player, GameState, PlayerDecision
from .economic import Economy, EconomicTimeSeries, ClassRelation, ProductionSector
from .political import PoliticalSystem, Policy, Institution, ElectionEvent
from .entities import Entity, EntityAttribute, EntityAttributeHistory, EntityRelationship, EntityEvent
from .contradictions import Contradiction, ContradictionHistory, ContradictionEffect, ContradictionNetwork, ContradictionResolution
from .event import Event
from .trigger import Trigger

logger = logging.getLogger(__name__)


class SchemaManager:
    """Manages database schema creation and migration."""
    
    def __init__(self, database_engine: Optional[Engine] = None):
        """Initialize the schema manager.
        
        Args:
            database_engine: SQLAlchemy engine to use. If None, uses default engine.
        """
        self.engine = database_engine or engine
        
    def create_all_tables(self) -> bool:
        """Create all tables defined in the models.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Creating all database tables...")
            Base.metadata.create_all(self.engine)
            logger.info("Successfully created all tables")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to create tables: {e}")
            return False
            
    def drop_all_tables(self) -> bool:
        """Drop all tables. USE WITH CAUTION!
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.warning("Dropping all database tables...")
            Base.metadata.drop_all(self.engine)
            logger.info("Successfully dropped all tables")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to drop tables: {e}")
            return False
            
    def get_existing_tables(self) -> List[str]:
        """Get list of existing table names in the database.
        
        Returns:
            List[str]: List of table names
        """
        try:
            inspector = inspect(self.engine)
            return inspector.get_table_names()
        except SQLAlchemyError as e:
            logger.error(f"Failed to get existing tables: {e}")
            return []
            
    def get_model_tables(self) -> List[str]:
        """Get list of table names defined in models.
        
        Returns:
            List[str]: List of table names from models
        """
        return list(Base.metadata.tables.keys())
        
    def check_schema_compatibility(self) -> Dict[str, Any]:
        """Check compatibility between models and existing database schema.
        
        Returns:
            Dict[str, Any]: Schema compatibility report
        """
        existing_tables = set(self.get_existing_tables())
        model_tables = set(self.get_model_tables())
        
        return {
            "existing_tables": list(existing_tables),
            "model_tables": list(model_tables),
            "missing_tables": list(model_tables - existing_tables),
            "extra_tables": list(existing_tables - model_tables),
            "compatible": len(model_tables - existing_tables) == 0,
        }
        
    def initialize_fresh_database(self) -> bool:
        """Initialize a fresh database with all tables and basic data.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.info("Initializing fresh database...")
            
            # Drop all existing tables
            self.drop_all_tables()
            
            # Create all tables
            if not self.create_all_tables():
                return False
                
            # Insert basic configuration data
            self._insert_basic_data()
            
            logger.info("Successfully initialized fresh database")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
            
    def _insert_basic_data(self) -> None:
        """Insert basic data needed for the game to function."""
        # This would include basic configuration data,
        # default entities, etc. Implementation depends on game requirements
        pass
        
    def validate_schema(self) -> Dict[str, Any]:
        """Validate the current database schema.
        
        Returns:
            Dict[str, Any]: Validation report
        """
        report = {
            "tables": {},
            "indexes": {},
            "foreign_keys": {},
            "overall_valid": True,
            "issues": [],
        }
        
        try:
            inspector = inspect(self.engine)
            
            # Check each table
            for table_name in self.get_model_tables():
                if table_name not in self.get_existing_tables():
                    report["issues"].append(f"Missing table: {table_name}")
                    report["overall_valid"] = False
                    continue
                    
                # Validate table structure
                table_report = self._validate_table(inspector, table_name)
                report["tables"][table_name] = table_report
                
                if not table_report["valid"]:
                    report["overall_valid"] = False
                    
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            report["overall_valid"] = False
            report["issues"].append(f"Validation error: {e}")
            
        return report
        
    def _validate_table(self, inspector: Any, table_name: str) -> Dict[str, Any]:
        """Validate a specific table structure.
        
        Args:
            inspector: SQLAlchemy inspector
            table_name: Name of table to validate
            
        Returns:
            Dict[str, Any]: Table validation report
        """
        report = {
            "valid": True,
            "columns": {},
            "indexes": [],
            "foreign_keys": [],
            "issues": [],
        }
        
        try:
            # Get table info
            columns = inspector.get_columns(table_name)
            indexes = inspector.get_indexes(table_name)
            foreign_keys = inspector.get_foreign_keys(table_name)
            
            report["columns"] = {col["name"]: col for col in columns}
            report["indexes"] = indexes
            report["foreign_keys"] = foreign_keys
            
        except Exception as e:
            report["valid"] = False
            report["issues"].append(f"Failed to inspect table {table_name}: {e}")
            
        return report
        
    def get_table_sizes(self) -> Dict[str, int]:
        """Get row counts for all tables.
        
        Returns:
            Dict[str, int]: Table names mapped to row counts
        """
        sizes = {}
        
        for table_name in self.get_existing_tables():
            try:
                with self.engine.connect() as conn:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    sizes[table_name] = result.scalar()
            except Exception as e:
                logger.error(f"Failed to get size for table {table_name}: {e}")
                sizes[table_name] = -1
                
        return sizes


def initialize_database(engine: Optional[Engine] = None) -> bool:
    """Initialize the database schema.
    
    This is the main function to call to set up the database
    for the Babylon game.
    
    Args:
        engine: SQLAlchemy engine to use. If None, uses default.
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SchemaManager(engine)
    return manager.create_all_tables()


def reset_database(engine: Optional[Engine] = None) -> bool:
    """Reset the database to a fresh state.
    
    WARNING: This will delete all data!
    
    Args:
        engine: SQLAlchemy engine to use. If None, uses default.
        
    Returns:
        bool: True if successful, False otherwise
    """
    manager = SchemaManager(engine)
    return manager.initialize_fresh_database()


def validate_database_schema(engine: Optional[Engine] = None) -> Dict[str, Any]:
    """Validate the current database schema.
    
    Args:
        engine: SQLAlchemy engine to use. If None, uses default.
        
    Returns:
        Dict[str, Any]: Validation report
    """
    manager = SchemaManager(engine)
    return manager.validate_schema()


# Export the main functions
__all__ = [
    "SchemaManager",
    "initialize_database",
    "reset_database", 
    "validate_database_schema",
]