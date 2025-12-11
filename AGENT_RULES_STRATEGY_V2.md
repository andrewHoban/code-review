# Agent Rules Strategy V2: Organization-Level Principles

## Philosophy Shift

**V1 Approach** (Project-specific): "Check docs/patterns-catalog.md for standard patterns"
**V2 Approach** (Organization-level): "Flag inconsistent patterns within this codebase"

**Key Insight**: Rules should be **context-free principles** that work across:
- Different tech stacks (Python, TypeScript, Java, Go)
- Different team processes (Scrum, Kanban, ad-hoc)
- Different maturity levels (startup MVP vs enterprise system)

---

## Refined Token Budget

### Before (Project-Specific)
- Core rules: 300 tokens
- Analyzer rules: 500 tokens
- Style rules: 300 tokens
- Test rules: 400 tokens
- Synthesizer rules: 400 tokens
**Total per pipeline**: ~1900 tokens
**Total for 2 languages**: ~3800 tokens

### After (Organization-Level Principles)
- Core principles: 150 tokens (50% reduction)
- Analyzer principles: 250 tokens (50% reduction)
- Design principles: 250 tokens (17% reduction - includes SOLID/DRY/YAGNI/DDD)
- Test principles: 200 tokens (50% reduction)
- Synthesizer principles: 200 tokens (50% reduction)
**Total per pipeline**: ~1050 tokens
**Total for 2 languages**: ~2100 tokens
**Savings**: 45% reduction

---

## Organization-Level Rules (Refined)

### TIER 1: Core Principles (ALL Agents)

**File**: `app/prompts/core_principles.py` - **150 tokens**

```python
CORE_PRINCIPLES = """
REVIEW PRINCIPLES:

1. Real Issues Only:
   - Flag only if: correctness bug, security risk, or performance problem
   - NOT style preferences, personal taste, or "could be better"
   - Ask: "What actual harm does this cause?"

2. Expected Pass Rate: 60-80%
   - Most code is acceptable with minor improvements
   - High severity issues are rare (0-2 per review)
   - Pass more often than fail

3. Be Specific:
   - Reference exact file:line
   - Show code snippet
   - Explain concrete harm, not vague concerns

4. When Uncertain (confidence <70%):
   - Say so explicitly
   - Explain what's unclear
   - Suggest alternatives, don't demand changes
"""
```

**Rationale**: Universal principles that work for any team/stack. No project-specific references.

---

### TIER 2a: Analyzer Principles

**File**: `app/prompts/analyzer_principles.py` - **250 tokens**

```python
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
```

**Rationale**:
- No references to specific tools (pyflakes, ESLint)
- No references to specific patterns (patterns-catalog.md)
- Works for any language with minimal adaptation
- Focuses on universal bug classes

---

### TIER 2b: Design Principles (SOLID, DRY, YAGNI)

**File**: `app/prompts/design_principles.py` - **200 tokens**

```python
DESIGN_PRINCIPLES = """
DESIGN QUALITY (Medium Priority):

1. Single Responsibility Principle:
   - Flag if: Function/class does multiple unrelated things
   - Evidence: "This function both validates input AND saves to database AND sends email"
   - Fix: Split into separate functions with clear names
   - Skip: Subjective "could be cleaner" without clear harm

2. DRY (Don't Repeat Yourself):
   - Flag if: Identical logic duplicated 3+ times
   - Evidence: Show the duplicated code blocks
   - Fix: Extract to shared function/constant
   - Skip: Similar-looking code that has different purposes
   - Skip: Duplication <3 times (might not be pattern yet)

3. YAGNI (You Aren't Gonna Need It):
   - Flag if: Unused code, parameters, or abstractions
   - Evidence: "This parameter is never used", "This class has no callers"
   - Flag if: Overly generic code without current use cases
   - Evidence: "This supports 5 formats but only 1 is used"
   - Skip: Reasonable extension points with 2+ current uses

4. Readability:
   - Functions >80 lines (hard to understand)
   - Nesting >4 levels (cognitive overload)
   - Meaningless names (x, data, info, temp, manager)
   - Magic numbers (except 0, 1, -1, true, false, empty string)

Skip Always:
- Formatting/whitespace (tools handle this)
- Personal preferences (tabs vs spaces, braces style)
- Abstract "could be better" without demonstrable harm
"""
```

