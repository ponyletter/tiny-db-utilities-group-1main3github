import os
import json
import pytest
import tempfile
from tinydb import TinyDB
from tinydb_tool.commands.insert_cmd import execute_insert_command

class TestInsertCommand:
    
    @pytest.fixture
    def temp_files(self):
        """
        Fixture: Creates a temporary database file and a temporary input data file.
        Returns a tuple of (db_path, input_json_path).
        """
        # Create temp DB file path (closed immediately, just need the name)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            db_path = f.name
            
        # Create temp input JSON file for --file-input testing
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            input_json_path = f.name
            # Write sample data to input file
            json.dump([{"source": "file", "id": 1}, {"source": "file", "id": 2}], f)

        yield db_path, input_json_path

        # Cleanup
        if os.path.exists(db_path):
            os.remove(db_path)
        if os.path.exists(input_json_path):
            os.remove(input_json_path)

    def test_insert_single_document(self, temp_files):
        """Test inserting a single JSON object via --data string."""
        db_path, _ = temp_files
        
        # Data to insert
        json_data = '{"name": "Test User", "role": "admin"}'
        
        # Execute insert command
        result = execute_insert_command(db_path=db_path, data=json_data)
        
        # Verify success
        assert result == 0
        
        # Verify data stored in DB
        db = TinyDB(db_path)
        docs = db.all()
        assert len(docs) == 1
        assert docs[0]['name'] == "Test User"
        db.close()

    def test_insert_multiple_documents(self, temp_files):
        """Test inserting a list of JSON objects via --data string."""
        db_path, _ = temp_files
        
        # Data to insert (JSON Array)
        json_data = '[{"id": 1}, {"id": 2}, {"id": 3}]'
        
        result = execute_insert_command(db_path=db_path, data=json_data)
        
        assert result == 0
        
        db = TinyDB(db_path)
        assert len(db) == 3
        db.close()

    def test_insert_from_file(self, temp_files):
        """Test inserting data reading from a separate JSON file (--file-input)."""
        db_path, input_file_path = temp_files
        
        # Execute insert command using file input
        result = execute_insert_command(db_path=db_path, file_input=input_file_path)
        
        assert result == 0
        
        db = TinyDB(db_path)
        # The input file created in fixture has 2 records
        assert len(db) == 2
        assert db.all()[0]['source'] == 'file'
        db.close()

    def test_insert_invalid_json(self, temp_files):
        """Test error handling for invalid JSON string."""
        db_path, _ = temp_files
        
        # Malformed JSON (missing closing brace)
        invalid_data = '{"name": "Broken"'
        
        # Should catch error and return 1
        result = execute_insert_command(db_path=db_path, data=invalid_data)
        
        assert result == 1