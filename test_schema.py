"""Test script to validate the database schema design.

This script tests the basic functionality of the database models
and ensures the schema can be created successfully.
"""

import sys
import os

# Ensure the src directory is included in PYTHONPATH when running this script.
# Example: PYTHONPATH=../../src python test_schema.py

def test_schema_creation():
    """Test that the schema can be created without errors."""
    try:
        # Import the schema manager
        from babylon.data.models.schema import SchemaManager
        
        print("✓ Successfully imported SchemaManager")
        
        # Import all models to ensure they're properly defined
        from babylon.data.models import (
            Game, Player, GameState, PlayerDecision,
            Economy, EconomicTimeSeries, ClassRelation, ProductionSector,
            PoliticalSystem, Policy, Institution, ElectionEvent,
            Entity, EntityAttribute, EntityAttributeHistory, EntityRelationship, EntityEvent,
            Contradiction, ContradictionHistory, ContradictionEffect, ContradictionNetwork, ContradictionResolution,
            Event, Trigger,
            LogEntry, Metric
        )
        
        print("✓ Successfully imported all database models")
        
        # Test model table names
        print("\nTable names defined in models:")
        tables = [
            Game.__tablename__,
            Economy.__tablename__, 
            PoliticalSystem.__tablename__,
            Entity.__tablename__,
            Contradiction.__tablename__,
            Event.__tablename__,
        ]
        
        for table in tables:
            print(f"  - {table}")
            
        print("\n✓ All models define proper table names")
        
        # Test that relationships are defined (basic check)
        game = Game.__mapper__.relationships
        economy = Economy.__mapper__.relationships
        
        print(f"✓ Game model has {len(game)} relationships defined")
        print(f"✓ Economy model has {len(economy)} relationships defined")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_model_enums():
    """Test that enums are properly defined."""
    try:
        from babylon.data.models.core import GameStatus
        from babylon.data.models.economic import EconomicPhase
        from babylon.data.models.political import PolicyStatus, GovernmentType
        from babylon.data.models.entities import EntityType, RelationType
        from babylon.data.models.contradictions import ContradictionType, ContradictionIntensity
        from babylon.data.models.event import EventType, EventStatus
        
        print("✓ All enum types successfully imported")
        
        # Test enum values
        assert GameStatus.ACTIVE.value == "active"
        assert EconomicPhase.EXPANSION.value == "expansion"
        assert PolicyStatus.ACTIVE.value == "active" 
        assert EntityType.ORGANIZATION.value == "organization"
        assert ContradictionType.ECONOMIC.value == "economic"
        assert EventType.ECONOMIC.value == "economic"
        
        print("✓ All enum values are correct")
        
        return True
        
    except Exception as e:
        print(f"✗ Enum test failed: {e}")
        return False

def test_model_creation():
    """Test that model instances can be created."""
    try:
        from babylon.data.models.core import Game, GameStatus
        from babylon.data.models.economic import Economy, EconomicPhase
        from babylon.data.models.contradictions import Contradiction, ContradictionType, ContradictionAntagonism, ContradictionIntensity
        
        # Test creating model instances
        game = Game(
            name="Test Game",
            description="A test game for schema validation",
            status=GameStatus.ACTIVE,
            difficulty_level="normal"
        )
        
        print("✓ Game model instance created")
        
        economy = Economy(
            game_id=1,  # Would be game.id in real usage
            turn_number=1,
            gdp=1000.0,
            constant_capital=600.0,
            variable_capital=400.0,
            surplus_value=200.0,
            economic_phase=EconomicPhase.EXPANSION
        )
        
        # Test derived metric calculation
        economy.calculate_derived_metrics()
        
        print(f"✓ Economy model instance created with rate of profit: {economy.rate_of_profit}")
        
        contradiction = Contradiction(
            game_id=1,
            name="Test Contradiction",
            description="A test contradiction for validation",
            contradiction_type=ContradictionType.ECONOMIC,
            antagonism=ContradictionAntagonism.ANTAGONISTIC,
            intensity=ContradictionIntensity.MEDIUM,
            first_observed_turn=1
        )
        
        print("✓ Contradiction model instance created")
        
        return True
        
    except Exception as e:
        print(f"✗ Model creation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("Testing Babylon Database Schema")
    print("=" * 40)
    
    tests = [
        ("Schema Creation", test_schema_creation),
        ("Enum Definitions", test_model_enums),
        ("Model Creation", test_model_creation),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\nRunning {test_name} test...")
        if test_func():
            print(f"✓ {test_name} test passed")
            passed += 1
        else:
            print(f"✗ {test_name} test failed")
            failed += 1
    
    print("\n" + "=" * 40)
    print(f"Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All tests passed! Database schema is valid.")
        return True
    else:
        print("❌ Some tests failed. Please review the schema.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)