#!/usr/bin/env python3
"""
ba-mcp — Model Context Protocol (MCP) Server for BetterAI (ba)
Provides deterministic verification tools for ANY AI agent (Claude, Gemini, Cursor, Roo, Cline, OpenAI).
Zero dependencies: runs on Python 3 standard library.
"""

import sys
import json
import subprocess
import os
from pathlib import Path

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ba-mcp"
SERVER_VERSION = "0.8.0"

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT_DIR / "scripts"

TOOLS = [
    {
        "name": "ba_gate",
        "description": "Run build + lint + test on the repository. Prints compact failure logs (last 40 lines). Exit 0 = green.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dir": {"type": "string", "description": "Target repository directory (default: current directory)"},
                "only": {"type": "string", "enum": ["build", "lint", "test"], "description": "Optional step filter"}
            }
        }
    },
    {
        "name": "ba_detect",
        "description": "Detect build, test, and lint commands for the project.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "dir": {"type": "string", "description": "Target repository directory (default: current directory)"}
            }
        }
    },
    {
        "name": "ba_prove_test",
        "description": "Proves that new tests are real (RED->GREEN proof). Reverts implementation files to confirm test fails, then reapplies to confirm test passes.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "test_cmd": {"type": "string", "description": "Command to run the tests"},
                "test_files": {"type": "array", "items": {"type": "string"}, "description": "List of test file paths"}
            },
            "required": ["test_cmd", "test_files"]
        }
    },
    {
        "name": "ba_prove_refactor",
        "description": "Proves that refactoring, perf, or test-splitting preserved all test assertions without regressions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "base_ref": {"type": "string", "description": "Git base reference, e.g. origin/main or HEAD~1"},
                "kind": {"type": "string", "enum": ["refactor", "perf", "test-split"], "description": "Kind of change"},
                "slow": {"type": "number", "description": "Threshold for slow tests in seconds (default: 60)"},
                "bench": {"type": "string", "description": "Benchmark command printing 'BENCH <number>' (for perf)"},
                "target": {"type": "number", "description": "Target percentage improvement (for perf)"}
            },
            "required": ["base_ref", "kind"]
        }
    },
    {
        "name": "ba_sec_scan",
        "description": "Run deterministic security scan: secrets (history + tree), code vulnerabilities, or vulnerable dependencies.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["secrets", "code", "deps"], "description": "Scan category"},
                "tree_only": {"type": "boolean", "description": "For secrets: scan working tree only (skip full history)"},
                "advisory_id": {"type": "string", "description": "For deps: verify that this GHSA/CVE advisory is resolved"}
            },
            "required": ["mode"]
        }
    },
    {
        "name": "ba_test_times",
        "description": "Analyze test suite execution durations and identify slow bottleneck tests.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "slow": {"type": "number", "description": "Threshold in seconds for slow tests (default: 60)"},
                "run_suite": {"type": "boolean", "description": "Execute a measured test run if reports are missing"},
                "dir": {"type": "string", "description": "Directory containing test reports"}
            }
        }
    }
]

def find_bash():
    """Finds a working bash executable, prioritizing Git Bash on Windows."""
    if sys.platform == "win32":
        candidates = [
            r"C:\Program Files\Git\bin\bash.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\bash.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c
    return "bash"

BASH_CMD = find_bash()

def run_bash_script(script_name, args, cwd=None):
    script_path = str(SCRIPTS_DIR / script_name)
    cmd = [BASH_CMD, script_path] + [str(a) for a in args]
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd or os.getcwd(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False
        )
        return proc.returncode, proc.stdout.strip()
    except Exception as e:
        return 1, f"Execution failed: {str(e)}"

def handle_call_tool(tool_name, arguments):
    cwd = arguments.get("dir") or os.getcwd()
    
    if tool_name == "ba_gate":
        args = [cwd]
        if arguments.get("only"):
            args.extend(["--only", arguments["only"]])
        rc, out = run_bash_script("gate.sh", args, cwd=cwd)
        return rc, out

    elif tool_name == "ba_detect":
        rc, out = run_bash_script("detect.sh", [cwd], cwd=cwd)
        return rc, out

    elif tool_name == "ba_prove_test":
        test_cmd = arguments.get("test_cmd", "")
        test_files = arguments.get("test_files", [])
        rc, out = run_bash_script("prove-test.sh", [test_cmd] + test_files, cwd=cwd)
        return rc, out

    elif tool_name == "ba_prove_refactor":
        base_ref = arguments.get("base_ref", "origin/main")
        kind = arguments.get("kind", "refactor")
        args = [base_ref, kind]
        if "slow" in arguments:
            args.extend(["--slow", str(arguments["slow"])])
        if "bench" in arguments:
            args.extend(["--bench", arguments["bench"]])
        if "target" in arguments:
            args.extend(["--target", str(arguments["target"])])
        rc, out = run_bash_script("prove-refactor.sh", args, cwd=cwd)
        return rc, out

    elif tool_name == "ba_sec_scan":
        mode = arguments.get("mode", "secrets")
        args = [mode]
        if arguments.get("tree_only"):
            args.append("--tree")
        if arguments.get("advisory_id"):
            args.extend(["--id", arguments["advisory_id"]])
        rc, out = run_bash_script("sec-scan.sh", args, cwd=cwd)
        return rc, out

    elif tool_name == "ba_test_times":
        args = []
        if arguments.get("run_suite"):
            args.append("--run")
        if "slow" in arguments:
            args.extend(["--slow", str(arguments["slow"])])
        if arguments.get("dir"):
            args.extend(["--dir", arguments["dir"]])
        rc, out = run_bash_script("test-times.sh", args, cwd=cwd)
        return rc, out

    else:
        return 1, f"Unknown tool: {tool_name}"

def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        if method == "initialize":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {
                        "name": SERVER_NAME,
                        "version": SERVER_VERSION
                    }
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            pass

        elif method == "tools/list":
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "tools": TOOLS
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            rc, out = handle_call_tool(tool_name, arguments)
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": out or ("OK" if rc == 0 else f"Failed with exit code {rc}")
                        }
                    ],
                    "isError": (rc != 0)
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

        elif req_id is not None:
            # Unknown method response
            resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    main()
