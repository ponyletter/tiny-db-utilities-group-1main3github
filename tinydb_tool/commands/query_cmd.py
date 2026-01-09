import re
from difflib import SequenceMatcher
from typing import Any, Optional, Tuple, List, Dict
from tinydb import Query
from tinydb_tool.shared.db_utils import load_database
from tinydb_tool.shared.formatting import print_documents
from tinydb_tool.shared.error import handle_error


def parse_query_string(string_to_query: str) -> Optional[Tuple[str, str, Any]]:
    """
    Parse a query string into its components.
    
    Args:
        string_to_query: Query string in the format "field == value", "field != value",
                        "field > value", "field < value", "field >= value", or "field <= value".
        
    Returns:
        A tuple of (field_name, operator, value) if parsing succeeds, None otherwise.
        - field_name: The field name to query
        - operator: The comparison operator ('==', '!=', '>', '<', '>=', or '<=')
        - value: The value to compare against (string or numeric)
    """
    if not string_to_query or not isinstance(string_to_query, str):
        return None
    
    string_to_query = string_to_query.strip()
    
    if not string_to_query:
        return None
    
    # Support ==, !=, >, <, >=, <= operators
    pattern = r'^(\w+)\s*(==|!=|>=|<=|>|<)\s*(.+)$'
    match = re.match(pattern, string_to_query)
    
    if not match:
        return None
    
    field_name = match.group(1)
    operator = match.group(2)
    value_string = match.group(3).strip()
    
    if not field_name or not operator or not value_string:
        return None
    
    value = parse_value(value_string)
    
    return field_name, operator, value


def parse_value(value_string: str) -> Any:
    """
    Parse a value string, removing quotes if present.
    
    Args:
        value_string: The value string, optionally quoted with single or double quotes.
        
    Returns:
        The parsed value. If the string is quoted, returns the unquoted string.
        Otherwise, returns the string as-is (which may represent a number).
    """
    value_string = value_string.strip()
    
    if (value_string.startswith('"') and value_string.endswith('"')) or \
       (value_string.startswith("'") and value_string.endswith("'")):
        return value_string[1:-1]

    return value_string


def parse_numeric_value(value: Any) -> float:
    """
    Parse a value as a numeric type (int or float).
    
    Args:
        value: Value to parse (can be int, float, or string representation).
        
    Returns:
        Float representation of the numeric value.
        
    Raises:
        ValueError: If the value cannot be parsed as a number.
    """
    if isinstance(value, (int, float)):
        return float(value)
    
    if isinstance(value, str):
        value = value.strip()
        try:
            return float(value)
        except ValueError:
            try:
                import math
                safe_namespace = {
                    'math': math,
                    '__builtins__': {}
                }
                result = eval(value, safe_namespace)
                if isinstance(result, (int, float)):
                    return float(result)
                else:
                    raise ValueError("")
            except:
                raise ValueError(f"Cannot parse as numeric value: {value}")
    
    raise ValueError(f"Cannot parse as numeric value: {value}")


def is_numeric_value(value: Any) -> bool:
    """
    Check if a value can be parsed as a number.
    
    Args:
        value: Value to check.
        
    Returns:
        True if the value can be parsed as a number, False otherwise.
    """
    try:
        parse_numeric_value(value)
        return True
    except (ValueError, TypeError):
        return False


def build_tinydb_query(field_name: str, operator: str, value: Any) -> Any:
    """
    Build a TinyDB query condition from parsed components.
    
    Args:
        field_name: The field name to query.
        operator: The comparison operator ('==', '!=', '>', '<', '>=', or '<=').
        value: The value to compare against.
        
    Returns:
        A TinyDB query condition object.
        
    Raises:
        ValueError: If the operator is not supported, or if numeric operators are used
                   with non-numeric values.
    """
    Q = Query()
    field = Q[field_name]
    
    # Handle numeric comparison operators (>, >=, <, <=)
    if operator in ('>', '>=', '<', '<='):
        try:
            numeric_value = parse_numeric_value(value)
        except ValueError as e:
            raise ValueError(f"Numeric comparison operators (>, >=, <, <=) require numeric values. {str(e)}")
        
        if operator == '>':
            return field.test(lambda x: is_numeric_value(x) and parse_numeric_value(x) > numeric_value)
        elif operator == '>=':
            return field.test(lambda x: is_numeric_value(x) and parse_numeric_value(x) >= numeric_value)
        elif operator == '<':
            return field.test(lambda x: is_numeric_value(x) and parse_numeric_value(x) < numeric_value)
        elif operator == '<=':
            return field.test(lambda x: is_numeric_value(x) and parse_numeric_value(x) <= numeric_value)
    
    # Handle equality operators (==, !=)
    if operator == '==':
        return field == value
    elif operator == '!=':
        return field != value
    else:
        raise ValueError(f"Unsupported operator: {operator}")


