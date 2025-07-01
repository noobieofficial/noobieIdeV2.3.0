import re
import sys
import random
import traceback
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Union, Optional, Set

class DataType(Enum):
    """Enumeration for supported data types"""
    INT = "INT"
    STR = "STR"
    CHAR = "CHAR"
    BOOL = "BOOL"
    FLOAT = "FLOAT"

class Command(Enum):
    """Enumeration for supported commands"""
    SAY = "SAY"
    EXIT = "EXIT"
    CREATE = "CREATE"
    RANDOM = "RANDOM"
    CHANGE = "CHANGE"
    CONVERT = "CONVERT"
    LISTEN = "LISTEN"

@dataclass
class Variable:
    """Data class to represent a variable"""
    type: str
    value: Any
    const: bool = False

# Constants
BOOLEAN_VALUES = {"true", "false", "null"}
EXPRESSION_REPLACEMENTS = {
    'true': 'True', 'false': 'False', 'null': 'None',
    'AND': 'and', 'OR': 'or', 'NOT': 'not', 'XOR': '!=', 'xor': '!='
}

class NoobieError(Exception):
    """Custom exception for Noobie language errors"""
    def __init__(self, message: str, line_number: Optional[int] = None):
        self.line_number = line_number
        super().__init__(message)

def auto_round(number: float, max_precision: int = 10) -> Union[int, float]:
    """Dynamically round a number based on its value"""
    if isinstance(number, int) or number == int(number):
        return int(number)
    
    # More efficient rounding calculation
    decimal_places = max_precision
    for i in range(max_precision):
        if round(number, i) == round(number, max_precision):
            decimal_places = i
            break
    
    return round(number, decimal_places)

def preprocess_expression(expression: str) -> str:
    """Preprocess the expression to replace specific constructs"""
    for old, new in EXPRESSION_REPLACEMENTS.items():
        expression = expression.replace(old, new)
    return expression

def evaluate_expression(expression: str, variables: Dict[str, Variable]) -> Union[str, int, float]:
    """Safely evaluate an expression with improved error handling"""
    try:
        expression = preprocess_expression(expression)
        used_variables = re.findall(r'\b[a-zA-Z_]\w*\b', expression)
        
        # Filter only actual variables (not Python keywords/functions)
        actual_vars = [var for var in used_variables if var in variables]
        
        if actual_vars:
            # Check type consistency
            types = {variables[var].type for var in actual_vars}
            if len(types) > 1:
                raise NoobieError(f"type Error: Variables have different types: {types}")
        
        # Create safe evaluation environment
        safe_dict = {"__builtins__": {}}
        local_scope = {name: var.value for name, var in variables.items()}
        
        result = eval(expression, safe_dict, local_scope)
        
        if isinstance(result, bool):
            return "true" if result else "false"
        return auto_round(result) if isinstance(result, float) else result
        
    except Exception as e:
        raise NoobieError(f"calculation Error: {e}")

def replace_variables(line: str, variables: Dict[str, Variable]) -> str:
    """Replace variable references with their values or types"""
    def substitute(match):
        prefix, var_name = match.groups()
        
        # Handle special reserved variable END (case insensitive)
        if var_name.lower() == "end":
            if prefix == "@":
                return "\\n"
            elif prefix == '?':
                return "STR"
            return match.group(0)
        
        if var_name not in variables:
            return match.group(0)
            
        var = variables[var_name]
        
        if prefix == "@":
            if var.type == "BOOL":
                return "null" if var.value is None else ("true" if var.value else "false")
            elif var.type in {"INT", "FLOAT"}:
                return str(auto_round(var.value))
            return str(var.value) if var.value is not None else "null"
        elif prefix == '?':
            return var.type
            
        return match.group(0)
    
    return re.sub(r'(@|\?)([a-zA-Z_]\w*)', substitute, line)

def read_code_from_file(filename: str) -> str:
    """Read code from file with better error handling"""
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise NoobieError(f"file '{filename}' not found")
    except PermissionError:
        raise NoobieError(f"permission denied reading file '{filename}'")
    except Exception as e:
        raise NoobieError(f"file reading error: {e}")

def handle_error(message: str, line_number: Optional[int] = None):
    """Improved error handling"""
    if line_number:
        print(f"LINE {line_number} -> ERROR: {message}", file=sys.stderr)
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    
    #if sys.exc_info()[0] is not None:
    #    traceback.print_exc()
    sys.exit(1)

def is_valid_expression(expression: str) -> bool:
    """Check if a string is a valid mathematical expression"""
    # Check for balanced parentheses
    paren_count = 0
    brace_count = 0
    
    for char in expression:
        if char == '(':
            paren_count += 1
        elif char == ')':
            paren_count -= 1
        elif char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
        
        # If at any point we have more closing than opening, it's invalid
        if paren_count < 0 or brace_count < 0:
            return False
    
    # Check if all parentheses and braces are balanced
    if paren_count != 0 or brace_count != 0:
        return False
    
    # Check if it contains mathematical operators or is numeric
    math_operators = ['+', '-', '*', '/', '//', '%', '**', '(', ')']
    has_operator = any(op in expression for op in math_operators)
    
    # Check if it's a number
    try:
        float(expression)
        return True
    except ValueError:
        pass
    
    return has_operator

