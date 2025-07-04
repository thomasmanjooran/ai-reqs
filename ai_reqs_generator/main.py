import os
import json
import ast
import sys
import argparse
from importlib import metadata
import urllib.request
import urllib.error
import re

# --- Configuration ---

# A list of Python's standard libraries.
STANDARD_LIBRARIES = {
    'abc', 'aifc', 'argparse', 'array', 'ast', 'asynchat', 'asyncio',
    'asyncore', 'atexit', 'audioop', 'base64', 'bdb', 'binascii', 'binhex',
    'bisect', 'builtins', 'bz2', 'calendar', 'cgi', 'cgitb', 'chunk', 'cmath',
    'cmd', 'code', 'codecs', 'codeop', 'collections', 'colorsys', 'compileall',
    'concurrent', 'configparser', 'contextlib', 'contextvars', 'copy',
    'copyreg', 'cProfile', 'crypt', 'csv', 'ctypes', 'curses', 'dataclasses',
    'datetime', 'dbm', 'decimal', 'difflib', 'dis', 'distutils', 'doctest',
    'email', 'encodings', 'ensurepip', 'enum', 'errno', 'faulthandler', 'fcntl',
    'filecmp', 'fileinput', 'fnmatch', 'formatter', 'fractions', 'ftplib',
    'functools', 'gc', 'getopt', 'getpass', 'gettext', 'glob', 'graphlib',
    'grp', 'gzip', 'hashlib', 'heapq', 'hmac', 'html', 'http', 'imaplib',
    'imghdr', 'imp', 'importlib', 'inspect', 'io', 'ipaddress', 'itertools',
    'json', 'keyword', 'lib2to3', 'linecache', 'locale', 'logging', 'lzma',
    'mailbox', 'mailcap', 'marshal', 'math', 'mimetypes', 'mmap', 'modulefinder',
    'multiprocessing', 'netrc', 'nis', 'nntplib', 'numbers', 'operator', 'optparse',
    'os', 'ossaudiodev', 'parser', 'pathlib', 'pdb', 'pickle', 'pickletools',
    'pipes', 'pkgutil', 'platform', 'plistlib', 'poplib', 'posix', 'pprint',
    'profile', 'pstats', 'pty', 'pwd', 'py_compile', 'pyclbr', 'pydoc', 'queue',
    'quopri', 'random', 're', 'readline', 'reprlib', 'resource', 'rlcompleter',
    'runpy', 'sched', 'secrets', 'select', 'selectors', 'shelve', 'shlex',
    'shutil', 'signal', 'site', 'smtpd', 'smtplib', 'sndhdr', 'socket',
    'socketserver', 'spwd', 'sqlite3', 'ssl', 'stat', 'statistics', 'string',
    'stringprep', 'struct', 'subprocess', 'sunau', 'symtable', 'sys',
    'sysconfig', 'syslog', 'tabnanny', 'tarfile', 'telnetlib', 'tempfile',
    'termios', 'textwrap', 'threading', 'time', 'timeit', 'tkinter', 'token',
    'tokenize', 'trace', 'traceback', 'tracemalloc', 'tty', 'turtle', 'turtledemo',
    'types', 'typing', 'unicodedata', 'unittest', 'urllib', 'uu', 'uuid',
    'venv', 'warnings', 'wave', 'weakref', 'webbrowser', 'wsgiref', 'xdrlib',
    'xml', 'xmlrpc', 'zipapp', 'zipfile', 'zipimport', 'zlib', 'zoneinfo'
}

# --- LLM Integration ---

def extract_json_from_string(text):
    """
    Finds and extracts a JSON object from a string that might contain other text,
    like markdown code fences.
    """
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        return match.group(1)
    try:
        start = text.index('{')
        end = text.rindex('}') + 1
        return text[start:end]
    except ValueError:
        return None

