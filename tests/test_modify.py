import os
import pytest
import tempfile
from tinydb import TinyDB, Query
from tinydb_tool.commands.update_cmd import execute_update_command
from tinydb_tool.commands.delete_cmd import execute_delete_command

class TestModifyCommands:
    
    @pytest.fixture
    def db_path(self):
        """Fixture: Setup DB for modification tests."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        
        db = TinyDB(path)
        db.insert_multiple([
            {'id': 1, 'status': 'active', 'score': 10},
            {'id': 2, 'status': 'inactive', 'score': 5},
            {'id': 3, 'status': 'active', 'score': 8}
        ])
        db.close()
        
        yield path
        
        if os.path.exists(path):
            os.remove(path)

    def test_update_command(self, db_path):
        """Test updating documents based on a query."""
        # Update: Set score to 0 for all inactive users
        update_data = '{"score": 0}'
        query = "status == 'inactive'"
        
        result = execute_update_command(db_path, string_to_query=query, data_string=update_data)
        assert result == 0
        
        # Verify update in DB
        db = TinyDB(db_path)
        User = Query()
        # User 2 should be updated
        updated_user = db.get(User.id == 2)
        assert updated_user['score'] == 0
        # User 1 should be unchanged
        active_user = db.get(User.id == 1)
        assert active_user['score'] == 10
        db.close()

    def test_delete_command(self, db_path):
        """Test deleting documents based on a query."""
        # Delete: Remove all active users
        query = "status == 'active'"
        
        result = execute_delete_command(db_path, string_to_query=query)
        assert result == 0
        
        # Verify deletion in DB
        db = TinyDB(db_path)
        # Should only have 1 document left (the inactive one)
        assert len(db.all()) == 1
        assert db.all()[0]['status'] == 'inactive'
        db.close()

    def test_update_invalid_json(self, db_path):
        """Test update command with invalid JSON data."""
        result = execute_update_command(
            db_path, 
            string_to_query="id == 1", 
            data_string="{invalid_json}"
        )
        assert result == 1