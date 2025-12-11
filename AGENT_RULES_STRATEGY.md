# Agent Rules Strategy & Recommendations

## Executive Summary

After analyzing your TypeScript project rules against the current Python code review agent implementation, I recommend a **layered, role-specific rule injection strategy** that:

1. **Minimizes token usage** by injecting rules only where needed
2. **Reduces false positives** through bias mitigation and confidence thresholds
3. **Maximizes bug detection** with targeted security and correctness checks
4. **Adapts to language context** (Python vs TypeScript vs multi-language)

## Current State Analysis

### What You Have Now

**Python Code Review Agent (Current)**:
- ✅ Sequential pipeline: Analyzer → StyleChecker → TestAnalyzer → FeedbackSynthesizer
- ✅ Language-specific tools (Python + TypeScript)
- ✅ Structured output format
- ⚠️ Generic prompts without specific quality gates
- ⚠️ No bias mitigation or false positive prevention
- ⚠️ No security-first checklist
- ⚠️ No pattern compliance checking

**TypeScript Project Rules (Your Other Project)**:
- ✅ Comprehensive security checklist (OWASP ASVS L1)
- ✅ Strong bias mitigation rules (challenge existing code, prefer simplification)
- ✅ Pattern compliance verification (docs/patterns-catalog.md)
- ✅ Severity mapping with clear thresholds
- ✅ Confidence calculation and uncertainty handling
- ✅ Two-tier approach: commit-level (review.mdc) vs codebase-level (senior-engineer.mdc)

---

## Recommended Strategy: Role-Specific Rule Injection

### Architecture: 3-Tier Rule System

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: Core Rules (Always Applied to All Agents)          │
│ - Bias mitigation                                           │
│ - Output format standards                                   │
│ - Confidence thresholds                                     │
│ Tokens: ~200-300                                            │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
┌───────▼────────┐  ┌───────▼────────┐  ┌──────▼─────────┐
│ TIER 2a:       │  │ TIER 2b:       │  │ TIER 2c:       │
│ Analyzer Rules │  │ Style Rules    │  │ Test Rules     │
│ - Correctness  │  │ - Clean code   │  │ - Test quality │
│ - Security     │  │ - Patterns     │  │ - Coverage     │
│ Tokens: ~500   │  │ Tokens: ~300   │  │ Tokens: ~400   │
└────────────────┘  └────────────────┘  └────────────────┘
                            │
                    ┌───────▼────────┐
                    │ TIER 3:        │
                    │ Synthesizer    │
                    │ - Severity map │
                    │ - Prioritize   │
                    │ Tokens: ~400   │
                    └────────────────┘
```

**Total Token Budget per Pipeline**: ~1800 tokens
**Total for 2 Language Pipelines**: ~3600 tokens
**Root Orchestrator**: ~300 tokens
**Grand Total**: ~3900 tokens (vs ~8000+ if all rules everywhere)

---

## Recommended Rules by Agent

### TIER 1: Core Rules (All Agents)

**File**: `app/prompts/core_rules.py`

```python
BIAS_MITIGATION_RULES = """
ANTI-BIAS RULES (CRITICAL):

1. Challenge ALL code regardless of:
   - Age (legacy can be wrong)
   - Author (seniors make mistakes)
   - Popularity (common != correct)

2. Only flag REAL issues:
   - Can you demonstrate actual harm?
   - Is this correctness/security or style preference?
   - Would you flag this in perfect code from a senior?

3. "PASS" is valid and common (60-80% for good code):
   - High severity: 0 allowed
   - Medium severity: <3 acceptable
   - Low severity: Informational only

4. Prefer simplification:
   - >40% of suggestions should simplify/remove code
   - <20% should add new abstractions
   - New patterns need 2+ current use cases
"""

