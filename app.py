from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
import subprocess
import tempfile
import os
import threading
import queue
import time
import signal

app = Flask(__name__)
CORS(app)

# Configurazione
INTERPRETER_PATH = "./noobie"  # Path all'eseguibile dell'interprete
MAX_EXECUTION_TIME = 5  # Timeout in secondi per l'esecuzione
MAX_OUTPUT_SIZE = 1024 * 1024  # 1MB max output

# Template HTML integrato
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Noobie IDE Online</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1e1e1e;
            color: #d4d4d4;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background-color: #2d2d30;
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #3e3e42;
        }

        .logo {
            font-size: 20px;
            font-weight: bold;
            color: #007acc;
        }

        .main-container {
            flex: 1;
            display: flex;
            height: calc(100vh - 60px);
        }

        .sidebar {
            width: 250px;
            background-color: #252526;
            border-right: 1px solid #3e3e42;
            padding: 20px;
            overflow-y: auto;
        }

        .editor-section {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .editor-container {
            flex: 1;
            position: relative;
            background-color: #1e1e1e;
        }

        #editor {
            width: 100%;
            height: 100%;
            background-color: #1e1e1e;
            color: #d4d4d4;
            font-family: 'Consolas', 'Courier New', monospace;
            font-size: 14px;
            padding: 20px;
            border: none;
            outline: none;
            resize: none;
            line-height: 1.5;
        }

        .output-section {
            height: 300px;
            background-color: #1e1e1e;
            border-top: 1px solid #3e3e42;
            display: flex;
            flex-direction: column;
        }

        .output-tabs {
            background-color: #2d2d30;
            display: flex;
            border-bottom: 1px solid #3e3e42;
        }

        .tab {
            padding: 8px 20px;
            cursor: pointer;
            border-right: 1px solid #3e3e42;
            transition: background-color 0.2s;
        }

        .tab:hover {
            background-color: #3e3e42;
        }

        .tab.active {
            background-color: #1e1e1e;
            border-bottom: 2px solid #007acc;
        }

        .output-content {
            flex: 1;
            padding: 15px;
            overflow-y: auto;
            font-family: 'Consolas', 'Courier New', monospace;
            white-space: pre-wrap;
        }

        .output-content.error {
            color: #f48771;
        }

        .output-content.success {
            color: #4ec9b0;
        }

        .btn {
            background-color: #007acc;
            color: white;
            border: none;
            padding: 8px 20px;
            cursor: pointer;
            border-radius: 4px;
            font-size: 14px;
            transition: background-color 0.2s;
        }

        .btn:hover {
            background-color: #005a9e;
        }

        .btn:disabled {
            background-color: #3e3e42;
            cursor: not-allowed;
        }

        .example-item {
            background-color: #2d2d30;
            margin-bottom: 10px;
            padding: 10px;
            border-radius: 4px;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .example-item:hover {
            background-color: #3e3e42;
        }

        .example-title {
            font-weight: bold;
            color: #007acc;
            margin-bottom: 5px;
        }

        .example-desc {
            font-size: 12px;
            color: #a0a0a0;
        }

        .input-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }

        .input-modal-content {
            background-color: #2d2d30;
            padding: 20px;
            border-radius: 8px;
            width: 400px;
            max-width: 90%;
        }

        .input-modal h3 {
            margin-bottom: 15px;
            color: #007acc;
        }

        .input-modal textarea {
            width: 100%;
            height: 100px;
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #3e3e42;
            border-radius: 4px;
            padding: 10px;
            font-family: 'Consolas', 'Courier New', monospace;
            resize: vertical;
        }

        .input-modal-buttons {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            justify-content: flex-end;
        }

        .status-indicator {
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 5px;
        }

        .status-indicator.online {
            background-color: #4ec9b0;
        }

        .status-indicator.offline {
            background-color: #f48771;
        }

        .execution-time {
            color: #a0a0a0;
            font-size: 12px;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">Noobie IDE</div>
        <div>
            <span class="status-indicator" id="statusIndicator"></span>
            <span id="statusText">Checking...</span>
            <button class="btn" id="runBtn" onclick="runCode()">▶ Run</button>
        </div>
    </div>

    <div class="main-container">
        <div class="sidebar">
            <h3 style="margin-bottom: 15px; color: #007acc;">Examples</h3>
            <div id="examplesList"></div>
        </div>

        <div class="editor-section">
            <div class="editor-container">
                <textarea id="editor" placeholder="# Write your Noobie code here..."></textarea>
            </div>

            <div class="output-section">
                <div class="output-tabs">
                    <div class="tab active" onclick="switchTab('output')">Output</div>
                    <div class="tab" onclick="switchTab('error')">Errors</div>
                </div>
                <div id="outputContent" class="output-content"></div>
                <div id="errorContent" class="output-content error" style="display: none;"></div>
            </div>
        </div>
    </div>

    <div class="input-modal" id="inputModal">
        <div class="input-modal-content">
            <h3>Program Input Required</h3>
            <p style="margin-bottom: 10px; color: #a0a0a0;">Your program requires input. Enter it below:</p>
            <textarea id="userInput" placeholder="Enter input here..."></textarea>
            <div class="input-modal-buttons">
                <button class="btn" onclick="cancelInput()">Cancel</button>
                <button class="btn" onclick="submitInput()">Submit</button>
            </div>
        </div>
    </div>

    <script>
        const API_URL = '';  // Stesso dominio
        let currentInput = '';
        let awaitingInput = false;

        // Check server status
        async function checkServerStatus() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                
                const indicator = document.getElementById('statusIndicator');
                const text = document.getElementById('statusText');
                
                if (data.status === 'healthy') {
                    indicator.className = 'status-indicator online';
                    text.textContent = 'Server Online';
                    document.getElementById('runBtn').disabled = false;
                } else {
                    indicator.className = 'status-indicator offline';
                    text.textContent = 'Interpreter Not Found';
                    document.getElementById('runBtn').disabled = true;
                }
            } catch (error) {
                const indicator = document.getElementById('statusIndicator');
                const text = document.getElementById('statusText');
                indicator.className = 'status-indicator offline';
                text.textContent = 'Server Offline';
                document.getElementById('runBtn').disabled = true;
            }
        }

        // Load examples
        async function loadExamples() {
            try {
                const response = await fetch('/api/examples');
                const examples = await response.json();
                
                const container = document.getElementById('examplesList');
                container.innerHTML = '';
                
                examples.forEach(example => {
                    const div = document.createElement('div');
                    div.className = 'example-item';
                    div.innerHTML = `
                        <div class="example-title">${example.name}</div>
                        <div class="example-desc">${example.description}</div>
                    `;
                    div.onclick = () => loadExample(example.code);
                    container.appendChild(div);
                });
            } catch (error) {
                console.error('Error loading examples:', error);
            }
        }

        function loadExample(code) {
            document.getElementById('editor').value = code;
        }

        async function runCode() {
            const code = document.getElementById('editor').value;
            
            if (!code.trim()) {
                showError('No code to execute');
                return;
            }

            // Check if code contains LISTEN command
            if (code.toLowerCase().includes('listen')) {
                // Show input modal
                document.getElementById('inputModal').style.display = 'flex';
                document.getElementById('userInput').focus();
                awaitingInput = true;
                return;
            }

            executeCode(code, '');
        }

        async function executeCode(code, input) {
            const runBtn = document.getElementById('runBtn');
            runBtn.disabled = true;
            runBtn.textContent = '⏳ Running...';

            clearOutput();
            switchTab('output');

            try {
                const response = await fetch('/api/execute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ code, input })
                });

                const result = await response.json();

                if (result.success) {
                    showOutput(result.output, result.execution_time);
                } else {
                    showError(result.error || 'Execution failed');
                    if (result.output) {
                        showOutput(result.output, result.execution_time);
                    }
                }
            } catch (error) {
                showError(`Network error: ${error.message}`);
            } finally {
                runBtn.disabled = false;
                runBtn.textContent = '▶ Run';
            }
        }

        function submitInput() {
            const input = document.getElementById('userInput').value;
            const code = document.getElementById('editor').value;
            
            document.getElementById('inputModal').style.display = 'none';
            document.getElementById('userInput').value = '';
            
            executeCode(code, input);
        }

        function cancelInput() {
            document.getElementById('inputModal').style.display = 'none';
            document.getElementById('userInput').value = '';
            awaitingInput = false;
        }

        function showOutput(output, executionTime) {
            const outputContent = document.getElementById('outputContent');
            outputContent.textContent = output || '(No output)';
            
            if (executionTime !== undefined) {
                const timeDiv = document.createElement('div');
                timeDiv.className = 'execution-time';
                timeDiv.textContent = `Execution time: ${executionTime.toFixed(3)}s`;
                outputContent.appendChild(timeDiv);
            }
        }

        function showError(error) {
            const errorContent = document.getElementById('errorContent');
            errorContent.textContent = error;
            switchTab('error');
        }

        function clearOutput() {
            document.getElementById('outputContent').textContent = '';
            document.getElementById('errorContent').textContent = '';
        }

        function switchTab(tab) {
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(t => t.classList.remove('active'));
            
            if (tab === 'output') {
                tabs[0].classList.add('active');
                document.getElementById('outputContent').style.display = 'block';
                document.getElementById('errorContent').style.display = 'none';
            } else {
                tabs[1].classList.add('active');
                document.getElementById('outputContent').style.display = 'none';
                document.getElementById('errorContent').style.display = 'block';
            }
        }

        // Keyboard shortcuts
        document.getElementById('editor').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                runCode();
            }
        });

        document.getElementById('userInput').addEventListener('keydown', (e) => {
            if (e.ctrlKey && e.key === 'Enter') {
                e.preventDefault();
                submitInput();
            }
        });

        // Initialize
        checkServerStatus();
        loadExamples();
        setInterval(checkServerStatus, 5000); // Check every 5 seconds
    </script>