def initialize_variable(var_type: str, raw_value: Optional[str] = None) -> Any:
    """Initialize a variable based on its type with improved validation"""
    var_type = var_type.upper()
    
    if var_type not in [t.value for t in DataType]:
        raise NoobieError(f"unsupported type: {var_type}")
    
    # Default values for None input
    if raw_value is None:
        defaults = {
            "INT": 0,
            "FLOAT": 0.0,
            "BOOL": None,
            "CHAR": '\x00',
            "STR": ''
        }
        return defaults[var_type]
    
    raw_value = str(raw_value).strip()
    
    try:
        # Skip expression evaluation if it starts with { (will be handled by interpreter)
        if raw_value.startswith('{') and raw_value.endswith('}'):
            raise NoobieError("expression with curly braces should be handled by the interpreter")
        
        # Handle mathematical expressions for numeric types
        if var_type in ["INT", "FLOAT"] and is_valid_expression(raw_value):
            try:
                result = eval(raw_value, {"__builtins__": {}})
                return int(result) if var_type == "INT" else float(result)
            except:
                # If eval fails, try to parse as regular value
                pass
        
        # Type-specific initialization
        if var_type == "INT":
            return int(raw_value)
        elif var_type == "FLOAT":
            return float(raw_value)
        elif var_type == "BOOL":
            lower_val = raw_value.lower()
            if lower_val == "null":
                return None
            return lower_val == "true"
        elif var_type == "CHAR":
            if raw_value.isdigit():
                ascii_val = int(raw_value)
                if 0 <= ascii_val <= 127:
                    return chr(ascii_val)
                raise NoobieError("CHAR ASCII value must be between 0 and 127")
            if len(raw_value) == 3 and raw_value.startswith("'") and raw_value.endswith("'"):
                return raw_value[1]
            if len(raw_value) == 1:
                return raw_value
            raise NoobieError("invalid CHAR value")
        elif var_type == "STR":
            return raw_value.strip('"\'')
            
    except ValueError as e:
        raise NoobieError(f"cannot convert '{raw_value}' to {var_type}: {e}")
    except NoobieError:
        raise
    except Exception as e:
        raise NoobieError(f"initialization error: {e}")

def convert_value(current: Any, old_type: str, new_type: str) -> Any:
    """Convert a value between data types with improved logic"""
    old_type, new_type = old_type.upper(), new_type.upper()
    
    if new_type not in [t.value for t in DataType]:
        raise NoobieError(f"unsupported type: {new_type}")
    
    try:
        # Conversion matrix - more readable
        conversions = {
            ("INT", "FLOAT"): lambda x: float(x),
            ("INT", "CHAR"): lambda x: chr(x) if 0 <= x <= 127 else None,
            ("INT", "STR"): lambda x: str(x),
            ("INT", "BOOL"): lambda x: x != 0,
            
            ("FLOAT", "INT"): lambda x: int(x),
            ("FLOAT", "CHAR"): lambda x: chr(int(x)) if 0 <= int(x) <= 127 else None,
            ("FLOAT", "STR"): lambda x: str(x),
            ("FLOAT", "BOOL"): lambda x: int(x) != 0,
            
            ("CHAR", "INT"): lambda x: ord(x),
            ("CHAR", "FLOAT"): lambda x: float(ord(x)),
            ("CHAR", "STR"): lambda x: x,
            ("CHAR", "BOOL"): lambda x: ord(x) not in {0, 32, 9, 48},  # Fixed logic
            
            ("BOOL", "INT"): lambda x: 1 if x else 0,
            ("BOOL", "FLOAT"): lambda x: 1.0 if x else 0.0,
            ("BOOL", "STR"): lambda x: "true" if x else "false",
            ("BOOL", "CHAR"): lambda x: '1' if x else '0',
            
            ("STR", "INT"): lambda x: len(x),
            ("STR", "FLOAT"): lambda x: float(len(x)),
            ("STR", "BOOL"): lambda x: bool(x.strip()),
            ("STR", "CHAR"): lambda x: x[0] if len(x) == 1 else None,
        }
        
        conversion_key = (old_type, new_type)
        if conversion_key in conversions:
            result = conversions[conversion_key](current)
            if result is None:
                raise NoobieError(f"invalid conversion from {old_type} to {new_type}")
            return result
        else:
            raise NoobieError(f"unsupported conversion: {old_type} -> {new_type}")
            
    except Exception as e:
        raise NoobieError(f"conversion error: {e}")

def randomize(min_val: int, max_val: int, var_type: str) -> Any:
    """Generate a random value with improved validation"""
    var_type = var_type.upper()
    
    if var_type not in [t.value for t in DataType]:
        raise NoobieError(f"unsupported type: {var_type}")
    
    if min_val > max_val:
        raise NoobieError("min value cannot be greater than max value")
    
    if var_type == "INT":
        return random.randint(min_val, max_val)
    elif var_type == "FLOAT":
        return random.uniform(min_val, max_val)
    elif var_type == "CHAR":
        if not (0 <= min_val <= max_val <= 127):
            raise NoobieError("CHAR range must be between 0 and 127")
        return chr(random.randint(min_val, max_val))
    elif var_type == "BOOL":
        if min_val == 1 and max_val == 2:
            return random.choice([True, False])
        elif min_val == 1 and max_val == 3:
            return random.choice([True, False, None])
        raise NoobieError("invalid BOOL range (use 1-2 or 1-3)")
    elif var_type == "STR":
        # More comprehensive character set
        chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+-=[]{}|;:'\",.<>/?`~"
        length = random.randint(min_val, max_val)
        return ''.join(random.choice(chars) for _ in range(length))
    
    raise NoobieError(f"unsupported type for randomization: {var_type}")