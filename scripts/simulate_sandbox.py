#!/usr/bin/env python3
"""
Sandbox Simulation for Gemma 4 SWE Agent
Simulates the 12h competition sandbox locally for testing.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Any

class SandboxSimulator:
    """Simulates the competition sandbox environment."""
    
    def __init__(self, budget_seconds: int = 43200):  # 12 hours
        self.budget_seconds = budget_seconds
        self.elapsed = 0
        self.results = []
    
    def run_command(self, cmd: str, cwd: str = None) -> Dict:
        """Simulate run_command tool."""
        start = time.time()
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, 
                timeout=300, cwd=cwd
            )
            elapsed = time.time() - start
            self.elapsed += elapsed
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed": elapsed,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            self.elapsed += elapsed
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out after 300s",
                "elapsed": elapsed,
                "returncode": -1
            }
    
    def read_file(self, filepath: str, start_line: int = None, end_line: int = None) -> Dict:
        """Simulate read_file tool."""
        try:
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            if start_line or end_line:
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                content = ''.join(lines[start:end])
            else:
                content = ''.join(lines)
            
            return {"success": True, "content": content}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def edit_file(self, filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> Dict:
        """Simulate edit_file tool."""
        try:
            with open(filepath, 'r') as f:
                content = f.read()
            
            if old_string not in content:
                return {"success": False, "error": "old_string not found"}
            
            if not allow_multiple and content.count(old_string) > 1:
                return {"success": False, "error": "Multiple matches found, use allow_multiple=True"}
            
            new_content = content.replace(old_string, new_string)
            
            with open(filepath, 'w') as f:
                f.write(new_content)
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def write_file(self, filepath: str, content: str) -> Dict:
        """Simulate write_file tool."""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def search_similar_code(self, query: str, k: int = 10) -> Dict:
        """Simulate search_similar_code tool (mock - would use embeddings in real)."""
        # This is a mock - in reality would use pre-computed embeddings
        return {
            "success": True,
            "results": [
                {"file": "example.py", "symbol": "function_name", "score": 0.9},
            ]
        }
    
    def get_code_neighbors(self, node: str, edge_type: str = None, max_neighbors: int = 50) -> Dict:
        """Simulate get_code_neighbors tool (mock)."""
        return {
            "success": True,
            "neighbors": [
                {"node": "related_function", "edge_type": "calls"},
            ]
        }
    
    def get_code_subgraph(self, nodes: List[str]) -> Dict:
        """Simulate get_code_subgraph tool (mock)."""
        return {
            "success": True,
            "subgraph": {"nodes": nodes, "edges": []}
        }
    
    def submit_patch(self, repo_path: str) -> Dict:
        """Simulate submit_patch tool - generates git diff."""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=repo_path, capture_output=True, text=True
            )
            return {
                "success": True,
                "patch": result.stdout
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

def run_simulation(issues: List[Dict], simulator: SandboxSimulator, agent) -> List[Dict]:
    """Run simulation on multiple issues."""
    results = []
    
    for i, issue in enumerate(issues):
        if simulator.elapsed >= simulator.budget_seconds:
            print(f"Budget exhausted at issue {i+1}")
            break
        
        print(f"\n=== Issue {i+1}/{len(issues)} ===")
        print(f"Budget remaining: {simulator.budget_seconds - simulator.elapsed:.0f}s")
        
        # This is where the agent would process the issue
        # For simulation, we just track budget
        issue_result = {
            "issue_id": issue.get("id", f"issue_{i}"),
            "repo": issue.get("repo", "unknown"),
            "elapsed": 0,
            "status": "simulated"
        }
        
        results.append(issue_result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description="Simulate competition sandbox")
    parser.add_argument("--issues", type=int, default=10, help="Number of issues to simulate")
    parser.add_argument("--budget", type=int, default=43200, help="Budget in seconds (default 12h)")
    parser.add_argument("--data", default="data/processed/test_issues.json", help="Test issues data")
    parser.add_argument("--output", default="simulation_results.json", help="Output file")
    args = parser.parse_args()
    
    # Load test issues
    try:
        with open(args.data) as f:
            issues = json.load(f)
        issues = issues[:args.issues]
    except FileNotFoundError:
        print(f"Data file not found: {args.data}")
        # Create mock issues for testing
        issues = [
            {"id": f"test_{i}", "repo": "django/django", "issue_text": f"Test issue {i}"}
            for i in range(args.issues)
        ]
    
    simulator = SandboxSimulator(args.budget)
    
    print(f"Starting sandbox simulation...")
    print(f"Issues: {len(issues)}")
    print(f"Budget: {args.budget/3600:.1f} hours")
    
    start_time = time.time()
    results = run_simulation(issues, simulator, None)
    total_time = time.time() - start_time
    
    # Save results
    output = {
        "total_issues": len(issues),
        "simulated_issues": len(results),
        "total_time_seconds": total_time,
        "budget_used_seconds": simulator.elapsed,
        "budget_remaining_seconds": simulator.budget_seconds - simulator.elapsed,
        "results": results
    }
    
    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSimulation complete!")
    print(f"Time: {total_time:.1f}s")
    print(f"Budget used: {simulator.elapsed:.1f}s / {simulator.budget_seconds}s")
    print(f"Results saved to: {args.output}")

if __name__ == "__main__":
    main()