**Rationale**:
- SOLID, DRY, YAGNI are universal engineering principles
- Made concrete with evidence requirements (not vague suggestions)
- Balanced: Flag real violations, skip subjective improvements
- Harm-based: Require demonstration of actual problem

---

### TIER 2c: Test Principles

**File**: `app/prompts/test_principles.py` - **200 tokens**

```python
TEST_PRINCIPLES = """
TEST QUALITY:

Red Flags (High Priority):
1. Rigged tests: Assertions so weak they always pass
   Bad: assert result is not None
   Good: assert result == expected_value

2. No assertions: Test runs code but doesn't verify behavior
   Bad: process_data(input)  # No assert
   Good: assert process_data(input).status == "success"

3. Over-mocked: Mocking business logic (not just external I/O)
   Bad: Mock every function call
   Good: Mock only API/DB/filesystem

4. Testing framework code instead of your code

Coverage Expectations:
- Critical paths (auth, payment, data loss scenarios): Must be tested
- Business logic: Should be tested
- Utilities/config: Optional

Don't Require:
- 100% coverage (80% is often sufficient)
- Tests for trivial getters/setters
- Tests for every edge case (focus on likely scenarios)

Measure: Would this test fail if the code was broken?
"""
```

**Rationale**:
- Removed framework-specific patterns (pytest vs Jest)
- Removed AAA pattern (useful but not universal)
- Removed naming conventions (team-specific)
- Kept only universal test quality principles

---

### TIER 3: Synthesis Principles

**File**: `app/prompts/synthesis_principles.py` - **200 tokens**

```python
SEVERITY_PRINCIPLES = """
SEVERITY LEVELS:

HIGH (Must Fix):
- Security vulnerability with demonstrated exploit
- Data loss/corruption scenario
- Crash/outage path
- Correctness bug in critical path (auth, payment, data integrity)

MEDIUM (Should Fix):
- Security issue without clear exploit path
- Performance degradation (measurable)
- Missing error handling (non-critical paths)
- Resource leak (minor)
- Inconsistent error handling

LOW (Optional):
- Readability issues (long functions, complex code)
- Missing tests (non-critical paths)
- Minor inconsistencies
- Maintainability concerns

Rule: High findings are rare (0-2 per review). Most reviews have 0-3 Medium, 2-5 Low.
"""

PRIORITIZATION_PRINCIPLES = """
PRIORITIZATION:

1. Security first (any severity)
2. Correctness in critical paths (High)
3. Everything else by severity

Limit output:
- High: Show all (expect 0-2)
- Medium: Top 5 by impact
- Low: Top 3 quick wins (<5 min to fix)

Skip:
- Listing same issue across many files (show one example + count)
- Nitpicking every minor style issue
- Suggesting rewrites without clear benefit
"""
```

**Rationale**:
- Removed project-specific categories
- Removed references to specific workflows
- Universal severity definitions that work for any context

---

## What We Removed (and Why)

### ❌ Removed: Process-Specific Rules

**Before**:
```
1. Check docs/patterns-catalog.md for standard patterns
2. Update README.md if API changes
3. Follow test naming: test_<function>_<condition>_<expected>
4. Add JSDoc for exported functions
5. Use Zod for validation (not manual checks)
```

**Why Remove**:
- References project-specific files (patterns-catalog.md, README.md)
- Prescribes specific tools (Zod, JSDoc)
- Assumes specific conventions (test naming)
- Doesn't work across different teams/stacks

**Replacement** (Organization Principle):
```
1. Flag inconsistent patterns within this codebase
2. Ensure public APIs are documented (any format)
3. Verify tests have meaningful assertions
```

---

### ❌ Removed: Tool-Specific Rules

**Before**:
```
Python: Follow PEP 8, use Ruff/Black
TypeScript: Follow ESLint config, use Prettier
Use parameterized queries (SQLAlchemy, Prisma, etc.)
```

**Why Remove**:
- Assumes specific tools installed
- Doesn't transfer to other languages (Java, Go, Rust)
- Teams may use different tools

**Replacement** (Universal Principle):
```
Python/TypeScript/Java/Go: Use language formatter (any)
All languages: Use parameterized queries (prevent SQL injection)
```

---

### ✅ Refined: Design Principles (Not Style Dogma)

**Before** (Too Vague):
```
- DRY: Extract repeated code
- Single Responsibility: Functions do ONE thing
- Constants over magic numbers: Replace all hard-coded values
- Encapsulation: Hide implementation details
```

**Problem**: Too abstract, leads to subjective/vague suggestions