</body>
</html>
"""

class CodeExecutor:
    def __init__(self):
        self.execution_queue = queue.Queue()
        
    def execute_code(self, code, user_input=""):
        """Esegue il codice Noobie e ritorna l'output"""
        result = {
            'output': '',
            'error': '',
            'exit_code': 0,
            'execution_time': 0
        }
        
        start_time = time.time()
        
        try:
            # Crea un file temporaneo per il codice
            with tempfile.NamedTemporaryFile(mode='w', suffix='.noob', delete=False) as f:
                f.write(code)
                temp_filename = f.name
            
            try:
                # Esegui l'interprete
                process = subprocess.Popen(
                    [INTERPRETER_PATH, temp_filename],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Fornisci input se necessario
                stdout, stderr = process.communicate(
                    input=user_input,
                    timeout=MAX_EXECUTION_TIME
                )
                
                # Limita la dimensione dell'output
                if len(stdout) > MAX_OUTPUT_SIZE:
                    stdout = stdout[:MAX_OUTPUT_SIZE] + "\n[Output truncated...]"
                if len(stderr) > MAX_OUTPUT_SIZE:
                    stderr = stderr[:MAX_OUTPUT_SIZE] + "\n[Error output truncated...]"
                
                result['output'] = stdout
                result['error'] = stderr
                result['exit_code'] = process.returncode
                
            except subprocess.TimeoutExpired:
                process.kill()
                result['error'] = f"Execution timeout ({MAX_EXECUTION_TIME} seconds)"
                result['exit_code'] = -1
            
            finally:
                # Rimuovi il file temporaneo
                if os.path.exists(temp_filename):
                    os.unlink(temp_filename)
                    
        except Exception as e:
            result['error'] = f"Server error: {str(e)}"
            result['exit_code'] = -2
        
        result['execution_time'] = time.time() - start_time
        return result

# Istanza globale dell'executor
executor = CodeExecutor()

@app.route('/')
def index():
    """Serve la pagina principale"""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/execute', methods=['POST'])
def execute():
    """Endpoint per eseguire codice Noobie"""
    try:
        data = request.get_json()
        
        if not data or 'code' not in data:
            return jsonify({
                'success': False,
                'error': 'No code provided'
            }), 400
        
        code = data['code']
        user_input = data.get('input', '')
        
        # Esegui il codice
        result = executor.execute_code(code, user_input)
        
        return jsonify({
            'success': result['exit_code'] == 0 and not result['error'],
            'output': result['output'],
            'error': result['error'],
            'exit_code': result['exit_code'],
            'execution_time': result['execution_time']
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint per verificare lo stato del server"""
    try:
        # Verifica che l'interprete esista
        interpreter_exists = os.path.exists(INTERPRETER_PATH)
        interpreter_executable = os.access(INTERPRETER_PATH, os.X_OK) if interpreter_exists else False
        
        return jsonify({
            'status': 'healthy' if interpreter_exists and interpreter_executable else 'unhealthy',
            'interpreter_path': INTERPRETER_PATH,
            'interpreter_exists': interpreter_exists,
            'interpreter_executable': interpreter_executable
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@app.route('/api/examples', methods=['GET'])
def examples():
    """Ritorna esempi di codice Noobie"""
    examples = [
        {
            'name': 'Hello World',
            'description': 'Print a message',
            'code': 'say "Hello, World!" end'
        },
        {
            'name': 'Variables',
            'description': 'Initialize variables',
            'code': '''create str name "Alice"
create int age 25
say "Name: " name end
say "Age: " age end'''
        },
        {
            'name': 'Input',
            'description': 'Read input from the user',
            'code': '''listen str nome "What's your name? "
say "Hi, " nome "!" end '''
        },
        {
            'name': 'Condition',
            'description': 'Use if/else',
            'code': '''create int x 10
if x > 5 DO
    say "x is less then 5" end
else
    say "x is greater or equal 5" end
endo'''
        },
        {
            'name': 'Loop',
            'description': 'Use while',
            'code': '''create int i 1
while i <= 5 DO
    say "I is equal to: " i end
    increment i
endo'''
        }
    ]
    
    return jsonify(examples)

@app.route('/api/validate', methods=['POST'])
def validate():
    """Valida il codice senza eseguirlo (sintassi base)"""
    try:
        data = request.get_json()
        code = data.get('code', '')
        
        # Validazioni base
        errors = []
        warnings = []
        
        lines = code.split('\n')
        if_count = 0
        while_count = 0
        endo_count = 0
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Conta IF/WHILE/ENDO
            if line.lower().startswith('if '):
                if_count += 1
                if not line.lower().endswith(' do'):
                    errors.append(f"Line {i}: IF statement must end with DO")
            elif line.lower().startswith('while '):
                while_count += 1
                if not line.lower().endswith(' do'):
                    errors.append(f"Line {i}: WHILE statement must end with DO")
            elif line.lower() == 'endo':
                endo_count += 1
        
        # Verifica bilanciamento
        expected_endo = if_count + while_count
        if endo_count < expected_endo:
            errors.append(f"Missing {expected_endo - endo_count} ENDO statement(s)")
        elif endo_count > expected_endo:
            errors.append(f"Too many ENDO statements ({endo_count - expected_endo} extra)")
        
        return jsonify({
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        })
        
    except Exception as e:
        return jsonify({
            'valid': False,
            'errors': [f'Validation error: {str(e)}']
        }), 500

if __name__ == '__main__':
    # Verifica che l'interprete esista
    if not os.path.exists(INTERPRETER_PATH):
        print(f"WARNING: Interpreter not found at {INTERPRETER_PATH}")
        print("Make sure to place the 'noobie' executable in the same directory")
    
    # Ottieni la porta dall'ambiente (per Render)
    port = int(os.environ.get('PORT', 5000))
    
    # Avvia il server
    app.run(debug=False, host='0.0.0.0', port=port)