def parse_and_build_query(string_to_query: str) -> Any:
    """
    Parse a query string and build a TinyDB query condition.
    
    This function is designed to be reused by other commands (e.g., delete, update).
    
    Args:
        string_to_query: Query string in the format "field == value", "field != value",
                        "field > value", "field < value", "field >= value", or "field <= value"
        
    Returns:
        TinyDB query condition object.
        
    Raises:
        ValueError: If the query string is invalid, empty, or operator is unsupported.
                    The error message will provide details about what went wrong.
    """
    if not string_to_query or not isinstance(string_to_query, str):
        raise ValueError("Query string cannot be empty or non-string")
    
    string_to_query = string_to_query.strip()
    if not string_to_query:
        raise ValueError("Query string cannot be empty or whitespace only")
    
    parsed = parse_query_string(string_to_query)
    if parsed is None:
        raise ValueError(
            f"Invalid query format: '{string_to_query}'. "
            f"Expected format: 'field == value', 'field != value', 'field > value', "
            f"'field < value', 'field >= value', or 'field <= value'. "
            f"Field names must be alphanumeric (letters, numbers, underscore)."
        )
    
    field_name, operator, value = parsed
    return build_tinydb_query(field_name, operator, value)


def calculate_similarity(str1: str, str2: str) -> float:
    return SequenceMatcher(None, str(str1).lower(), str(str2).lower()).ratio()


def find_best_fuzzy_match(field_name: str, target_value: Any, all_documents: List[Dict]) -> Optional[Tuple[Dict, float]]:
    if not all_documents:
        return None
    
    best_match = None
    best_score = 0.0
    target_str = str(target_value)
    
    for doc in all_documents:
        if field_name in doc:
            doc_value = doc[field_name]
            doc_value_str = str(doc_value)
            
            score = calculate_similarity(target_str, doc_value_str)
            
            if score > best_score:
                best_score = score
                best_match = doc
    

    if best_match is not None and best_score > 0.0:
        return best_match, best_score
    
    return None


def execute_query_command(file_path: str, string_to_query: str, pretty: bool = True, fuzzy: bool = False) -> int:
    """
    Execute the query command to search for documents in the database.
    
    Args:
        file_path: Path to the TinyDB JSON database file.
        string_to_query: Query condition string in the format "field == value", "field != value",
                         "field > value", "field < value", "field >= value", or "field <= value".
        pretty: If True, format output with indentation. Default is True.
        
    Returns:
        Exit code: 0 for success, 1 for error.
    """
    try:
        # Parse and build query condition
        try:
            query_condition = parse_and_build_query(string_to_query)
        except ValueError as e:
            handle_error(str(e))
            return 1
        
        parsed_query = parse_query_string(string_to_query)
        
        # Load database
        try:
            db = load_database(file_path)
        except (FileNotFoundError, PermissionError, ValueError) as e:
            # Errors are already handled in load_database
            return 1
        
        # Search for matching documents
        try:
            matching_documents = db.search(query_condition)
        except Exception as e:
            handle_error(f"Failed to search database: {str(e)}")
            db.close()
            return 1
        
        if not matching_documents and fuzzy and parsed_query is not None:
            field_name, operator, target_value = parsed_query
            
            if operator == '==':
                print("No exact matches found.")
                
                try:
                    all_documents = db.all()
                except Exception as e:
                    handle_error(f"Failed to retrieve documents for fuzzy matching: {str(e)}")
                    db.close()
                    return 1
                
                fuzzy_result = find_best_fuzzy_match(field_name, target_value, all_documents)
                
                if fuzzy_result is not None:
                    best_match, score = fuzzy_result
                    print(f"\nDid you mean this record? (similarity: {score:.2%})")
                    print_documents([best_match], pretty)
                else:
                    print("No similar records found in the database.")
            else:
                print("No exact matches found.")
        else:
            print_documents(matching_documents, pretty)
        
        db.close()
        return 0
        
    except Exception as e:
        handle_error(f"Unexpected error while querying documents: {str(e)}")
        return 1