CONFIDENCE_RULES = """
CONFIDENCE ASSESSMENT:

confidence = 0.90

IF unclear_requirements: confidence -= 0.20
IF multiple_valid_approaches: confidence -= 0.15
IF language_specific_edge_case: confidence -= 0.10

IF confidence < 0.70: Add "Uncertainty" section explaining why
IF confidence < 0.50: Flag for human review, don't auto-suggest
"""

OUTPUT_FORMAT_RULES = """
OUTPUT FORMAT:

- Be specific: Reference file paths, line numbers, actual code
- Be actionable: "Change X to Y because Z" not "improve this"
- Be honest: Report actual issues, not rigged positives
- Be constructive: Explain why, not just what
"""
```

**Injection Point**: All 4 agents in each pipeline
**Token Cost**: ~300 tokens per agent

---

### TIER 2a: Code Analyzer Rules

**File**: `app/prompts/analyzer_rules.py`

```python
CORRECTNESS_RULES = """
CORRECTNESS CHECKS (Priority Order):

1. Logic Errors (High):
   - Off-by-one errors
   - Wrong comparison operators
   - Missing edge case handling
   - Incorrect algorithm implementation

2. Error Handling (High):
   - Unhandled exceptions/promises
   - Missing timeout on external calls
   - Resource leaks (connections, file handles)
   - Generic error messages (no context)

3. Data Integrity (High):
   - Missing input validation
   - Type mismatches
   - Null/undefined access
   - Race conditions
"""

SECURITY_RULES_PYTHON = """
SECURITY CHECKS (OWASP-Based, Python):

1. Injection Prevention (Critical):
   - SQL injection: Only parameterized queries
   - Command injection: Avoid os.system(), shell=True
   - Path traversal: Validate all file paths
   - Code injection: No eval(), exec() on user input

2. Secrets & Crypto (Critical):
   - No hardcoded secrets (check for 'password=', 'api_key=', tokens)
   - Use secrets.token_bytes() not random.random() for security
   - Timing-safe comparisons for secrets (secrets.compare_digest)
   - Min 32 bytes for security tokens

3. Input Validation (High):
   - Validate length, format, type
   - Reject invalid data early
   - Sanitize before logging (no PII leaks)
"""

SECURITY_RULES_TYPESCRIPT = """
SECURITY CHECKS (OWASP-Based, TypeScript):

1. Injection Prevention (Critical):
   - SQL injection: Only parameterized queries
   - XSS: Output encoding, CSP headers
   - Command injection: No shell execution with user input
   - Template injection: Safe template engines

2. Secrets & Crypto (Critical):
   - No hardcoded secrets
   - crypto.randomBytes() not Math.random() for security
   - Timing-safe comparisons (crypto.timingSafeEqual)
   - JWT validation (signature, expiration)

3. Input Validation (High):
   - Schema validation (Zod/Joi)
   - Length limits, format validation
   - Reject invalid early
"""

PERFORMANCE_RULES = """
PERFORMANCE (Only flag obvious issues):

- N+1 queries (DB/API calls in loops)
- Unbounded data structures (no max-size on caches)
- O(n²) in hot paths
- Blocking I/O in async paths
- No connection pooling
- No batch operations (single-record inserts in loops)
"""
```

**Injection Point**: `PythonCodeAnalyzer`, `TypeScriptCodeAnalyzer`
**Token Cost**: ~500 tokens

---

### TIER 2b: Style Checker Rules

**File**: `app/prompts/style_rules.py`

```python
CLEAN_CODE_RULES = """
CLEAN CODE PRINCIPLES:

1. Meaningful Names:
   - Variables/functions reveal purpose
   - No abbreviations unless universal
   - Avoid generic names (data, info, manager)

2. Single Responsibility:
   - Functions do ONE thing
   - Functions <50 lines (flag >80 lines)
   - Complexity <8 (flag >10)

3. DRY Principle:
   - Flag duplication >3 occurrences
   - Suggest extraction to shared function
   - Must show actual benefit

4. Constants Over Magic:
   - Replace hard-coded values with named constants
   - Exception: 0, 1, -1, true, false, null, "", []
"""

