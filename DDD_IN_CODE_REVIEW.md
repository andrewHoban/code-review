# Domain-Driven Design in Code Review

## TL;DR

**✅ Include**: Strategic DDD principles (separation of concerns, ubiquitous language)
**❌ Exclude**: Tactical DDD patterns (Entities, Aggregates, Repositories - implementation details)

**Token Cost**: +50 tokens (250 total for design principles)

---

## What is Strategic vs Tactical DDD?

### Strategic DDD (Universal Principles) ✅

**Core Concepts**:
1. **Ubiquitous Language**: Use domain terms in code
2. **Bounded Contexts**: Clear boundaries between different domains
3. **Domain vs Infrastructure Separation**: Business logic separate from technical concerns

**Why Universal**:
- Applies to any codebase (web app, CLI tool, data pipeline)
- Works in any paradigm (OOP, functional, procedural)
- Improves maintainability regardless of stack
- Language/framework agnostic

**Example Violations to Flag**:

```python
# BAD: Business logic mixed with infrastructure
def process_order(order_data):
    # Validation (domain logic)
    if order_data['total'] < 0:
        raise ValueError("Negative total")

    # HTTP call (infrastructure)
    response = requests.post('https://api.payment.com', json=order_data)

    # Database write (infrastructure)
    db.execute("INSERT INTO orders VALUES (?)", order_data)

    # Email (infrastructure)
    send_email(order_data['customer_email'], "Order confirmed")

# GOOD: Separation of concerns
def validate_order(order: Order) -> ValidationResult:
    """Pure domain logic - no infrastructure"""
    if order.total < 0:
        return ValidationResult.error("Negative total")
    return ValidationResult.success()

def save_order(order: Order, repository: OrderRepository):
    """Infrastructure concern - injected dependency"""
    repository.save(order)
```

```typescript
// BAD: Technical names, not domain language
const x = calculateStuff(data);
if (x > threshold) {
    doThing();
}

// GOOD: Ubiquitous language from domain
const creditLimit = calculateCustomerCreditLimit(customer);
if (creditLimit > purchaseAmount) {
    approvePurchase();
}
```

---

### Tactical DDD (Implementation Patterns) ❌

**Core Concepts**:
1. **Entities**: Objects with identity
2. **Value Objects**: Immutable objects without identity
3. **Aggregates**: Clusters of domain objects
4. **Repositories**: Data access abstraction
5. **Domain Events**: Messages between bounded contexts
6. **Factories**: Complex object creation