**After** (Evidence-Based):
```
- DRY: Flag if duplicated 3+ times, show the duplications
- SRP: Flag if function does multiple unrelated things, be specific
- YAGNI: Flag unused code/parameters, show they're unused
- Magic numbers: Flag if meaning unclear (not 0, 1, true, false)
```

**Key Change**: Keep the principles but require concrete evidence
- Don't say "violates SRP" - say "function does X, Y, and Z"
- Don't say "not DRY" - show the 3+ duplicated blocks
- Don't say "you might need it" - show it's currently unused

---

### ❌ Removed: Coverage Dogma

**Before**:
```
- Target: 80% overall, 90% for critical paths
- Use test pyramid: 70% unit, 25% integration, 5% E2E
- Tests must follow AAA pattern
- Use exact assertions (no toBeTruthy, toBeDefined)
```

**Why Remove**:
- Arbitrary percentages (context-dependent)
- Test pyramid is one approach, not universal law
- AAA is helpful but not mandatory
- Some assertions are appropriate (exists checks for optional fields)

**Replacement** (Quality Focus):
```
- Critical paths must be tested (auth, payment, data loss)
- Tests must have meaningful assertions (detect when code breaks)
- Avoid rigged tests (always pass even if code broken)
```

---

### ❌ Removed: Architecture Prescriptions

**Before**:
```
- Use dependency injection (not singletons)
- Follow clean architecture (business logic → infrastructure)
- Separate concerns (controllers, services, repositories)
- Use Result types (not exceptions) for error handling
```

**Why Remove**:
- Architectural choices are team/project decisions
- Different paradigms work (DI vs singletons, exceptions vs Results)
- Prescriptive for established codebases

**Replacement** (Consistency Focus):
```
- Flag inconsistent error handling within this codebase
- Flag inconsistent architecture patterns within this codebase
- Don't prescribe architecture, enforce existing patterns
```

---

## Updated Agent Prompts (Examples)

### Before: Analyzer (500 tokens)

```python
instruction = f"""You are a {language} code analysis specialist.

SECURITY CHECKS (OWASP ASVS L1):
- SQL injection: Use parameterized queries (SQLAlchemy, Prisma)
- Command injection: Avoid os.system(), subprocess with shell=True
- Path traversal: Validate paths against whitelist
- XSS: Use output encoding, CSP headers
- Secrets: Check for 'password=', 'api_key=' patterns
- Crypto: Use secrets.token_bytes() not random.random()
- Timing attacks: Use secrets.compare_digest() for comparisons

CORRECTNESS CHECKS:
- Off-by-one errors
- Wrong comparison operators
- Missing edge cases
- Unhandled exceptions
- Resource leaks (connections, files)
- Null access without checks
- Race conditions

PERFORMANCE CHECKS:
- N+1 queries
- Unbounded loops
- Blocking I/O in async
- No connection pooling
- O(n²) algorithms

[...more rules...]
"""
```

### After: Analyzer (250 tokens)

```python
from app.prompts.core_principles import CORE_PRINCIPLES
from app.prompts.analyzer_principles import (
    CORRECTNESS_PRINCIPLES,
    SECURITY_PRINCIPLES,
    PERFORMANCE_PRINCIPLES
)

instruction = f"""You are a {language} code analysis specialist.

{CORE_PRINCIPLES}

{CORRECTNESS_PRINCIPLES}

{SECURITY_PRINCIPLES}

{PERFORMANCE_PRINCIPLES}

LANGUAGE CONTEXT: {language}
Adapt checks to {language} idioms while following universal principles.
"""
```

**Token Savings**: 250 tokens (50% reduction)

---

### Before: Test Analyzer (400 tokens)

```python
instruction = f"""You are a testing specialist for {language}.

TEST QUALITY RULES:
1. Tests Real Behavior:
   ✅ DO: Test correct output for inputs
   ✅ DO: Test error conditions
   ✅ DO: Use exact assertions (assert result == 6, not assert result > 0)
   ❌ DON'T: Test implementation details
   ❌ DON'T: Test framework code

2. Proper Mocking:
   ✅ DO: Mock external I/O only (API, DB, filesystem)
   ❌ DON'T: Mock business logic
   Example: Mock requests.get, don't mock calculate_total

3. Independence:
   - Tests run in any order
   - Tests clean up after themselves
   - No shared state

4. Naming Conventions:
   Python: test_<function>_<condition>_<expected>
   TypeScript: describe/it with "should <behavior> when <condition>"

COVERAGE EXPECTATIONS:
- Critical paths: 90%+
- Business logic: 80%+
- Utilities: 70%+
- Config: Optional

TEST FRAMEWORKS:
Python: pytest, unittest
TypeScript: Jest, Vitest, Mocha

[...more rules...]
"""
```