LANGUAGE_STYLE_PYTHON = """
PYTHON STYLE (PEP 8 via tool, only flag obvious):

- Long functions (>50 lines)
- Deep nesting (>3 levels)
- Complex conditionals (extract to functions)
- Missing type hints on public APIs
- Unused imports (let tool catch)
"""

LANGUAGE_STYLE_TYPESCRIPT = """
TYPESCRIPT STYLE (ESLint via tool, only flag obvious):

- Long functions (>50 lines)
- Deep nesting (>3 levels)
- any without justification
- console.log in server-side code
- Missing error handling in async functions
"""

NO_WHITESPACE_RULE = "DO NOT suggest whitespace, indentation, or formatting changes (tools handle this)"
```

**Injection Point**: `PythonStyleChecker`, `TypeScriptStyleChecker`
**Token Cost**: ~300 tokens

---

### TIER 2c: Test Analyzer Rules

**File**: `app/prompts/test_rules.py`

```python
TEST_QUALITY_RULES = """
TEST QUALITY ASSESSMENT:

1. Tests Real Behavior (Critical):
   ✅ DO: Test correct output for given inputs
   ✅ DO: Test error conditions handled correctly
   ❌ DON'T: Test implementation details
   ❌ DON'T: Write tests that always pass (rigged tests)

2. Meaningful Assertions:
   ✅ DO: assert result == expected_value
   ❌ DON'T: assert result is not None (too weak)
   ❌ DON'T: assert len(result) > 0 (vague)

3. Proper Mocking:
   ✅ DO: Mock external I/O only (API calls, DB, file system)
   ❌ DON'T: Mock business logic (defeats purpose)
   ❌ DON'T: Over-mock (testing nothing real)

4. Independence:
   - Tests run in any order
   - Tests clean up after themselves
   - No shared state between tests
"""

TEST_COVERAGE_RULES = """
TEST COVERAGE EXPECTATIONS:

- Critical paths: 90%+ (auth, payment, data access)
- Business logic: 80%+
- Utilities: 70%+
- Configuration: Not required

RED FLAGS:
- Tests that can't fail (always pass even if code broken)
- Trivial tests (testing getters with no logic)
- Duplicate tests (multiple tests verify same thing)
- Testing framework code (not your code)
"""

TEST_NAMING_PYTHON = """
PYTHON TEST NAMING:
- test_<function>_<condition>_<expected>
- Example: test_calculate_total_empty_list_returns_zero
"""

TEST_NAMING_TYPESCRIPT = """
TYPESCRIPT TEST NAMING:
- describe("<Component>", () => { it("should <behavior> when <condition>", ...) })
- Example: it("should return 0 when list is empty")
"""
```

**Injection Point**: `PythonTestAnalyzer`, `TypeScriptTestAnalyzer`
**Token Cost**: ~400 tokens

---

### TIER 3: Feedback Synthesizer Rules

**File**: `app/prompts/synthesizer_rules.py`

```python
SEVERITY_MAPPING = """
SEVERITY LEVELS:

HIGH (Blocking):
- Security bypass (auth bypass, injection, secrets exposure)
- Data loss or corruption
- Crash/outage scenario
- Resource exhaustion (no limits)
- Logic errors in critical paths

MEDIUM (Strongly Recommend):
- Security vulnerability (non-critical but exploitable)
- Performance degradation affecting UX
- Missing error handling
- Resource leaks
- Untested critical paths
- Inconsistent patterns

LOW (Optional):
- Maintainability concerns
- Missing docs (non-critical)
- Suboptimal patterns with no current impact
- Minor inconsistencies
- Style preferences
"""