def resolve_imports_with_llm(modules_to_resolve, api_key):
    """
    Uses the Gemini API to find the pip package names for a list of import names.
    """
    if not api_key:
        print("\nWarning: No API key provided. Skipping AI resolution.", file=sys.stderr)
        return {}
        
    print(f"\nAttempting to resolve {len(modules_to_resolve)} modules with AI: {', '.join(modules_to_resolve)}")
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    
    prompt = (
        "You are an expert Python developer. For each Python import name in the following list, "
        "provide the corresponding official package name that is used for 'pip install'. "
        "Your response must be a single, valid JSON object where keys are the import names "
        "and values are the package names. If a package name cannot be found for an import, "
        f"use a null value. The list of import names is: {list(modules_to_resolve)}"
    )
    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(api_url, data=data, headers={'Content-Type': 'application/json'})

    try:
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode('utf-8')
            result = json.loads(response_body)
            
            if (result.get('candidates') and result['candidates'][0].get('content') and 
                result['candidates'][0]['content'].get('parts') and 
                result['candidates'][0]['content']['parts'][0].get('text')):
                
                content_text = result['candidates'][0]['content']['parts'][0]['text']
                json_string = extract_json_from_string(content_text)
                
                if json_string:
                    llm_mappings = json.loads(json_string)
                    print("AI resolution successful.")
                    return llm_mappings
                else:
                    print("AI Warning: Could not find a valid JSON object in the response.", file=sys.stderr)
                    return {}
            else:
                print("AI Warning: Response format was unexpected.", file=sys.stderr)
                return {}
    except urllib.error.HTTPError as e:
        print(f"AI Error: HTTP Error {e.code}. Check your API key and permissions.", file=sys.stderr)
        return {}
    except urllib.error.URLError as e:
        print(f"AI Error: Could not connect to the API. {e.reason}", file=sys.stderr)
        return {}
    except json.JSONDecodeError as e:
        print(f"AI Error: Could not parse the JSON response from the API. Error: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"An unexpected error occurred during AI resolution: {e}", file=sys.stderr)
        return {}

# --- Core Logic ---

class ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports = set()

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.add(alias.name.split('.')[0])
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.add(node.module.split('.')[0])
        self.generic_visit(node)

def get_imports_from_code(code):
    try:
        tree = ast.parse(code)
        visitor = ImportVisitor()
        visitor.visit(tree)
        return visitor.imports
    except SyntaxError as e:
        print(f"Warning: Skipping a code block due to syntax error: {e}", file=sys.stderr)
        return set()

def get_imports_from_py(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
        return get_imports_from_code(code)
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        return set()

def get_imports_from_ipynb(file_path):
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            notebook = json.load(f)
        code_cells = [cell['source'] for cell in notebook.get('cells', []) if cell.get('cell_type') == 'code']
        for cell_source in code_cells:
            full_source = "".join(cell_source)
            imports.update(get_imports_from_code(full_source))
    except Exception as e:
        print(f"Error processing notebook {file_path}: {e}", file=sys.stderr)
    return imports

def get_distribution_packages():
    mapping = {}
    try:
        dist_map = metadata.packages_distributions()
        for package, modules in dist_map.items():
            for module in modules:
                mapping[module] = package
    except Exception as e:
        print(f"Warning: Could not automatically map all distributions. {e}", file=sys.stderr)
    return mapping

def run(project_path, api_key):
    """Main function to scan directory, find imports, and generate requirements.txt."""
    print(f"Starting scan in '{project_path}'...")
    all_imports = set()

    for root, _, files in os.walk(project_path):
        if any(d in root for d in ['venv', 'env', '.git', '.ipynb_checkpoints']):
            continue
        for file in files:
            file_path = os.path.join(root, file)
            if file.endswith('.py'):
                all_imports.update(get_imports_from_py(file_path))
            elif file.endswith('.ipynb'):
                all_imports.update(get_imports_from_ipynb(file_path))

    print(f"\nScan complete. Found {len(all_imports)} potential imports.")
    external_imports = sorted(list(all_imports - STANDARD_LIBRARIES))
    print(f"Found {len(external_imports)} external modules to resolve.")

    module_to_package_map = get_distribution_packages()
    requirements = set()
    unresolved_modules = set()

    for module_name in external_imports:
        package_name = module_to_package_map.get(module_name)
        if package_name:
            requirements.add(package_name)
        else:
            try:
                metadata.version(module_name)
                requirements.add(module_name)
            except metadata.PackageNotFoundError:
                unresolved_modules.add(module_name)
    
    if unresolved_modules:
        llm_mappings = resolve_imports_with_llm(unresolved_modules, api_key)
        still_unresolved = set()
        for module, package in llm_mappings.items():
            if package:
                print(f"  - AI resolved '{module}' to '{package}'")
                requirements.add(package)
            else:
                still_unresolved.add(module)
        unresolved_modules = still_unresolved

    if not requirements:
        print("\nNo external packages found. requirements.txt will not be created.")
        return

    output_lines = []
    print("\nGenerating requirements.txt with versions...")
    for package in sorted(list(requirements)):
        try:
            version = metadata.version(package)
            line = f"{package}=={version}"
            print(f"  - Found: {line}")
            output_lines.append(line)
        except metadata.PackageNotFoundError:
            print(f"  - Warning: Could not find version for '{package}'. It may be a namespace package or part of another.", file=sys.stderr)

    output_path = os.path.join(project_path, 'requirements.txt')
    try:
        with open(output_path, 'w') as f:
            f.write("# Generated by AI-Reqs\n")
            f.write("\n".join(output_lines))
            f.write("\n")
        print(f"\nSuccessfully created {output_path}!")
    except IOError as e:
        print(f"\nError: Could not write to {output_path}. {e}", file=sys.stderr)

    if unresolved_modules:
        print("\n--- ATTENTION ---", file=sys.stderr)
        print("The following imports could not be resolved automatically or by AI.", file=sys.stderr)
        for module in unresolved_modules:
            print(f"  - {module}", file=sys.stderr)
        print("-------------------", file=sys.stderr)

def main():
    """Entry point for the command-line tool."""
    parser = argparse.ArgumentParser(
        description="Generate a requirements.txt file for a Python project using AI for dependency resolution."
    )
    parser.add_argument(
        '--path',
        default='.',
        help='The path to the project directory to scan. Defaults to the current directory.'
    )
    parser.add_argument(
        '--api-key',
        default=os.environ.get('GEMINI_API_KEY'),
        help='Your Gemini API key. Can also be set via the GEMINI_API_KEY environment variable.'
    )
    args = parser.parse_args()
    
    if not args.api_key:
        print("Error: Gemini API key not found.", file=sys.stderr)
        print("Please provide it using the --api-key argument or by setting the GEMINI_API_KEY environment variable.", file=sys.stderr)
        sys.exit(1)
        
    run(args.path, args.api_key)

if __name__ == "__main__":
    main()
