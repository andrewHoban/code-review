# Code Review Bot Architecture & Deployment

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEVELOPER WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────┘

    Developer opens PR
           │
           ▼
    ┌──────────────┐
    │   GitHub     │
    │  Repository  │
    └──────┬───────┘
           │ Webhook Event
           │ (pull_request opened/updated)
           ▼

┌─────────────────────────────────────────────────────────────────────┐
│                    WEBHOOK SERVICE (Cloud Run)                      │
│  Location: europe-west1                                             │
│  Service: code-review-webhook                                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  1. Validate webhook signature                                     │
│  2. Extract PR context (files, diffs, metadata)                    │
│  3. Load repository configuration (.code-review.yml)               │
│  4. Call Agent Engine ──────────────────────┐                      │
│  5. Post review comments to GitHub          │                      │
│                                              │                      │
└──────────────────────────────────────────────┼──────────────────────┘
                                               │
                                               │ Query Agent
                                               ▼

┌─────────────────────────────────────────────────────────────────────┐
│                   AGENT ENGINE (Vertex AI)                          │
│  Location: europe-west1                                             │
│  Agent ID: 3659508948773371904                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │              Root Orchestrator Agent                         │  │
│  │              (gemini-2.5-pro)                                │  │
│  └────────┬──────────────────────────────────────────┬──────────┘  │
│           │                                           │             │
│           ├── Language Detection                     │             │
│           ├── Repository Context Tools               │             │
│           │                                           │             │
│  ┌────────▼──────────────────┐           ┌───────────▼──────────┐  │
│  │  Python Review Pipeline   │           │ TypeScript Pipeline  │  │
│  │  ────────────────────────  │           │ ───────────────────  │  │
│  │  1. Code Analyzer         │           │  1. Code Analyzer    │  │
│  │  2. Style Checker         │           │  2. Style Checker    │  │
│  │  3. Test Analyzer         │           │  3. Test Analyzer    │  │
│  │  4. Feedback Synthesizer  │           │  4. Synthesizer      │  │
│  └───────────────────────────┘           └──────────────────────┘  │
│                                                                     │
│  Returns: JSON with summary + inline comments                      │
│                                                                     │
└──────────────────────────────────────────┬──────────────────────────┘
                                           │
                                           │ Review Response
                                           ▼

┌─────────────────────────────────────────────────────────────────────┐
│                         GITHUB API                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  • Post summary comment on PR                                       │
│  • Post inline comments on specific lines                          │
│  • Use GitHub App installation token for auth                      │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────┐
    │   GitHub     │
    │  Pull Request│
    │  + Comments  │
    └──────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT FLOW                             │
└─────────────────────────────────────────────────────────────────────┘

CODE CHANGES:
├── app/ directory (Agent logic)
│   └── Triggers: Agent Engine deployment
│       └── Command: make deploy
│       └── Target: Vertex AI Agent Engine
│
└── webhook_service/ directory (GitHub integration)
    └── Triggers: Webhook Service deployment
        └── Command: make deploy-webhook
        └── Target: Cloud Run