**Why NOT Universal**:
- Implementation choice (teams may use different patterns)
- Overkill for simple domains (CRUD app doesn't need Aggregates)
- Requires shared team understanding
- Can be applied incorrectly (cargo cult)

**Examples to SKIP**:

```python
# DON'T FLAG: "This should be a Value Object"
# DON'T FLAG: "Use a Repository pattern here"
# DON'T FLAG: "This Aggregate is too large"
# DON'T FLAG: "Missing Domain Events"
```

These are **architectural decisions** for the team to make, not code review issues.

---

## What to Flag vs What to Skip

### ✅ Flag (Strategic DDD)

| Issue | Evidence | Fix |
|-------|----------|-----|
| Business logic mixed with infrastructure | "This validation function makes HTTP calls" | Separate domain logic from I/O |
| Technical names for domain concepts | "Variable 'x' represents customer credit limit" | Use domain language: `creditLimit` |
| Domain logic in infrastructure layer | "Order validation is in the database repository" | Move validation to domain layer |
| Unclear domain boundaries | "User service handles payments" | Separate concerns or explain why |

### ❌ Skip (Tactical DDD)

| Pattern | Why Skip |
|---------|----------|
| "This should be an Entity" | Implementation choice |
| "Use Value Objects for money" | Team decision |
| "Missing Repository pattern" | Architectural choice |
| "Aggregate roots aren't enforced" | Pattern adoption choice |
| "No Domain Events" | Feature decision |

---

## Code Review Prompt (Strategic DDD)

```python
DOMAIN_DRIVEN_DESIGN = """
4. Domain-Driven Design (Strategic Principles):

   a) Separation of Concerns:
      - Flag if: Business logic mixed with infrastructure concerns
      - Evidence: "This order validation function makes HTTP calls and writes to database"
      - Fix: Separate domain logic (validation) from infrastructure (HTTP, DB)
      - Example: Extract validate_order() that's pure business logic

   b) Ubiquitous Language:
      - Flag if: Domain concepts not clearly named in code
      - Evidence: "Variable 'x' represents customer credit limit but name unclear"
      - Fix: Use domain language in code: creditLimit, not x
      - Example: Rename calculate_stuff() to calculate_customer_credit_limit()

   c) Domain vs Infrastructure:
      - Flag if: Infrastructure details leak into domain logic
      - Evidence: "Business rule 'orders over $1000 require approval' is in SQL query"
      - Fix: Move business rules to domain layer, keep SQL for data access only

   Skip:
   - Tactical patterns (don't prescribe Entities, Repositories, Aggregates)
   - Architecture choices (let teams decide implementation)
   - Pattern enforcement (if team doesn't use DDD tactically, that's fine)
"""
```

---

## Examples: Good Strategic DDD Review Comments

### ✅ Good Comment (Strategic - Separation)

```markdown
**Issue**: Business logic mixed with infrastructure
**File**: `src/orders/process_order.py:45-67`
**Evidence**: This function validates orders (business logic) and makes HTTP calls (infrastructure)
```python
def process_order(order_data):
    if order_data['total'] < 0:  # Domain logic
        raise ValueError("Invalid")
    response = requests.post(...)  # Infrastructure
```
**Risk**: Hard to test business rules, changes to payment API affect validation
**Fix**: Separate concerns:
```python
def validate_order(order: Order) -> bool:
    """Pure domain logic - testable without HTTP"""
    return order.total >= 0

def process_order(order: Order, payment_service: PaymentService):
    if not validate_order(order):
        raise ValidationError("Invalid order")
    payment_service.charge(order)  # Infrastructure injected
```
```

### ✅ Good Comment (Strategic - Language)

```markdown
**Issue**: Technical names instead of domain language
**File**: `src/customers/service.ts:23`
**Evidence**: Variable `x` represents customer credit limit but name unclear
```typescript
const x = calculateStuff(customer);
if (x > amount) { approve(); }
```
**Risk**: Future developers won't understand business meaning
**Fix**: Use domain language:
```typescript
const creditLimit = calculateCustomerCreditLimit(customer);
if (creditLimit > purchaseAmount) {
    approvePurchase();
}
```
```

---

## Examples: Bad Tactical DDD Review Comments

### ❌ Bad Comment (Tactical - Prescriptive)

```markdown
**Issue**: Money should be a Value Object
**Fix**: Create a Money class with currency and amount
```

**Why Bad**:
- Prescribes implementation pattern
- May be overkill for simple use case
- Team may have chosen not to use Value Objects
- Not an actual bug or risk

### ❌ Bad Comment (Tactical - Architecture)

```markdown
**Issue**: Missing Repository pattern
**Fix**: Create OrderRepository interface and implementation
```

**Why Bad**:
- Architectural choice, not code quality issue
- Team may use different patterns (Active Record, etc.)
- No demonstrated harm
- Style preference

### ❌ Bad Comment (Tactical - Pattern Enforcement)

```markdown
**Issue**: Aggregate boundaries not clear
**Fix**: Make Order an Aggregate Root and prevent direct access to OrderLine
```

**Why Bad**:
- Requires team-wide DDD adoption
- Pattern enforcement, not bug detection
- May not be appropriate for this domain complexity
- No clear harm demonstrated

---

## Decision Matrix: DDD in Code Review

| Principle | Universal? | Include? | Reasoning |
|-----------|------------|----------|-----------|
| Separation of Concerns | ✅ Yes | ✅ Yes | Applies to all codebases |
| Ubiquitous Language | ✅ Yes | ✅ Yes | Improves readability always |
| Bounded Contexts | ⚠️ Medium | ✅ Yes | Flag unclear boundaries |
| Entities | ❌ No | ❌ No | Implementation choice |
| Value Objects | ❌ No | ❌ No | Pattern choice |
| Aggregates | ❌ No | ❌ No | Architecture decision |
| Repositories | ❌ No | ❌ No | Pattern choice |
| Domain Events | ❌ No | ❌ No | Feature decision |
| Factories | ❌ No | ❌ No | Pattern choice |

---

## Token Budget Impact

### Before (SOLID, DRY, YAGNI only)
```python
DESIGN_PRINCIPLES = """
1. Single Responsibility (40 tokens)
2. DRY (40 tokens)
3. YAGNI (40 tokens)
4. Readability (40 tokens)
Total: 200 tokens
"""
```

### After (+ Strategic DDD)
```python
DESIGN_PRINCIPLES = """
1. Single Responsibility (40 tokens)
2. DRY (40 tokens)
3. YAGNI (40 tokens)
4. Domain-Driven Design - Strategic (50 tokens)
5. Readability (40 tokens)
Total: 250 tokens
"""
```

**Cost**: +50 tokens per language pipeline = +100 tokens total
**Budget**: 2250 / 5000 = 45% (55% headroom remaining)

---

## When NOT to Include DDD

Skip DDD principles if your organization:

1. **Doesn't use DDD terminology** - Will confuse teams
2. **Builds simple CRUD apps** - Overhead without benefit
3. **Has diverse tech stacks** - Some stacks don't map well to DDD
4. **Junior-heavy teams** - DDD concepts may be unfamiliar

In these cases, just use:
- ✅ SOLID (especially SRP - separation of concerns)
- ✅ DRY
- ✅ YAGNI
- ✅ Readability

These capture most of strategic DDD benefits without the terminology.

---

## Recommendation for Your Org

**Include Strategic DDD** because:

1. ✅ You identified it as an organizational principle
2. ✅ Strategic DDD is universal (separation, naming)
3. ✅ Only +50 tokens (minimal cost)
4. ✅ Significant benefit (better domain modeling)
5. ✅ Doesn't prescribe implementation patterns

**Explicitly exclude** tactical DDD to avoid:
- ❌ Prescribing architecture
- ❌ Pattern enforcement
- ❌ False positives on valid code that doesn't use DDD patterns

---

## Summary

**Include in `design_principles.py`**:
```python
"""
4. Domain-Driven Design (Strategic Principles):
   - Flag: Business logic mixed with infrastructure
   - Flag: Domain concepts not clearly named
   - Skip: Tactical patterns (Entities, Repositories, etc.)
   - Skip: Architecture prescriptions
"""
```

**Cost**: +50 tokens
**Benefit**: Better separation of concerns, clearer domain modeling
**Risk**: Low (strategic only, no pattern enforcement)

**Verdict**: ✅ **Include Strategic DDD**
