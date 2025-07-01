import sys
import re
from func import *
from typing import Dict, List, Optional, Callable, Tuple

class NoobieInterpreter:
    """Main interpreter class for the Noobie language"""
    def __init__(self):
        self.in_comment_block = False
        self.variables: Dict[str, Variable] = {}
        self.command_handlers = self._initialize_command_handlers()
    
    def _initialize_command_handlers(self) -> Dict[str, Callable]:
        """Initialize command handlers for better maintainability"""
        return {
            'if': self._handle_if,
            'while': self._handle_while,
            'say': self._handle_say,
            'del': self._handle_del,
            'exit': self._handle_exit,
            'swap': self._handle_swap,
            'round': self._handle_round,
            'reset': self._handle_reset,
            'random': self._handle_random,
            'create': self._handle_create,
            'listen': self._handle_listen,
            'change': self._handle_change,
            'convert': self._handle_convert,
            'reverse': self._handle_reverse,
            'increment': self._handle_increment,
            'decrement': self._handle_decrement,
            'uppercase': self._handle_uppercase,
            'lowercase': self._handle_lowercase,
        }
    
    def _evaluate_expression_with_parentheses(self, expression: str) -> Any:
        """Evaluate expression with better error handling"""
        try:
            result = evaluate_expression(expression, self.variables)
            # Convert None to "null" for display
            if result is None:
                return "null"
            return result
        except NoobieError:
            raise
        except Exception as e:
            raise NoobieError(f"error evaluating expression: {e}")
    
    def _reconstruct_string_from_parts(self, parts: List[str], start_index: int) -> str:
        """Reconstruct a string from mixed quoted and unquoted parts"""
        result_parts = []
        i = start_index
        
        while i < len(parts):
            part = parts[i]
            
            # If it's a quoted string, add it as is (removing quotes)
            if (part.startswith('"') and part.endswith('"')) or \
               (part.startswith("'") and part.endswith("'")):
                result_parts.append(part[1:-1])  # Remove quotes
            # If it's a variable name, convert it to @variable format
            else:
                # Check if it's the special END variable (case insensitive)
                if part.lower() == "end":
                    result_parts.append("@end")
                else:
                    result_parts.append(f"@{part}")
            
            i += 1
        
        return ''.join(result_parts)
    
    def _parse_mixed_string_command(self, parts: List[str], start_index: int) -> str:
        """Parse a command that can have mixed quoted strings and variables"""
        # Check if this looks like a traditional single quoted string
        joined = ' '.join(parts[start_index:])
        
        # If it starts and ends with quotes and doesn't contain unquoted variable names, treat as traditional
        if ((joined.startswith('"') and joined.endswith('"')) or 
            (joined.startswith("'") and joined.endswith("'"))):
            # Check if it's a simple quoted string without mixed parts
            quote_char = joined[0]
            # Count quotes to see if it's just one quoted string
            quote_count = joined.count(quote_char)
            if quote_count == 2:  # Opening and closing quote only
                return joined[1:-1]  # Return without quotes, will be processed normally
        
        # Otherwise, reconstruct from parts preserving original spacing
        return self._reconstruct_from_original_line(parts, start_index)
    
    def _reconstruct_from_original_line(self, parts: List[str], start_index: int) -> str:
        """Reconstruct string from original line, preserving only spaces inside quotes"""
        # Join the parts back with spaces, then parse more carefully
        original = ' '.join(parts[start_index:])
        result = ""
        i = 0
        
        while i < len(original):
            if original[i] in ['"', "'"]:
                # Found start of quoted string
                quote_char = original[i]
                i += 1  # Skip opening quote
                # Find matching closing quote and preserve all content inside including spaces
                quote_content = ""
                while i < len(original) and original[i] != quote_char:
                    quote_content += original[i]
                    i += 1
                if i < len(original):  # Skip closing quote
                    i += 1
                result += quote_content
            elif original[i].isspace():
                # Skip spaces between parts (don't preserve them)
                i += 1
            else:
                # Found start of variable name
                var_name = ""
                while i < len(original) and not original[i].isspace() and original[i] not in ['"', "'"]:
                    var_name += original[i]
                    i += 1
                
                # Handle special END variable (case insensitive)
                if var_name.lower() == "end":
                    result += "@end"
                else:
                    result += f"@{var_name}"
        
        return result
    
    def _extract_expression(self, message: str) -> str:
        """Extract and execute expressions in curly braces"""
        # First handle the special \\n sequence for END variable
        message = message.replace("\\n", "\n")
        
        pattern = r'\{([^{}]+)\}'
        
        while re.search(pattern, message):
            match = re.search(pattern, message)
            if not match:
                break
            
            expression = match.group(1)
            result = self._evaluate_expression_with_parentheses(expression)
            message = message[:match.start()] + str(result) + message[match.end():]
        
        return message
    
    def _evaluate_condition(self, condition: str) -> bool:
        """Evaluate a condition and return boolean result"""
        # Replace variables with their values
        condition = replace_variables(condition, self.variables)
        
        try:
            result = self._evaluate_expression_with_parentheses(condition)
            
            # Convert result to boolean
            if isinstance(result, str):
                if result.lower() in ['true', 'false']:
                    return result.lower() == 'true'
                # Non-empty strings are truthy
                return bool(result.strip())
            elif isinstance(result, (int, float)):
                return result != 0
            else:
                return bool(result)
                
        except Exception as e:
            raise NoobieError(f"error evaluating condition '{condition}': {e}")
    
    def _find_matching_endo(self, lines: List[str], start_index: int, block_type: str = "if") -> int:
        """Find the matching ENDO for an IF or WHILE statement"""
        block_count = 1
        for i in range(start_index + 1, len(lines)):
            line = lines[i].strip().lower()
            if line.startswith('if ') or line.startswith('while '):
                block_count += 1
            elif line == 'endo':
                block_count -= 1
                if block_count == 0:
                    return i
        
        raise NoobieError(f"missing ENDO for {block_type.upper()} statement")
    
    def _find_else_in_block(self, lines: List[str], start_index: int, end_index: int) -> Optional[int]:
        """Find ELSE at the same nesting level within an IF block"""
        block_count = 0
        for i in range(start_index + 1, end_index):
            line = lines[i].strip().lower()
            if line.startswith('if ') or line.startswith('while '):
                block_count += 1
            elif line == 'endo':
                block_count -= 1
            elif line == 'else' and block_count == 0:
                return i
        
        return None
    
    def _handle_if(self, parts: List[str], line_number: int):
        """Handle IF command - this is called when we encounter IF in single-line mode"""
        raise NoobieError("IF command should be handled in multiline context")
    
    def _handle_while(self, parts: List[str], line_number: int):
        """Handle WHILE command - this is called when we encounter WHILE in single-line mode"""
        raise NoobieError("WHILE command should be handled in multiline context")
    
    def _execute_if_else_block(self, condition: str, if_lines: List[str], else_lines: Optional[List[str]] = None):
        """Execute an IF/ELSE block based on condition"""
        if self._evaluate_condition(condition):
            # Execute IF block
            if if_lines:
                block_code = '\n'.join(if_lines)
                temp_interpreter = NoobieInterpreter()
                temp_interpreter.variables = self.variables.copy()  # Share variables
                temp_interpreter.interpret(block_code)
                # Update our variables with any changes
                self.variables.update(temp_interpreter.variables)
        else:
            # Execute ELSE block if it exists
            if else_lines:
                block_code = '\n'.join(else_lines)
                temp_interpreter = NoobieInterpreter()
                temp_interpreter.variables = self.variables.copy()  # Share variables
                temp_interpreter.interpret(block_code)
                # Update our variables with any changes
                self.variables.update(temp_interpreter.variables)
    
    def _execute_while_block(self, condition: str, while_lines: List[str], max_iterations: int = 10000):
        """Execute a WHILE block repeatedly while condition is true"""
        iteration_count = 0
        
        while self._evaluate_condition(condition):
            # Safety check to prevent infinite loops
            iteration_count += 1
            if iteration_count > max_iterations:
                raise NoobieError(f"WHILE loop exceeded maximum iterations ({max_iterations}). Possible infinite loop.")
            
            # Execute WHILE block
            if while_lines:
                block_code = '\n'.join(while_lines)
                temp_interpreter = NoobieInterpreter()
                temp_interpreter.variables = self.variables.copy()  # Share variables
                temp_interpreter.interpret(block_code)
                # Update our variables with any changes
                self.variables.update(temp_interpreter.variables)
    
    def _handle_exit(self, parts: List[str], line_number: int):
        """Handle EXIT command"""
        if len(parts) == 1:
            sys.exit(0)
        elif len(parts) >= 2:
            # Parse message (supporting both traditional and decomposed strings)
            message = self._parse_mixed_string_command(parts, 1)
            message = replace_variables(message, self.variables)
            message = self._extract_expression(message)
            print(message, end='')  # Rimuove l'andata a capo automatica
            sys.exit(0)
        else:
            raise NoobieError("EXIT command requires at most one argument")
    
    def _handle_say(self, parts: List[str], line_number: int):
        """Handle SAY command"""
        if len(parts) < 2:
            raise NoobieError("SAY command requires a message")
        
        # Parse message (supporting both traditional and decomposed strings)
        message = self._parse_mixed_string_command(parts, 1)
        message = replace_variables(message, self.variables)
        message = self._extract_expression(message)
        print(message, end='')  # Rimuove l'andata a capo automatica
    
    def _validate_bool_value(self, value_str: str) -> bool:
        """Validate and convert BOOL value, accepting only true, false, null (case insensitive)"""
        value_lower = value_str.lower().strip()
        if value_lower == "true":
            return True
        elif value_lower == "false":
            return False
        elif value_lower == "null":
            return False  # null is treated as false for BOOL
        else:
            raise NoobieError(f"BOOL variables only accept 'true', 'false', or 'null' (case insensitive), got: '{value_str}'")
    
    def _handle_create(self, parts: List[str], line_number: int):
        """Handle CREATE command with improved parsing for expressions in braces and variable references"""
        if len(parts) < 3:
            raise NoobieError("CREATE command requires at least 2 arguments")
        
        # Check if CONST is specified
        is_const = parts[1].lower() == 'const'
        offset = 2 if is_const else 1
        
        if len(parts) < offset + 2:
            raise NoobieError(f"CREATE {'CONST ' if is_const else ''}command requires type and variable name")
        
        var_type = parts[offset].upper()
        var_name = parts[offset + 1].lower()
        
        # Check for reserved variable names (case insensitive)
        if var_name.lower() == "end":
            raise NoobieError("cannot use 'end' as variable name (reserved for newline)")
        
        # Check if variable is already a constant
        if var_name in self.variables and self.variables[var_name].const:
            raise NoobieError(f"cannot redeclare constant variable: '{var_name}'")
        
        # Handle value assignment
        if len(parts) > offset + 2:
            # Join the remaining parts to handle expressions with spaces
            value_raw = ' '.join(parts[offset + 2:])
            
            # Check if the value is an expression in braces
            if value_raw.startswith('{') and value_raw.endswith('}'):
                # Extract and evaluate the expression
                expression = value_raw[1:-1]  # Remove the braces
                try:
                    evaluated_value = self._evaluate_expression_with_parentheses(expression)
                    
                    # Convert the evaluated result to the specified type if needed
                    if var_type == "INT" and isinstance(evaluated_value, (int, float)):
                        value = int(evaluated_value)
                    elif var_type == "FLOAT" and isinstance(evaluated_value, (int, float)):
                        value = float(evaluated_value)
                    elif var_type == "STR":
                        value = str(evaluated_value)
                    elif var_type == "BOOL":
                        if isinstance(evaluated_value, str):
                            value = self._validate_bool_value(evaluated_value)
                        else:
                            value = bool(evaluated_value)
                    elif var_type == "CHAR":
                        if isinstance(evaluated_value, str) and len(evaluated_value) == 1:
                            value = evaluated_value
                        elif isinstance(evaluated_value, (int, float)):
                            ascii_val = int(evaluated_value)
                            if 0 <= ascii_val <= 127:
                                value = chr(ascii_val)
                            else:
                                raise NoobieError("CHAR ASCII value must be between 0 and 127")
                        else:
                            raise NoobieError(f"cannot convert expression result to {var_type}")
                    else:
                        value = evaluated_value
                        
                except Exception as e:
                    raise NoobieError(f"error evaluating expression in CREATE command: {e}")
            else:
                # Handle variable references by replacing variables first
                value_with_vars_replaced = replace_variables(value_raw, self.variables)
                
                # Special validation for BOOL type
                if var_type == "BOOL":
                    value = self._validate_bool_value(value_with_vars_replaced)
                else:
                    # Handle regular value assignment
                    value = initialize_variable(var_type, value_with_vars_replaced)
        else:
            # No value provided, use default
            value = initialize_variable(var_type, None)
        
        # Create the variable
        self.variables[var_name] = Variable(var_type, value, is_const)
    
    def _handle_listen(self, parts: List[str], line_number: int):
        """Handle LISTEN command with new syntax: LISTEN <type> [<variable_name>] "prompt" """
        if len(parts) < 3:
            raise NoobieError("LISTEN command requires at least type and prompt")
        
        var_type = parts[1].upper()
        
        # Check if var_type is valid
        if var_type not in [t.value for t in DataType]:
            raise NoobieError(f"unsupported type: {var_type}")
        
        # Simple logic: if the third part starts with a quote, no variable name was provided
        if parts[2].startswith('"') or parts[2].startswith("'"):
            # listen <type> "prompt..."
            var_name = "listened"
            prompt = self._parse_mixed_string_command(parts, 2)
        else:
            # listen <type> <var_name> "prompt..."
            var_name = parts[2].lower()
            # Check if var_name is reserved
            if var_name.lower() == "end":
                raise NoobieError("cannot use 'end' as variable name (reserved for newline)")
            prompt = self._parse_mixed_string_command(parts, 3)
        
        # Check if variable is already a constant
        if var_name in self.variables and self.variables[var_name].const:
            raise NoobieError(f"cannot modify constant variable: '{var_name}'")
        
        # Process the prompt (replace variables and expressions)
        prompt = replace_variables(prompt, self.variables)
        prompt = self._extract_expression(prompt)
        
        # Get user input (senza andata a capo automatica nel prompt)
        user_input = input(prompt)
        
        # Initialize the value with the correct type
        try:
            if var_type == "BOOL":
                value = self._validate_bool_value(user_input)
            else:
                value = initialize_variable(var_type, user_input)
        except NoobieError as e:
            raise NoobieError(f"error converting input to {var_type}: {e}")
        
        # Store the variable
        self.variables[var_name] = Variable(var_type, value)
    
    def _handle_change(self, parts: List[str], line_number: int):
        """Handle CHANGE command with support for variable references"""
        if len(parts) < 3:
            raise NoobieError("CHANGE command requires variable name and new value")
        
        var_name = parts[1].lower()
        new_value_raw = ' '.join(parts[2:])
        
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        if self.variables[var_name].const:
            raise NoobieError(f"cannot modify constant variable: '{var_name}'")
        
        var_type = self.variables[var_name].type
        
        # Handle expressions in braces
        if new_value_raw.startswith('{') and new_value_raw.endswith('}'):
            expression = new_value_raw[1:-1]
            new_value = self._evaluate_expression_with_parentheses(expression)
        else:
            # Handle variable references by replacing variables first
            new_value_with_vars_replaced = replace_variables(new_value_raw, self.variables)
            
            # Special validation for BOOL type
            if var_type == "BOOL":
                new_value = self._validate_bool_value(new_value_with_vars_replaced)
            else:
                new_value = initialize_variable(var_type, new_value_with_vars_replaced)
        
        self.variables[var_name].value = new_value
    
    def _handle_convert(self, parts: List[str], line_number: int):
        """Handle CONVERT command with support for ?variable syntax to get variable type"""
        if len(parts) != 3:
            raise NoobieError("CONVERT command requires variable name and new type")
        
        var_name, new_type_param = parts[1].lower(), parts[2]
        
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        if self.variables[var_name].const:
            raise NoobieError(f"cannot modify constant variable: '{var_name}'")
        
        # Check if new_type_param starts with ? (variable type reference)
        if new_type_param.startswith('?'):
            # Extract variable name after ?
            type_var_name = new_type_param[1:].lower()
            if type_var_name not in self.variables:
                raise NoobieError(f"variable '{type_var_name}' not declared")
            new_type = self.variables[type_var_name].type
        else:
            new_type = new_type_param.upper()
        
        old_var = self.variables[var_name]
        new_value = convert_value(old_var.value, old_var.type, new_type)
        self.variables[var_name] = Variable(new_type, new_value, old_var.const)
    
    def _handle_random(self, parts: List[str], line_number: int):
        """Handle RANDOM command with support for variable references"""
        if len(parts) < 4:
            raise NoobieError("RANDOM command requires type, min, and max values")
        
        var_type = parts[1].upper()
        
        # Parse min value - can be a number or a variable reference
        min_val_str = parts[2]
        if min_val_str.startswith('@'):
            # It's a variable reference
            var_name = min_val_str[1:].lower()
            if var_name not in self.variables:
                raise NoobieError(f"variable '{var_name}' not declared")
            var = self.variables[var_name]
            if var.type not in ['INT', 'FLOAT']:
                raise NoobieError(f"variable '{var_name}' must be INT or FLOAT for RANDOM min value")
            min_val = int(var.value) if var.type == 'INT' else int(var.value)
        else:
            # It's a literal number
            try:
                min_val = int(min_val_str)
            except ValueError:
                raise NoobieError(f"invalid min value for RANDOM: '{min_val_str}'")
        
        # Parse max value - can be a number or a variable reference
        max_val_str = parts[3]
        if max_val_str.startswith('@'):
            # It's a variable reference
            var_name = max_val_str[1:].lower()
            if var_name not in self.variables:
                raise NoobieError(f"variable '{var_name}' not declared")
            var = self.variables[var_name]
            if var.type not in ['INT', 'FLOAT']:
                raise NoobieError(f"variable '{var_name}' must be INT or FLOAT for RANDOM max value")
            max_val = int(var.value) if var.type == 'INT' else int(var.value)
        else:
            # It's a literal number
            try:
                max_val = int(max_val_str)
            except ValueError:
                raise NoobieError(f"invalid max value for RANDOM: '{max_val_str}'")
        
        # Generate random value
        result = randomize(min_val, max_val, var_type)
        
        # Handle output or variable assignment
        if len(parts) == 4:
            print(result)
        elif len(parts) == 5:
            var_name = parts[4].lower()
            if var_name == "end":
                raise NoobieError("cannot use 'end' as variable name (reserved for newline)")
            if var_name in self.variables and self.variables[var_name].const:
                raise NoobieError(f"cannot modify constant variable: '{var_name}'")
            self.variables[var_name] = Variable(var_type, result)
        else:
            raise NoobieError("RANDOM command has too many arguments")
    
    def _handle_round(self, parts: List[str], line_number: int):
        """Handle ROUND command with support for variable references"""
        if len(parts) != 3:
            raise NoobieError("ROUND command requires variable name and precision")
        
        var_name = parts[1].lower()
        
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        if self.variables[var_name].const:
            raise NoobieError(f"cannot modify constant variable: '{var_name}'")
        
        if self.variables[var_name].type != 'FLOAT':
            raise NoobieError("ROUND command requires a FLOAT variable")
        
        # Parse precision - can be a number or a variable reference
        precision_str = parts[2]
        if precision_str.startswith('@'):
            # It's a variable reference
            precision_var_name = precision_str[1:].lower()
            if precision_var_name not in self.variables:
                raise NoobieError(f"variable '{precision_var_name}' not declared")
            precision_var = self.variables[precision_var_name]
            if precision_var.type not in ['INT', 'FLOAT']:
                raise NoobieError(f"variable '{precision_var_name}' must be INT or FLOAT for ROUND precision")
            precision = int(precision_var.value)
        else:
            # It's a literal number
            try:
                precision = int(precision_str)
            except ValueError:
                raise NoobieError(f"invalid precision value for ROUND: '{precision_str}'")
    
        # Validate precision range
        if precision < 0:
            raise NoobieError("ROUND precision cannot be negative")
        
        # Apply rounding
        value = self.variables[var_name].value
        self.variables[var_name].value = round(value, precision)
    
    def _handle_del(self, parts: List[str], line_number: int):
        """Handle DEL command"""
        if len(parts) != 2:
            raise NoobieError("DEL command requires exactly one variable name")
        
        var_name = parts[1].lower()
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        del self.variables[var_name]
    
    def _handle_reset(self, parts: List[str], line_number: int):
        """Handle RESET command"""
        if len(parts) != 2:
            raise NoobieError("RESET command requires exactly one variable name")
        
        var_name = parts[1].lower()
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        var_type = self.variables[var_name].type
        self.variables[var_name].value = initialize_variable(var_type, None)
    
    def _handle_increment(self, parts: List[str], line_number: int):
        """Handle INCREMENT command"""
        if len(parts) != 2:
            raise NoobieError("INCREMENT command requires exactly one variable name")
        
        var_name = parts[1].lower()
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        if self.variables[var_name].type not in ['INT', 'FLOAT']:
            raise NoobieError("INCREMENT requires INT or FLOAT variable")
        
        self.variables[var_name].value += 1
    
    def _handle_decrement(self, parts: List[str], line_number: int):
        """Handle DECREMENT command"""
        if len(parts) != 2:
            raise NoobieError("DECREMENT command requires exactly one variable name")
        
        var_name = parts[1].lower()
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        if self.variables[var_name].type not in ['INT', 'FLOAT']:
            raise NoobieError("DECREMENT requires INT or FLOAT variable")
        
        self.variables[var_name].value -= 1
    
    def _handle_swap(self, parts: List[str], line_number: int):
        """Handle SWAP command"""
        if len(parts) != 3:
            raise NoobieError("SWAP command requires exactly two variable names")
        
        var1, var2 = parts[1].lower(), parts[2].lower()
        
        if var1 not in self.variables or var2 not in self.variables:
            raise NoobieError("both variables must be declared")
        
        if self.variables[var1].type != self.variables[var2].type:
            raise NoobieError("both variables must have the same type")
        
        self.variables[var1].value, self.variables[var2].value = \
            self.variables[var2].value, self.variables[var1].value
    
    def _handle_string_operation(self, parts: List[str], line_number: int, operation: str):
        """Generic handler for string operations"""
        if len(parts) != 2:
            raise NoobieError(f"{operation} command requires exactly one variable name")
        
        var_name = parts[1].lower()
        if var_name not in self.variables:
            raise NoobieError(f"variable '{var_name}' not declared")
        
        var_type = self.variables[var_name].type
        valid_types = ['CHAR', 'STR'] if operation != 'REVERSE' else ['STR']
        
        if var_type not in valid_types:
            type_str = " or ".join(valid_types)
            raise NoobieError(f"{operation} command requires a {type_str} variable")
        
        value = self.variables[var_name].value
        
        if operation == 'UPPERCASE':
            result = value.upper()
        elif operation == 'LOWERCASE':
            result = value.lower()
        elif operation == 'REVERSE':
            result = value[::-1]
        
        self.variables[var_name].value = result
    
    def _handle_uppercase(self, parts: List[str], line_number: int):
        """Handle UPPERCASE command"""
        self._handle_string_operation(parts, line_number, 'UPPERCASE')
    
    def _handle_lowercase(self, parts: List[str], line_number: int):
        """Handle LOWERCASE command"""
        self._handle_string_operation(parts, line_number, 'LOWERCASE')
    
    def _handle_reverse(self, parts: List[str], line_number: int):
        """Handle REVERSE command"""
        self._handle_string_operation(parts, line_number, 'REVERSE')
    
    def _process_line(self, line: str, line_number: int):
        """Process a single line of code"""
        # Handle comment blocks
        if line.startswith('##'):
            if not self.in_comment_block:
                self.in_comment_block = True
                return
            else:
                self.in_comment_block = False
                return
        
        if self.in_comment_block:
            return
        
        # Remove single-line comments and strip whitespace
        line = line.split('#', 1)[0].strip()
        if not line:
            return
        
        # Store the original line for processing
        original_line = line
        
        # Parse command - preserve original case for parsing
        parts = original_line.split()
        if not parts:
            return
        
        # Convert only the command to lowercase, preserve case for arguments
        command = parts[0].lower()
        
        # Create new parts list with lowercase command but original case arguments
        processed_parts = [command] + parts[1:]
        
        # For variable replacement, we need to be careful about preserving string content
        # Only replace variables in the line, not in quoted strings
        line_for_variable_replacement = self._replace_variables_preserve_strings(original_line)
        
        # Handle commands using command handlers
        if command in self.command_handlers:
            try:
                self.command_handlers[command](processed_parts, line_number)
            except NoobieError:
                raise
            except Exception as e:
                raise NoobieError(f"Error in {command.upper()} command: {e}")
        
        # Handle arithmetic expressions
        elif any(op in line_for_variable_replacement for op in ['+', '-', '*', '/', '//', '%', '**', '==', '!=', '<', '>', 
                                    'AND', 'OR', 'NOT', 'XOR', 'and', 'or', 'not', 'xor']):
            try:
                result = self._evaluate_expression_with_parentheses(line_for_variable_replacement)
                # Handle None result by printing "null"
                if result is None:
                    print("null")
                else:
                    print(result)
            except NoobieError:
                raise
        else:
            raise NoobieError(f"Unknown command: {command}")
        
    def _replace_variables_preserve_strings(self, line: str) -> str:
        """Replace variables but preserve content inside quoted strings"""
        result = ""
        i = 0
        
        while i < len(line):
            if line[i] in ['"', "'"]:
                # Found start of quoted string - preserve everything inside
                quote_char = line[i]
                result += line[i]  # Add opening quote
                i += 1
                
                # Copy everything until closing quote
                while i < len(line) and line[i] != quote_char:
                    result += line[i]
                    i += 1
                
                if i < len(line):
                    result += line[i]  # Add closing quote
                    i += 1
            else:
                # Not in quotes, process normally for variable replacement
                char_added = False
                # Check if this could be start of a variable reference
                if line[i] in ['@', '?']:
                    # Find the variable name
                    var_start = i
                    i += 1
                    while i < len(line) and (line[i].isalnum() or line[i] == '_'):
                        i += 1
                    var_part = line[var_start:i]
                    
                    # Apply variable replacement to this part only
                    replaced = replace_variables(var_part, self.variables)
                    result += replaced
                    char_added = True
                
                if not char_added:
                    result += line[i]
                    i += 1
        
        return result
    
    def interpret(self, code: str):
        """Main interpretation method with IF/ELSE and WHILE support"""
        try:
            lines = code.splitlines()
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                line_number = i + 1
                
                # Skip empty lines
                if not line:
                    i += 1
                    continue
                
                # Handle comment blocks
                if line.startswith('##'):
                    if not self.in_comment_block:
                        self.in_comment_block = True
                    else:
                        self.in_comment_block = False
                    i += 1
                    continue
                
                if self.in_comment_block:
                    i += 1
                    continue
                
                # Remove single-line comments
                line = line.split('#', 1)[0].strip()
                if not line:
                    i += 1
                    continue
                
                # Check for IF statement
                if line.lower().startswith('if '):
                    # Extract condition
                    if_parts = line.split()
                    if len(if_parts) < 3 or if_parts[-1].lower() != 'do':
                        raise NoobieError("IF statement must end with DO", line_number)
                    
                    # Extract condition (everything between IF and DO)
                    condition = ' '.join(if_parts[1:-1])
                    
                    # Find matching ENDO
                    try:
                        endo_index = self._find_matching_endo(lines, i, "if")
                    except NoobieError as e:
                        e.line_number = line_number
                        raise
                    
                    # Find ELSE within this block (if exists)
                    else_index = self._find_else_in_block(lines, i, endo_index)
                    
                    # Extract IF block lines
                    if_end_index = else_index if else_index else endo_index
                    if_lines = []
                    for j in range(i + 1, if_end_index):
                        block_line = lines[j].strip()
                        if block_line:  # Skip empty lines in block
                            if_lines.append(block_line)
                    
                    # Extract ELSE block lines (if exists)
                    else_lines = []
                    if else_index:
                        for j in range(else_index + 1, endo_index):
                            block_line = lines[j].strip()
                            if block_line:  # Skip empty lines in block
                                else_lines.append(block_line)
                    
                    # Execute IF/ELSE block
                    try:
                        self._execute_if_else_block(condition, if_lines, else_lines if else_lines else None)
                    except NoobieError as e:
                        if e.line_number is None:
                            e.line_number = line_number
                        raise
                    
                    # Skip to after ENDO
                    i = endo_index + 1
                
                # Check for WHILE statement
                elif line.lower().startswith('while '):
                    # Extract condition
                    while_parts = line.split()
                    if len(while_parts) < 3 or while_parts[-1].lower() != 'do':
                        raise NoobieError("WHILE statement must end with DO", line_number)
                    
                    # Extract condition (everything between WHILE and DO)
                    condition = ' '.join(while_parts[1:-1])
                    
                    # Find matching ENDO
                    try:
                        endo_index = self._find_matching_endo(lines, i, "while")
                    except NoobieError as e:
                        e.line_number = line_number
                        raise
                    
                    # Extract WHILE block lines
                    while_lines = []
                    for j in range(i + 1, endo_index):
                        block_line = lines[j].strip()
                        if block_line:  # Skip empty lines in block
                            while_lines.append(block_line)
                    
                    # Execute WHILE block
                    try:
                        self._execute_while_block(condition, while_lines)
                    except NoobieError as e:
                        if e.line_number is None:
                            e.line_number = line_number
                        raise
                    
                    # Skip to after ENDO
                    i = endo_index + 1
                
                # Skip ELSE and ENDO lines (they're handled by IF/WHILE processing)
                elif line.lower() in ['else', 'endo']:
                    # These should only appear within IF/WHILE blocks
                    if line.lower() == 'else':
                        raise NoobieError("ELSE without matching IF", line_number)
                    elif line.lower() == 'endo':
                        raise NoobieError("ENDO without matching IF or WHILE", line_number)
                    i += 1
                
                # Process other lines normally
                else:
                    try:
                        self._process_line(line, line_number)
                    except NoobieError as e:
                        e.line_number = line_number
                        raise
                    i += 1
                    
        except NoobieError as e:
            handle_error(str(e), e.line_number)
        except Exception as e:
            handle_error(f"Unexpected error: {e}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        handle_error("Specify a .noob file")
    
    filename = sys.argv[1]
    
    try:
        code = read_code_from_file(filename)
        interpreter = NoobieInterpreter()
        interpreter.interpret(code)
    except NoobieError as e:
        handle_error(str(e))
    except Exception as e:
        handle_error(f"Error reading file: {e}")

if __name__ == '__main__':
    main()