AUTOMATED DEPLOYMENT:

    Developer commits to main branch
              │
              ▼
    ┌──────────────────────┐
    │  GitHub Actions      │
    │  Workflows           │
    └──────┬───────────────┘
           │
           ├─── app/** changed?
           │    └─→ .github/workflows/deploy.yml
           │         ├─ Run tests
           │         ├─ Authenticate to GCP
           │         ├─ Run make deploy
           │         └─→ Updates Agent Engine
           │
           └─── webhook_service/** changed?
                └─→ .github/workflows/deploy-webhook.yml
                     ├─ Run tests
                     ├─ Build Docker image
                     ├─ Push to GCR
                     └─→ Deploy to Cloud Run


MANUAL DEPLOYMENT:

    Local Development
         │
         ├─→ Agent Engine:
         │   └─ make test
         │   └─ make deploy
         │
         └─→ Webhook Service:
             └─ export GITHUB_APP_ID="..."
             └─ make deploy-webhook
```

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                          DATA FLOW                                  │
└─────────────────────────────────────────────────────────────────────┘

1. WEBHOOK RECEIVED
   ┌────────────────┐
   │ GitHub Webhook │
   │ POST /webhook  │
   └───────┬────────┘
           │
           │ Headers: X-Hub-Signature-256, X-GitHub-Event
           │ Body: PR metadata, changed files, etc.
           │
           ▼
   ┌────────────────────────┐
   │ Signature Validation   │
   │ (HMAC SHA256)          │
   └───────┬────────────────┘
           │
           ▼

2. CONTEXT EXTRACTION
   ┌────────────────────────────────────┐
   │ Extract PR Context                 │
   │ ────────────────────────────────   │
   │ • Changed files + diffs            │
   │ • Related files (imports)          │
   │ • Test files                       │
   │ • Repository metadata              │
   │ • PR metadata                      │
   └───────┬────────────────────────────┘
           │
           │ Input JSON (CodeReviewInput schema)
           │
           ▼

3. AGENT ENGINE QUERY
   ┌────────────────────────────────────┐
   │ Agent Engine API Call              │
   │ POST /reasoningEngines/:query      │
   └───────┬────────────────────────────┘
           │
           │ Multi-agent processing:
           │ • Detect language
           │ • Analyze code
           │ • Check style
           │ • Review tests
           │ • Synthesize feedback
           │
           ▼
   ┌────────────────────────────────────┐
   │ Response JSON                      │
   │ ────────────────────────────────   │
   │ • summary: "## Review Summary..."  │
   │ • inline_comments: [...]           │
   │ • overall_status: "NEEDS_CHANGES"  │
   │ • metrics: {...}                   │
   └───────┬────────────────────────────┘
           │
           ▼

4. POST COMMENTS
   ┌────────────────────────────────────┐
   │ GitHub API Calls                   │
   │ ────────────────────────────────   │
   │ • POST /issues/{pr}/comments       │
   │ • POST /pulls/{pr}/comments        │
   │ (using GitHub App install token)   │
   └────────────────────────────────────┘
```

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SECURITY LAYERS                              │
└─────────────────────────────────────────────────────────────────────┘

AUTHENTICATION:
├── GitHub → Webhook Service
│   └── HMAC SHA256 signature validation
│       └── Secret stored in Google Secret Manager
│
├── Webhook Service → Agent Engine
│   └── GCP Application Default Credentials
│       └── Service Account with aiplatform.user role
│
└── Webhook Service → GitHub API
    └── GitHub App JWT + Installation Token
        └── Private key stored in Google Secret Manager


AUTHORIZATION:
├── GitHub App Permissions
│   ├── Pull requests: Read & Write
│   ├── Contents: Read-only
│   └── Metadata: Read-only
│
├── Cloud Run Service Account
│   ├── roles/aiplatform.user (Agent Engine access)
│   ├── roles/secretmanager.secretAccessor (Secrets)
│   └── roles/datastore.user (Firestore)
│
└── Installation Tracking
    └── Firestore tracks which repos have app installed
        └── Only processes webhooks for installed repos


SECRETS MANAGEMENT:
┌─────────────────────────────────┐
│   Google Secret Manager         │
├─────────────────────────────────┤
│ • github-app-private-key        │
│   └── JWT signing for GitHub    │
│                                  │
│ • github-webhook-secret          │
│   └── Webhook signature verify  │
└─────────────────────────────────┘
         │
         │ Secrets mounted at runtime
         ▼
┌─────────────────────────────────┐
│   Cloud Run Instance            │
│   (Ephemeral, short-lived)      │
└─────────────────────────────────┘
```

## Monitoring & Observability

```
┌─────────────────────────────────────────────────────────────────────┐
│                     MONITORING STACK                                │
└─────────────────────────────────────────────────────────────────────┘

LOGGING:
├── Cloud Run Logs
│   ├── Request/response logs
│   ├── Application logs (Flask)
│   └── Error stack traces
│
└── Agent Engine Logs
    ├── Agent execution traces
    ├── Model API calls
    └── Performance metrics


METRICS:
├── Cloud Run Metrics
│   ├── Request count
│   ├── Request latency
│   ├── Error rate
│   ├── Container CPU/memory
│   └── Instance count
│
└── Agent Engine Metrics
    ├── Query latency
    ├── Token usage
    └── Success/error rate


TRACING:
└── Cloud Trace
    ├── End-to-end request traces
    ├── Agent execution breakdown
    └── Identify bottlenecks


ALERTING (Optional):
└── Cloud Monitoring
    ├── Error rate > 10%
    ├── Latency > 5 minutes
    └── Service unavailable
```

## Cost Structure

```
┌─────────────────────────────────────────────────────────────────────┐
│                         COST BREAKDOWN                              │
└─────────────────────────────────────────────────────────────────────┘

PER PR REVIEW COSTS:
├── Agent Engine Query
│   ├── Gemini 2.5 Pro: ~$0.01-0.05 per PR
│   └── Depends on: PR size, file count
│
├── Cloud Run Execution
│   ├── ~$0.0001 per PR
│   └── First 2M requests/month free
│
└── GitHub API Calls
    └── Free (within rate limits)


MONTHLY FIXED COSTS (typical usage):
├── Cloud Run
│   ├── ~$5-20/month
│   └── Depends on: traffic, instances
│
├── Secret Manager
│   ├── ~$0.06/month
│   └── Per active secret version
│
├── Firestore
│   ├── ~$0.10-1.00/month
│   └── Depends on: reads/writes
│
└── Container Registry
    ├── ~$1-5/month
    └── Image storage

ESTIMATED TOTAL:
├── Low usage (10 PRs/day): ~$10-20/month
├── Medium usage (50 PRs/day): ~$30-60/month
└── High usage (200 PRs/day): ~$100-200/month
```

## Scaling Characteristics

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCALING BEHAVIOR                                 │
└─────────────────────────────────────────────────────────────────────┘

WEBHOOK SERVICE (Cloud Run):
├── Auto-scaling: 0-10 instances
├── Cold start: ~2-3 seconds
├── Warm request: <100ms
├── Max concurrent: 80 requests/instance
└── Request timeout: 300 seconds (5 minutes)


AGENT ENGINE:
├── Scaling: Managed by Google
├── Query latency: 30-120 seconds
├── Concurrent queries: High (exact limit unknown)
└── Token limits: Per model tier


BOTTLENECKS:
├── Agent Engine query time (largest)
│   └── Mitigation: Optimize prompts, reduce context size
│
├── GitHub API rate limits
│   └── 5000 requests/hour per installation
│   └── Mitigation: Batch comments, cache data
│
└── Cloud Run cold starts
    └── Mitigation: Set min-instances=1 (increases cost)
```

## Disaster Recovery

```
┌─────────────────────────────────────────────────────────────────────┐
│                   DISASTER RECOVERY                                 │
└─────────────────────────────────────────────────────────────────────┘

BACKUP STRATEGY:
├── Source Code
│   └── Git repository (GitHub)
│       └── Full history, tags, branches
│
├── Container Images
│   └── Google Container Registry
│       └── Multiple tagged versions
│
├── Secrets
│   └── Google Secret Manager
│       └── Versioned, can rollback
│
└── Configuration
    └── Infrastructure as Code
        └── Documented in WEBHOOK_DEPLOYMENT.md


RECOVERY PROCEDURES:
├── Webhook Service Failure
│   ├── Auto-restart (Cloud Run)
│   ├── Rollback to previous revision
│   └── RTO: <5 minutes
│
├── Agent Engine Failure
│   ├── Redeploy from previous commit
│   └── RTO: ~10 minutes
│
└── Complete System Failure
    ├── Redeploy from scratch
    ├── Restore secrets from backup
    └── RTO: ~30 minutes


FAILOVER:
└── GitHub webhook retries
    ├── Retry on 5xx errors
    ├── Exponential backoff
    └── Max 3 attempts
```
