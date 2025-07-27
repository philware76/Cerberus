import argparse
import ast
import inspect
import shlex
from typing import Dict, Union
from cmdShells.basePluginShell import BasePluginShell
from plugins.basePlugin import BasePlugin
from testManager import TestManager

def get_base_methods(base_cls):
    return {
        name: method
        for name, method in inspect.getmembers(base_cls, predicate=inspect.isfunction)
        if not name.startswith('_') and (name.startswith("set") or name.startswith("get"))
    }

class SilentArgParser(argparse.ArgumentParser):
    def __init__(self, prog, add_help):
        super().__init__(prog=prog, add_help=add_help)

    def error(self, message):
        # Raise a clean exception instead of printing to stderr
        raise argparse.ArgumentError(None, message)

class RunCommandShell(BasePluginShell):
    def __init__(self, plugin:BasePlugin, manager: TestManager):
        super().__init__(plugin, manager)

        self.base_cls = plugin.__class__.__bases__[0]
        self.allowed_methods = get_base_methods(self.base_cls)
        self.parsers = self._buildParsers()

    def _buildParsers(self) -> Dict[str, argparse.ArgumentParser]:
        """Build ArgumentParsers for each allowed method based on its signature."""
        parsers = {}

        for name, method in self.allowed_methods.items():
            sig = inspect.signature(method)
            parser = SilentArgParser(prog=name, add_help=False)
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue

                # Check if parameter is Optional
                is_optional = self._is_optional_type(param.annotation)

                if is_optional:
                    # Optional parameters become optional arguments with --
                    parser.add_argument(f'--{param_name}', type=self._safe_eval_type, default=None)
                else:
                    # Required parameters remain positional
                    parser.add_argument(param_name, type=self._safe_eval_type)

            parsers[name] = parser

        return parsers

    def _is_optional_type(self, annotation):
        """Check if a type annotation represents an Optional type."""
        if annotation == inspect.Parameter.empty:
            return False

        # Check for typing.Optional or typing.Union[X, None]
        origin = getattr(annotation, '__origin__', None)
        if origin is Union:
            args = getattr(annotation, '__args__', ())
            # Optional[X] is equivalent to Union[X, None]
            return type(None) in args

        return False

    def _safe_eval_type(self, value):
        """Safely evaluate Python literals, fall back to string."""
        try:
            return ast.literal_eval(value)
        except (ValueError, SyntaxError):
            return value

    def default(self, line):
        try:
            parts = shlex.split(line.strip())
        except ValueError as e:
            print(f"Error parsing command: {e}")
            return

        if not parts:
            raise ValueError("No arguments!")

        method_name = parts[0]
        args = parts[1:]

        if method_name not in self.allowed_methods:
            print(f"Error: '{method_name}' is not a valid command.")
            return

        parser = self.parsers[method_name]
        try:
            parsed_args = parser.parse_args(args)
            arg_values = vars(parsed_args)
            if 'self' in arg_values:
                del arg_values['self']

            method = getattr(self.equip, method_name)
            method(**arg_values)

        except SystemExit:
            pass
        
        except argparse.ArgumentError:
            print(self.parsers[method_name].format_usage().strip())
            
        except Exception as e:
            print(f"Error calling method: {e}")
        
    def _format_type_annotation(self, annotation):
        """Format type annotation for clean display."""
        if annotation == inspect.Parameter.empty:
            return None

        # Convert to string and clean up common patterns
        type_str = str(annotation)

        # Remove 'typing.' prefix
        type_str = type_str.replace('typing.', '')

        # Handle <class 'type'> format
        if type_str.startswith("<class '") and type_str.endswith("'>"):
            type_str = type_str[8:-2]  # Remove <class '...'> wrapper

        return type_str

    def do_cmds(self, cmd):
        """List the commands this plugin can execute"""
        if not cmd:
            print("Available commands:-")
            for method_name, method in self.allowed_methods.items():
                sig = inspect.signature(method)

                # Build parameter list, excluding 'self'
                params = []
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue

                    # Add type annotation if available
                    formatted_type = self._format_type_annotation(param.annotation)
                    if formatted_type:
                        params.append(f"{param_name}: {formatted_type}")
                    else:
                        params.append(param_name)

                # Join parameters with spaces or commas as you prefer
                param_str = ' '.join(params)

                print(f"  {method_name} {param_str}")

            print()

        elif cmd in self.parsers:
            print(self.parsers[cmd].format_usage().strip())
            
        else:
            print(f"No help available for '{cmd}'.")