### After: Test Analyzer (200 tokens)

```python
from app.prompts.core_principles import CORE_PRINCIPLES
from app.prompts.test_principles import TEST_PRINCIPLES

instruction = f"""You are a testing specialist for {language}.

{CORE_PRINCIPLES}

{TEST_PRINCIPLES}

Focus on test quality over coverage percentages.
Ask: Would this test fail if the code was broken?
"""
```

**Token Savings**: 200 tokens (50% reduction)

---

## Comparison Table: Project vs Organization Rules

| Aspect | Project-Specific Rules | Organization-Level Principles | Token Savings |
|--------|----------------------|------------------------------|---------------|
| **Style** | "Follow PEP 8", "Use Black" | "Functions <80 lines, meaningful names" | 67% |
| **Security** | "Use SQLAlchemy parameterized queries" | "Use parameterized queries (any library)" | 40% |
| **Testing** | "Use pytest, follow AAA pattern" | "Tests must have meaningful assertions" | 50% |
| **Patterns** | "Check docs/patterns-catalog.md" | "Flag inconsistent patterns in this codebase" | 80% |
| **Coverage** | "80% overall, 90% critical" | "Critical paths must be tested" | 60% |
| **Architecture** | "Use DI, clean architecture" | "Flag inconsistent error handling" | 70% |
| **Documentation** | "Add JSDoc for exports" | "Document public APIs (any format)" | 50% |
| **Overall** | ~1900 tokens per pipeline | ~900 tokens per pipeline | **53%** |

---

## Key Principles for Organization-Level Rules

### 1. **Language-Agnostic Core**

❌ **Bad** (Language-specific):
```
Python: Use type hints
TypeScript: Avoid 'any'
Java: Use generics
```

✅ **Good** (Universal):
```
Use type system to prevent errors (if language has types)
```

### 2. **Tool-Agnostic**

❌ **Bad** (Tool-specific):
```
Use ESLint for linting
Use Ruff for formatting
Use pytest for testing
```

✅ **Good** (Universal):
```
Use automated linter (any)
Use automated formatter (any)
Use test framework (any)
```

### 3. **Process-Agnostic**

❌ **Bad** (Process-specific):
```
Follow Scrum conventions
Update Jira ticket
Tag with version number
```

✅ **Good** (Universal):
```
Explain what changed and why (any format)
Reference related work (any system)
```

### 4. **Maturity-Agnostic**

❌ **Bad** (Assumes maturity):
```
Add performance monitoring
Implement circuit breakers
Use distributed tracing
Set up A/B testing
```

✅ **Good** (Scales with maturity):
```
Handle errors gracefully
Add timeouts to external calls
Log enough context to debug issues
```

### 5. **Harm-Focused**

❌ **Bad** (Style preference):
```
Extract this to a separate function
Use const instead of let
Rename variable to be more descriptive
```

✅ **Good** (Actual harm):
```
This causes SQL injection vulnerability
This leaks database connections
This crashes when input is null
```

---

## Implementation Strategy

### Phase 1: Extract Organization Principles (Week 1)

1. Create `app/prompts/` directory structure:
   ```
   app/prompts/
   ├── __init__.py
   ├── core_principles.py          # 150 tokens
   ├── analyzer_principles.py      # 250 tokens
   ├── design_principles.py        # 250 tokens (SOLID, DRY, YAGNI, DDD Strategic)
   ├── test_principles.py          # 200 tokens
   └── synthesis_principles.py     # 200 tokens
   ```

2. Write principles (not processes):
   - Focus on "what" not "how"
   - Universal patterns, not specific tools
   - Harm-based, not style-based

3. **Success Criteria**:
   - Each principle file <250 tokens
   - No references to specific tools/files
   - Works across Python, TypeScript, Java, Go

---

### Phase 2: Update Agent Instructions (Week 1)