PRIORITIZATION_RULES = """
PRIORITIZATION:

1. Group by severity (High → Medium → Low)
2. Within severity, group by category:
   - Security
   - Correctness
   - Performance
   - Maintainability
3. Limit findings:
   - High: All (no limit)
   - Medium: Top 5 most impactful
   - Low: Top 3 easiest wins (<5 min fixes)

AVOID:
- Listing every minor style issue
- Repeating same issue for multiple files
- Nitpicking without real benefit
"""

FEEDBACK_FORMAT = """
FEEDBACK STRUCTURE:

## Summary
[2-3 sentences: what changed, overall assessment, verdict]

## Verdict
- ✅ PASS: No blocking issues
- ⚠️ COMMENT: Non-blocking suggestions
- ❌ NEEDS_CHANGES: Blocking issues

## Findings by Severity

### High Severity Issues
[File:line] [Category] [One-line description]
Evidence: [code snippet]
Risk: [actual harm scenario]
Fix: [specific change with code example]

### Medium Severity Issues
[Same format, top 5]

### Low Severity Issues
[Same format, top 3 quick wins]

## Positive Observations
[2-3 specific strengths]

## Test Assessment
- Coverage: [%]
- Quality: [assessment]
- Missing: [critical gaps]
"""
```

**Injection Point**: `PythonFeedbackSynthesizer`, `TypeScriptFeedbackSynthesizer`
**Token Cost**: ~400 tokens

---

## Rules NOT to Include (False Positive Risks)

### From TypeScript Rules - SKIP These:

1. **Pattern Compliance Check** (docs/patterns-catalog.md)
   - ❌ **Why**: Your Python project doesn't have patterns-catalog.md
   - ❌ **Risk**: Agent will hallucinate patterns or complain about missing docs
   - ✅ **Alternative**: Add only IF you create patterns-catalog.md first

2. **README.md Maintenance**
   - ❌ **Why**: Too meta for code review agent (it's reviewing PR code, not docs)
   - ❌ **Risk**: Every PR will get "update README" suggestion
   - ✅ **Alternative**: Separate docs agent or manual process

3. **Process Improvement Loop** (updating agent rules after review)
   - ❌ **Why**: Self-modifying agents are risky, need human oversight
   - ❌ **Risk**: Agent rewrites own prompts incorrectly
   - ✅ **Alternative**: Manual quarterly review of agent effectiveness

4. **Distributed Communication (A2A Protocol)**
   - ❌ **Why**: Not used in your architecture (you use sequential pipelines)
   - ❌ **Risk**: Confusion about communication patterns
   - ✅ **Alternative**: Keep for reference docs only

5. **Speculative Abstractions (YAGNI)**
   - ⚠️ **Maybe**: This is valuable but needs tuning
   - ⚠️ **Risk**: Agent might flag legitimate future-proofing
   - ✅ **Alternative**: Include but with confidence penalty: "IF new_abstraction AND use_cases < 2: confidence -= 0.15"

---

## Implementation Plan

### Phase 1: Core Rules (Week 1)

**Goal**: Add bias mitigation and confidence thresholds to all agents

1. Create `app/prompts/core_rules.py`
2. Update `app/agents/pipeline_factory.py`:
   ```python
   from app.prompts.core_rules import BIAS_MITIGATION_RULES, CONFIDENCE_RULES

   def _get_analyzer_instruction(...):
       base_instruction = f"""..."""
       return base_instruction + "\n\n" + BIAS_MITIGATION_RULES + "\n\n" + CONFIDENCE_RULES
   ```
3. Test on existing PRs - measure:
   - % of reviews that pass (target: 60-80%)
   - False positive rate (flag issues that aren't real)
   - Token usage increase

**Success Criteria**:
- Pass rate between 60-80%
- No increase in false positives
- Token usage increase <20%

---

### Phase 2: Security & Correctness Rules (Week 2)

**Goal**: Add security and correctness checks to Analyzer agents

1. Create `app/prompts/analyzer_rules.py`
2. Add language-specific security rules to Analyzer instruction
3. Create test suite with known vulnerabilities (SQL injection, secrets, etc.)
4. Measure recall: % of known issues detected

**Success Criteria**:
- Detect 90%+ of known security issues
- <10% false positives on security findings
- Token usage per analyzer: ~800 tokens total

---

### Phase 3: Test Quality Rules (Week 3)

**Goal**: Improve test quality assessment

1. Create `app/prompts/test_rules.py`
2. Add to TestAnalyzer instruction
3. Test on PRs with known rigged tests
4. Measure: % of rigged tests detected

**Success Criteria**:
- Detect 80%+ of rigged tests
- Suggest meaningful test improvements
- Don't require 100% coverage

---

### Phase 4: Feedback Synthesis (Week 4)

**Goal**: Improve prioritization and severity mapping

1. Create `app/prompts/synthesizer_rules.py`
2. Add severity mapping and prioritization rules
3. Test on diverse PRs (trivial, medium, complex)
4. Measure: Are findings properly prioritized?

**Success Criteria**:
- High severity findings are truly high
- Low severity findings are quick wins (<5 min)
- Feedback is constructive, not just critical

---

## Tuning & Monitoring

### Metrics to Track

1. **Pass Rate** (most important)
   - Target: 60-80% of good PRs pass
   - <40%: Too harsh (false positives)
   - >90%: Too lenient (false negatives)

2. **False Positive Rate**
   - Target: <15%
   - Measure: Human reviewers disagree with agent finding
   - Fix: Tighten conditions, add confidence penalties

3. **False Negative Rate**
   - Target: <10% for High severity
   - Measure: Bugs reach production that agent missed
   - Fix: Add specific checks for missed bug class

4. **Token Usage**
   - Target: <5000 tokens per full review
   - Current estimate: ~3900 tokens
   - Buffer: 22% under target

5. **Review Time**
   - Target: <60 seconds per PR
   - Measure: End-to-end latency
   - Optimize: Parallel agent calls if needed

### Feedback Loop

**Monthly Review**:
1. Sample 20 agent reviews (10 passed, 10 failed)
2. Human expert reviews same PRs
3. Calculate agreement rate
4. Identify systematic issues
5. Update rules (not prompts directly - update rule constants)

**Quarterly Refactor**:
1. Analyze all reviews from quarter
2. Identify patterns in false positives/negatives
3. Major rule updates (with testing)
4. Token budget rebalancing

---

## Example: Updated Analyzer Prompt

**Before** (current):
```python
instruction = f"""You are a {language} code analysis specialist responsible for understanding code structure.

Your task:
1. Take the {language} code submitted by the user
2. Use the analyze_{language_lower}_structure tool to parse and analyze it
3. Identify all {structure_elements}
4. Note any syntax errors or structural issues
..."""
```

**After** (with rules):
```python
from app.prompts.core_rules import BIAS_MITIGATION_RULES, CONFIDENCE_RULES, OUTPUT_FORMAT_RULES
from app.prompts.analyzer_rules import CORRECTNESS_RULES, get_security_rules

