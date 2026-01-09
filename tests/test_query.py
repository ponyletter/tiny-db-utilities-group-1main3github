import os
import pytest
import tempfile
from tinydb import TinyDB
from tinydb_tool.commands.query_cmd import execute_query_command

class TestQueryCommand:
    
    @pytest.fixture
    def db_path(self):
        """Fixture: Create a temporary database with diverse sample data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        
        db = TinyDB(path)
        db.insert_multiple([
            {'name': 'John', 'age': 30, 'role': 'admin'},
            {'name': 'Jane', 'age': 25, 'role': 'user'},
            {'name': 'Bob', 'age': 35, 'role': 'user'},
            {'name': 'Alice', 'age': 30, 'role': 'guest'}
        ])
        db.close()
        
        yield path
        
        if os.path.exists(path):
            os.remove(path)

    def test_query_equality(self, db_path, capsys):
        """Test simple equality query (name == 'John')."""
        result = execute_query_command(db_path, string_to_query="name == 'John'", pretty=False)
        assert result == 0
        
        captured = capsys.readouterr()
        assert '"name": "John"' in captured.out
        assert '"name": "Jane"' not in captured.out

    def test_query_inequality(self, db_path, capsys):
        """Test inequality query (role != 'admin')."""
        result = execute_query_command(db_path, string_to_query="role != 'admin'", pretty=False)
        assert result == 0
        
        captured = capsys.readouterr()
        # Should find Jane, Bob, Alice
        assert '"role": "user"' in captured.out
        assert '"role": "guest"' in captured.out
        # Should not find John
        assert '"name": "John"' not in captured.out

    def test_query_numeric_comparison(self, db_path, capsys):
        """Test numeric comparison (age > 28)."""
        result = execute_query_command(db_path, string_to_query="age > 28", pretty=False)
        assert result == 0
        
        captured = capsys.readouterr()
        # Should match John (30), Bob (35), Alice (30)
        assert '"name": "John"' in captured.out
        assert '"name": "Bob"' in captured.out
        # Should not match Jane (25)
        assert '"name": "Jane"' not in captured.out

    def test_query_invalid_syntax(self, db_path):
        """Test error handling for invalid query syntax."""
        # Missing value
        result = execute_query_command(db_path, string_to_query="age ==")
        assert result == 1
        
        # Unsupported operator
        result = execute_query_command(db_path, string_to_query="age ~= 30")
        assert result == 1