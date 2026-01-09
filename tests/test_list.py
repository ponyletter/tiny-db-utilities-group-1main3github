import os
import pytest
import tempfile
from tinydb import TinyDB
from tinydb_tool.commands.list_cmd import execute_list_command


class TestListCommand:
    @pytest.fixture
    def temp_db_with_data(self):
        """
        Fixture: Creates a database file with temporary data.
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            db_path = f.name
        
        # Initialize data
        db = TinyDB(db_path)
        sample_docs = [
            {'name': 'Alice', 'age': 30, 'city': 'New York'},
            {'name': 'Bob', 'age': 25, 'city': 'Los Angeles'},
            {'name': 'Charlie', 'age': 35, 'city': 'Chicago'}
        ]
        db.insert_multiple(sample_docs)
        db.close()
        
        yield db_path, sample_docs
        
        # Cleanup: Delete the temporary file
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_list_command_execution(self, temp_db_with_data, capsys):
        """
        Tests if the list command executes correctly and outputs content (Happy Path).
        """
        db_path, sample_data = temp_db_with_data
        
        # Execute the list command
        result_code = execute_list_command(db_path, pretty=False)
        
        # Assertion 1: The return code should be 0 (success)
        assert result_code == 0
        
        # Assertion 2: Capture standard output (stdout), check if it contains the data
        captured = capsys.readouterr()
        for doc in sample_data:
            assert doc['name'] in captured.out
            assert str(doc['age']) in captured.out