instruction = f"""You are a {language} code analysis specialist responsible for understanding code structure.

YOUR TASK:
1. Use the analyze_{language_lower}_structure tool to parse and analyze code
2. Identify all {structure_elements}
3. Check for correctness and security issues
4. Provide specific, actionable feedback

{BIAS_MITIGATION_RULES}

{CORRECTNESS_RULES}

{get_security_rules(language_lower)}

{CONFIDENCE_RULES}

{OUTPUT_FORMAT_RULES}

PASS THE CODE EXACTLY as provided - do not modify, fix, or improve it.
The goal is to analyze what IS there, not what SHOULD be there.
"""
```

**Token Impact**:
- Before: ~200 tokens
- After: ~800 tokens
- Increase: 4x but within budget

---

## Decision Matrix: Which Rules Where?

| Rule Category | Orchestrator | Analyzer | StyleChecker | TestAnalyzer | Synthesizer | Tokens |
|--------------|-------------|----------|--------------|--------------|-------------|--------|
| Bias Mitigation | ✅ | ✅ | ✅ | ✅ | ✅ | 300 each |
| Confidence Assessment | ✅ | ✅ | ✅ | ✅ | ✅ | Included above |
| Output Format | ✅ | ✅ | ✅ | ✅ | ✅ | Included above |
| Security (OWASP) | ❌ | ✅ | ❌ | ❌ | ❌ | 200 |
| Correctness | ❌ | ✅ | ❌ | ❌ | ❌ | 150 |
| Performance | ❌ | ✅ | ❌ | ❌ | ❌ | 100 |
| Clean Code | ❌ | ❌ | ✅ | ❌ | ❌ | 200 |
| Test Quality | ❌ | ❌ | ❌ | ✅ | ❌ | 400 |
| Test Coverage | ❌ | ❌ | ❌ | ✅ | ❌ | Included above |
| Severity Mapping | ❌ | ❌ | ❌ | ❌ | ✅ | 250 |
| Prioritization | ❌ | ❌ | ❌ | ❌ | ✅ | 150 |
| Feedback Format | ❌ | ❌ | ❌ | ❌ | ✅ | Included above |
| **Total per Agent** | **300** | **~800** | **~500** | **~700** | **~700** | **~3000** |

**Per Language Pipeline**: ~3000 tokens
**Two Pipelines (Python + TypeScript)**: ~6000 tokens
**With Root Orchestrator**: ~6300 tokens

**Optimization**: Share rules across languages where possible (bias mitigation is identical)

---

## Recommended Rule Files Structure

```
app/prompts/
├── __init__.py
├── core_rules.py              # Bias mitigation, confidence, output format
├── analyzer_rules.py          # Security, correctness, performance
├── style_rules.py             # Clean code, language-specific style
├── test_rules.py              # Test quality, coverage, naming
├── synthesizer_rules.py       # Severity, prioritization, feedback
└── language_specific/
    ├── python_security.py     # Python-specific security checks
    └── typescript_security.py # TypeScript-specific security checks
