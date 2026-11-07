import difflib
import json
import logging
import os
import subprocess
import sys
import tempfile
from typing import Dict, Any, List, Optional

from app.config import CODE_MODEL
from app.services.chat_service import generate_chat_response

logger = logging.getLogger("nova_ai.code_service")

CODE_SYSTEM_PROMPT = """You are NOVA AI Code Assistant, an elite senior principal software engineer, security auditor, and systems architect.
You specialize in: Python, JavaScript, TypeScript, React, Next.js, Node.js, Go, Rust, Java, C++, C#, SQL, Docker, Kubernetes, and Cloud Architecture.
When generating or reviewing code:
1. Always write complete, production-ready, clean, idiomatic code with robust error handling.
2. Emphasize security (prevent SQL injections, XSS, SSRF, memory leaks, OWASP Top 10).
3. Provide precise, step-by-step technical explanations and installation/run commands.
4. When debugging, pinpoint the exact line, explain why it failed, and provide the exact corrected code.
5. In Project Builder mode, provide the complete directory tree structure and every single file needed.
"""


def generate_code_solution(prompt: str, language: str = "python", framework: Optional[str] = None) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": CODE_SYSTEM_PROMPT},
        {"role": "user", "content": f"Generate a complete, production-grade {language} program ({framework or 'standard'}). Description:\n{prompt}\nInclude clear comments, tests, and run commands."},
    ]
    response = generate_chat_response(messages, model=CODE_MODEL)
    return {
        "language": language,
        "framework": framework,
        "solution": response,
    }


def debug_code(code: str, error_message: str, language: str = "python") -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": CODE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Debug this {language} code.
Original Code:
```{language}
{code}
```

Error Message / Symptoms:
```
{error_message}
```

Instructions:
1. Identify the exact root cause.
2. Explain why the bug occurred.
3. Provide the full corrected code.
4. Provide unit tests to ensure it does not regress.
""",
        },
    ]
    response = generate_chat_response(messages, model=CODE_MODEL)
    return {
        "language": language,
        "original_code": code,
        "error_message": error_message,
        "analysis_and_fix": response,
    }


def review_code(code: str, language: str = "python") -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": CODE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Perform a comprehensive code review of this {language} code.
```{language}
{code}
```

Analyze:
1. Security vulnerabilities (OWASP, input sanitization, memory safety)
2. Performance & Big-O complexity bottlenecks
3. Code smell, maintainability, architectural flaws
4. Missing error handling and edge cases
5. Recommended refactored code.
""",
        },
    ]
    response = generate_chat_response(messages, model=CODE_MODEL)
    return {
        "language": language,
        "review": response,
    }


def build_full_project(description: str, tech_stack: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": CODE_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": f"""Generate a full multi-file software project architecture for:
Project Goal: {description}
Target Tech Stack: {tech_stack}

Requirements:
1. Complete folder and file structure.
2. Frontend code files.
3. Backend API files.
4. Database schema / migration files.
5. Configuration files (.env.example, Dockerfile, requirements.txt or package.json).
6. Setup and deployment terminal commands.
""",
        },
    ]
    response = generate_chat_response(messages, model=CODE_MODEL)
    return {
        "tech_stack": tech_stack,
        "description": description,
        "blueprint": response,
    }


def execute_sandboxed_code(code: str, language: str = "python", timeout_seconds: int = 4) -> Dict[str, Any]:
    """
    Safely executes code in an isolated subprocess sandbox.
    Enforces strict timeouts, output truncation, and catches runtime errors.
    Only supports safe scripting languages (Python, JS).
    """
    if language.lower() not in ("python", "py", "javascript", "js"):
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution of language '{language}' is disabled for safety. Supported: Python, JavaScript.",
            "execution_time_ms": 0,
        }

    # Python security blacklist heuristics for main process protection
    dangerous_keywords = ["os.system", "shutil.rmtree", "subprocess.Popen", "rm -rf", "ctypes"]
    for kw in dangerous_keywords:
        if kw in code:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Security restriction: Use of '{kw}' is blocked in sandbox.",
                "execution_time_ms": 0,
            }

    import time
    start_time = time.time()
    temp_dir = tempfile.mkdtemp()
    
    try:
        if language.lower() in ("python", "py"):
            file_path = os.path.join(temp_dir, "script.py")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            # Use current virtual environment python
            py_exe = sys.executable
            proc = subprocess.run(
                [py_exe, "-I", file_path],  # -I: isolated mode (no user site-packages, no PYTHONPATH)
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=temp_dir,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout[:10000],
                "stderr": proc.stderr[:10000],
                "returncode": proc.returncode,
                "execution_time_ms": elapsed_ms,
            }

        elif language.lower() in ("javascript", "js"):
            file_path = os.path.join(temp_dir, "script.js")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)

            proc = subprocess.run(
                ["node", "--no-warnings", file_path],
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=temp_dir,
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "success": proc.returncode == 0,
                "stdout": proc.stdout[:10000],
                "stderr": proc.stderr[:10000],
                "returncode": proc.returncode,
                "execution_time_ms": elapsed_ms,
            }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution timed out (limit: {timeout_seconds} seconds).",
            "execution_time_ms": timeout_seconds * 1000,
        }
    except Exception as exc:
        return {
            "success": False,
            "stdout": "",
            "stderr": f"Execution environment error: {str(exc)}",
            "execution_time_ms": 0,
        }
    finally:
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

