# Code Review Agent Model Architecture

## Visual Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         CODE REVIEW REQUEST                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR AGENT                                    │
│  Task: Detect languages, route to pipelines                             │
│  Model: Codestral (FREE) ──┐                                            │
│                            │                                            │
│                            │ (if fails)                                 │
│                            ▼                                            │
│                    Llama 4 (FREE fallback)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
    ┌───────────────────────┐      ┌───────────────────────┐
    │  PYTHON PIPELINE       │      │ TYPESCRIPT PIPELINE    │
    └───────────────────────┘      └───────────────────────┘
                    │                               │
        ┌───────────┴───────────┐      ┌───────────┴───────────┐
        │                       │      │                       │
        ▼                       ▼      ▼                       ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ CODE ANALYZER   │  │ FEEDBACK       │  │ CODE ANALYZER   │  │ FEEDBACK        │
│ AGENT           │  │ REVIEWER       │  │ AGENT           │  │ REVIEWER        │
│                 │  │ AGENT          │  │                 │  │ AGENT           │
│ Task: Analyze   │  │ Task: Synthesize│ │ Task: Analyze   │  │ Task: Synthesize│
│ structure,      │  │ feedback,       │  │ structure,      │  │ feedback,       │
│ design, style   │  │ prioritize     │  │ design, style   │  │ prioritize     │
│                 │  │                │  │                 │  │                │
│ Model:          │  │ Model:         │  │ Model:          │  │ Model:         │
│ Gemini 2.5 Pro │  │ Gemini 2.5 Pro │  │ Gemini 2.5 Pro │  │ Gemini 2.5 Pro │
│ ($0.20/review)  │  │ ($0.20/review) │  │ ($0.20/review) │  │ ($0.20/review) │
│        │        │  │        │        │  │        │        │  │        │        │
│        │ (if fails)          │ (if fails)          │ (if fails)          │ (if fails)
│        ▼        │  │        ▼        │  │        ▼        │  │        ▼        │
│  Llama 4 (FREE) │  │  Llama 4 (FREE) │  │  Llama 4 (FREE) │  │  Llama 4 (FREE) │
└─────────────────┘  └─────────────────┘  └─────────────────┘  └─────────────────┘
        │                       │                  │                       │
        └───────────┬───────────┘                  └───────────┬───────────┘
                    │                                           │
                    └───────────────┬───────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PUBLISHER AGENT                                  │
│  Task: Format final output as JSON                                      │
│  Model: Codestral (FREE) ──┐                                            │
│                            │                                            │
│                            │ (if fails)                                 │
│                            ▼                                            │
│                    Llama 4 (FREE fallback)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                        ┌───────────────────┐
                        │  FINAL OUTPUT     │
                        │  (JSON Review)    │
                        └───────────────────┘
```

## Model Usage by Agent

### FREE Models (No Cost)
```
┌─────────────────────┬──────────────────────┬─────────────────────┐
│   ORCHESTRATOR      │     PUBLISHER        │    FALLBACKS        │
├─────────────────────┼──────────────────────┼─────────────────────┤
│ Model: Codestral    │ Model: Codestral     │ Model: Llama 4      │
│ Cost: $0            │ Cost: $0             │ Cost: $0            │
│ Task: Routing       │ Task: JSON Format    │ Task: Backup        │
│ Why: Simple task    │ Why: Simple task     │ Why: Free fallback  │
└─────────────────────┴──────────────────────┴─────────────────────┘
```

### PAID Models (Gemini 2.5 Pro - $0.20/review)
```
┌─────────────────────┬──────────────────────┐
│   CODE ANALYZER     │  FEEDBACK REVIEWER    │
├─────────────────────┼──────────────────────┤
│ Model: Gemini 2.5   │ Model: Gemini 2.5     │
│       Pro           │       Pro             │
│ Cost: $0.20/review  │ Cost: $0.20/review    │
│ Task: Deep analysis │ Task: Synthesis      │
│ Why: Needs advanced │ Why: Needs advanced   │
│      reasoning      │      reasoning        │
└─────────────────────┴──────────────────────┘
```

## Cost Breakdown Per Review

### Before Optimization
```
Orchestrator:  Gemini 2.5 Pro    = $0.20
Code Analyzer: Gemini 2.5 Pro    = $0.20
Feedback:      Gemini 2.5 Pro    = $0.20
Publisher:     Gemini 2.5 Flash  = $0.10
───────────────────────────────────────
Total per review:                 = $0.70
```

### After Optimization
```
Orchestrator:  Codestral (FREE)  = $0.00  ✅ Saved $0.20
Code Analyzer: Gemini 2.5 Pro    = $0.20
Feedback:      Gemini 2.5 Pro    = $0.20
Publisher:     Codestral (FREE)  = $0.00  ✅ Saved $0.10
───────────────────────────────────────
Total per review:                 = $0.40
```

**Savings: $0.30 per review (43% cost reduction)**

## Fallback Chains

### Simple Tasks (Orchestrator, Publisher)
```
Primary:   Codestral (FREE)
    │
    │ (if fails)
    ▼
Fallback:  Llama 4 (FREE)
```

### Complex Tasks (Code Analyzer, Feedback Reviewer)
```
Primary:   Gemini 2.5 Pro ($0.20/review)
    │
    │ (if hits token limits)
    ▼
Fallback:   Llama 4 (FREE)
```

## Why This Makes Sense

### Simple Tasks → Free Models
- **Orchestrator**: Just needs to detect "Python" or "TypeScript" - simple pattern matching
- **Publisher**: Just needs to format JSON - no reasoning needed
- **Result**: Save $0.30 per review with no quality loss

### Complex Tasks → Gemini 2.5 Pro
- **Code Analyzer**: Needs to understand code structure, find bugs, check security
- **Feedback Reviewer**: Needs to synthesize multiple inputs, prioritize issues
- **Result**: Pay for quality where it matters

## Example Flow

```
1. PR comes in with Python files
   └─> Orchestrator (Codestral FREE) detects "Python"
       └─> Routes to Python Pipeline

2. Python Pipeline runs
   └─> Code Analyzer (Gemini 2.5 Pro $0.20) analyzes code
       └─> Finds 3 issues, calculates style score
   └─> Feedback Reviewer (Gemini 2.5 Pro $0.20) synthesizes
       └─> Creates prioritized feedback

3. Publisher formats output
   └─> Publisher (Codestral FREE) formats as JSON
       └─> Returns final review

Total Cost: $0.40 (vs $0.70 before)
```

## Key Insight

**We only pay for Gemini 2.5 Pro where we need advanced reasoning:**
- ✅ Code analysis (complex)
- ✅ Feedback synthesis (complex)
- ❌ Language detection (simple) → FREE
- ❌ JSON formatting (simple) → FREE
