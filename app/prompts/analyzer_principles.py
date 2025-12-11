# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Analyzer principles - correctness, security, and performance checks."""

CORRECTNESS_PRINCIPLES = """
CORRECTNESS (High Priority):

Check ONLY these bug classes:
1. Logic errors (off-by-one, wrong operators, missing edge cases)
2. Unhandled errors (exceptions, promise rejections, timeouts)
3. Resource leaks (connections, files, memory not freed)
4. Null/undefined access without checks
5. Race conditions (shared state without synchronization)

Skip: Style, naming, structure (unless impacts correctness)
"""

SECURITY_PRINCIPLES = """
SECURITY (Critical Priority):

Universal checks (any language):
1. Injection: SQL, command, path traversal
2. Secrets: Hardcoded passwords/keys/tokens in code
3. Crypto: Weak random (Math.random for secrets), insecure algorithms
4. Input: No validation on external inputs
5. Output: Sensitive data in errors/logs

Language-specific:
- Python: eval/exec on user input, shell=True with user data
- TypeScript: innerHTML with unescaped data, weak JWT validation
- Java: Runtime.exec with user input, SQL string concatenation
- Go: Unsafe SQL formatting, missing error checks

Flag ONLY if demonstrated vulnerability, not theoretical.
"""

PERFORMANCE_PRINCIPLES = """
PERFORMANCE (Only Obvious Issues):

Flag ONLY if visible impact:
- N+1 queries (proven by analyzing loop + query)
- Unbounded loops/recursion (no exit condition)
- Blocking operations in async code paths
- No connection pooling (new connection per request)

Skip: Micro-optimizations, hypothetical bottlenecks
"""