```

---

## Key Takeaways

### DO Include:

1. ✅ **Bias Mitigation** - Everywhere (most important for quality)
2. ✅ **Security Checklist** - In Analyzer only (OWASP ASVS L1 essentials)
3. ✅ **Confidence Thresholds** - Everywhere (prevents overconfident mistakes)
4. ✅ **Severity Mapping** - In Synthesizer only (consistent prioritization)
5. ✅ **Test Quality Rules** - In TestAnalyzer only (detect rigged tests)
6. ✅ **Clean Code Basics** - In StyleChecker only (meaningful names, DRY, SRP)

### DON'T Include:

1. ❌ **Pattern Compliance** - Until you create patterns-catalog.md
2. ❌ **README Maintenance** - Too meta, high false positive rate
3. ❌ **Process Improvement Loop** - Risky self-modification
4. ❌ **Senior Engineer Full Rules** - Too verbose for commit-level review
5. ❌ **Whitespace/Formatting** - Tools handle this (Ruff, ESLint)

### Token Budget:

- **Target**: <5000 tokens total
- **Estimated**: ~6300 tokens (26% over - need optimization)
- **Optimization**: Share core rules, use references not duplication

### Success Metrics:

- **Pass Rate**: 60-80% (currently unknown, need to measure)
- **False Positives**: <15%
- **False Negatives (High Severity)**: <10%
- **Review Time**: <60 seconds

---

## Next Steps

1. **Implement Phase 1** (Core Rules) this week
2. **Measure baseline** on 20 recent PRs
3. **Tune thresholds** based on data
4. **Roll out Phase 2-4** incrementally with testing
5. **Monthly review** of metrics and adjustments

This strategy balances quality, speed, and token efficiency while learning from your TypeScript project's battle-tested rules.