1. Modify `app/agents/pipeline_factory.py`:
   ```python
   from app.prompts.core_principles import CORE_PRINCIPLES
   from app.prompts.analyzer_principles import (
       CORRECTNESS_PRINCIPLES,
       SECURITY_PRINCIPLES,
       PERFORMANCE_PRINCIPLES
   )

   def _get_analyzer_instruction(language: str) -> str:
       return f"""You are a {language} code analysis specialist.

   {CORE_PRINCIPLES}
   {CORRECTNESS_PRINCIPLES}
   {SECURITY_PRINCIPLES}
   {PERFORMANCE_PRINCIPLES}

   LANGUAGE: {language}
   Adapt these universal principles to {language} idioms.
   """
   ```

2. Same for style, test, synthesizer agents

3. **Success Criteria**:
   - Total tokens per pipeline: ~900 (down from ~1900)
   - All agents use shared principles
   - No duplication across language pipelines

---

### Phase 3: Test Across Different Contexts (Week 2)

Test the same rules on different scenarios to verify universality:

1. **Different Languages**: Python, TypeScript, Java (if you add it)
2. **Different Maturity**: MVP code vs production code
3. **Different Styles**: Functional vs OOP, strict vs loose typing
4. **Different Teams**: Startup vs enterprise patterns

**Measure**:
- Pass rate remains 60-80% across contexts?
- False positives stay <15% across contexts?
- Rules don't break in unfamiliar codebases?

---

### Phase 4: Validate with Real Teams (Week 3-4)

1. Deploy to 3 different teams with different stacks
2. Collect feedback:
   - Are findings relevant?
   - Any false positives from context mismatch?
   - Any suggestions that don't apply?

3. Refine principles based on feedback

---

## Anti-Pattern Detection

Watch for these signs that rules are too project-specific:

🚩 **References specific files**: "Check docs/patterns.md"
🚩 **Names specific tools**: "Use Ruff", "Use ESLint"
🚩 **Prescribes process**: "Update Jira", "Tag with version"
🚩 **Assumes architecture**: "Use DI", "Separate layers"
🚩 **Requires frameworks**: "Use pytest", "Use Jest"
🚩 **Enforces conventions**: "test_<name>", "PascalCase classes"
🚩 **Arbitrary thresholds**: "80% coverage", "Functions <50 lines"

✅ **Good organization principles**:
- Describe harm, not style
- Universal patterns, not specific implementations
- Adaptable thresholds, not rigid numbers
- Language-agnostic core with minimal adaptation

---

## Token Budget Breakdown (Final)

### Per-Language Pipeline

| Agent | Before | After | Savings |
|-------|--------|-------|---------|
| Analyzer | 500 | 250 | 50% |
| DesignChecker (was StyleChecker) | 300 | 250 | 17% |
| TestAnalyzer | 400 | 200 | 50% |
| FeedbackSynthesizer | 400 | 200 | 50% |
| Core (shared) | 300 | 150 | 50% |
| **Total per pipeline** | **1900** | **1050** | **45%** |

### Full System

| Component | Tokens |
|-----------|--------|
| Root Orchestrator | 150 |
| Python Pipeline | 1050 |
| TypeScript Pipeline | 1050 |
| **Total** | **2250** |

**Compared to Target**: 2250 / 5000 = 45% of budget (55% headroom)

**Benefit**: Massive headroom for:
- Adding more languages (Java, Go, Rust)
- More sophisticated analysis
- Better examples in prompts
- Context about specific PR

---

## Key Takeaway

**Organization-level rules should be principles that teach agents to think, not checklists that tell them what to do.**

**Bad** (Checklist):
```
1. Check if SQL uses parameterized queries
2. Check if secrets are in environment variables
3. Check if functions have docstrings
4. Check if tests follow naming convention
```

**Good** (Principles):
```
1. Flag demonstrated vulnerabilities (injection, secrets, etc.)
2. Flag code that's hard to understand (long functions, bad names)
3. Flag tests that wouldn't catch bugs (weak assertions, over-mocking)
4. Prioritize by actual harm (security > correctness > style)
```

The agent learns patterns across codebases instead of applying rigid rules to one codebase.

---

## Next Steps

1. ✅ **Validate approach**: Review this document, confirm direction
2. ⬜ **Create principle files**: Write 5 small Python files (~150-250 tokens each)
3. ⬜ **Update agent factory**: Inject principles into existing agents
4. ⬜ **Test on diverse PRs**: Python, TypeScript, different patterns
5. ⬜ **Measure universality**: Do rules work across different teams?
6. ⬜ **Iterate**: Refine based on false positives/negatives

Want me to start creating the actual principle files?
