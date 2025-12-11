# Cost Analysis: Gemini vs Devstral2 Deployment

## Current Pricing (December 2025)

### Gemini 2.5 Pro (Vertex AI)
**Context < 200k tokens:**
- Input: **$1.25 per million tokens**
- Output: **$10.00 per million tokens**

**Context > 200k tokens:**
- Input: **$2.50 per million tokens**
- Output: **$15.00 per million tokens**

### Gemini 3.0 Pro (Vertex AI)
**Context < 200k tokens:**
- Input: **$2.00 per million tokens** (60% more expensive)
- Output: **$12.00 per million tokens** (20% more expensive)

**Context > 200k tokens:**
- Input: **$4.00 per million tokens** (60% more expensive)
- Output: **$18.00 per million tokens** (20% more expensive)

### Devstral2 Deployment (Custom Vertex AI Endpoint)
**Infrastructure Costs:**
- 4x H100 GPUs: **$9.80/hour each** = $39.20/hour
- Vertex AI Management: **$1.47/hour per GPU** = $5.88/hour
- VM Instance (n1-standard-4): **~$0.22/hour**
- **Total: ~$45.30/hour** = **$32,616/month** (24/7 operation)

**Operational Costs:**
- Storage (model artifacts): ~$50-200/month
- Network egress: Variable
- Monitoring/logging: ~$100-500/month
- **Total Ops: ~$150-700/month**

**Total Devstral2 Cost: ~$32,766 - $33,316/month**

## Token Usage Estimates for Code Review

Based on your agent architecture:

### Per Review Session (Typical PR)
- **Orchestrator Agent:**
  - Input: ~5,000 tokens (PR metadata, file list)
  - Output: ~500 tokens (routing decision)

- **Code Analyzer Agent (per language):**
  - Input: ~50,000 tokens (code files, context, principles)
  - Output: ~3,000 tokens (analysis summary)

- **Feedback Reviewer Agent:**
  - Input: ~10,000 tokens (analysis summaries, test info)
  - Output: ~2,000 tokens (synthesized feedback)

- **Publisher Agent:**
  - Input: ~5,000 tokens (all feedback)
  - Output: ~1,000 tokens (JSON output)

**Total per Review:**
- Input: ~70,000-80,000 tokens (assuming 1 language)
- Output: ~6,500 tokens
- **Total: ~76,500 tokens per review**

**With Context Caching (50-75% reduction):**
- Effective input: ~35,000-40,000 tokens
- **Total: ~41,500-46,500 tokens per review**

## Cost Calculations

### Scenario 1: Low Volume (100 reviews/month)
**Gemini 2.5 Pro:**
- Input: 100 × 40,000 = 4M tokens × $1.25 = **$5.00**
- Output: 100 × 6,500 = 650k tokens × $10.00 = **$6.50**
- **Total: $11.50/month**

**Gemini 3.0 Pro:**
- Input: 4M tokens × $2.00 = **$8.00**
- Output: 650k tokens × $12.00 = **$7.80**
- **Total: $15.80/month**

**Devstral2:**
- Fixed: **$32,766/month**
- **Cost per review: $327.66**

**Break-even:** Not viable at this volume

---

### Scenario 2: Medium Volume (1,000 reviews/month)
**Gemini 2.5 Pro:**
- Input: 1,000 × 40,000 = 40M tokens × $1.25 = **$50.00**
- Output: 1,000 × 6,500 = 6.5M tokens × $10.00 = **$65.00**
- **Total: $115.00/month**

**Gemini 3.0 Pro:**
- Input: 40M tokens × $2.00 = **$80.00**
- Output: 6.5M tokens × $12.00 = **$78.00**
- **Total: $158.00/month**

**Devstral2:**
- Fixed: **$32,766/month**
- **Cost per review: $32.77**

**Break-even:** Still not viable (282x more expensive)

---

### Scenario 3: High Volume (10,000 reviews/month)
**Gemini 2.5 Pro:**
- Input: 10,000 × 40,000 = 400M tokens × $1.25 = **$500.00**
- Output: 10,000 × 6,500 = 65M tokens × $10.00 = **$650.00**
- **Total: $1,150.00/month**

**Gemini 3.0 Pro:**
- Input: 400M tokens × $2.00 = **$800.00**
- Output: 65M tokens × $12.00 = **$780.00**
- **Total: $1,580.00/month**

**Devstral2:**
- Fixed: **$32,766/month**
- **Cost per review: $3.28**

**Break-even:** Still 28x more expensive than Gemini 2.5 Pro

---

### Scenario 4: Very High Volume (100,000 reviews/month)
**Gemini 2.5 Pro:**
- Input: 100,000 × 40,000 = 4B tokens × $1.25 = **$5,000.00**
- Output: 100,000 × 6,500 = 650M tokens × $10.00 = **$6,500.00**
- **Total: $11,500.00/month**

**Gemini 3.0 Pro:**
- Input: 4B tokens × $2.00 = **$8,000.00**
- Output: 650M tokens × $12.00 = **$7,800.00**
- **Total: $15,800.00/month**

**Devstral2:**
- Fixed: **$32,766/month**
- **Cost per review: $0.33**

**Break-even:** Devstral2 becomes cheaper at **~2.8M reviews/month** (28,000 reviews/day)

---

## Break-Even Analysis

### Devstral2 vs Gemini 2.5 Pro
**Break-even point:** ~2,850 reviews/month
- Below this: Gemini 2.5 Pro is cheaper
- Above this: Devstral2 becomes cost-effective

**At 10,000 reviews/month:**
- Gemini 2.5 Pro: $1,150/month
- Devstral2: $32,766/month
- **Devstral2 is 28.5x more expensive**

**At 100,000 reviews/month:**
- Gemini 2.5 Pro: $11,500/month
- Devstral2: $32,766/month
- **Devstral2 is 2.8x more expensive**

**At 200,000 reviews/month:**
- Gemini 2.5 Pro: $23,000/month
- Devstral2: $32,766/month
- **Devstral2 is 1.4x more expensive**

**At 300,000 reviews/month:**
- Gemini 2.5 Pro: $34,500/month
- Devstral2: $32,766/month
- **Devstral2 is 5% cheaper** ✅

### Devstral2 vs Gemini 3.0 Pro
**Break-even point:** ~2,000 reviews/month
- Below this: Gemini 3.0 Pro is cheaper
- Above this: Devstral2 becomes cost-effective

**At 10,000 reviews/month:**
- Gemini 3.0 Pro: $1,580/month
- Devstral2: $32,766/month
- **Devstral2 is 20.7x more expensive**

**At 100,000 reviews/month:**
- Gemini 3.0 Pro: $15,800/month
- Devstral2: $32,766/month
- **Devstral2 is 2.1x more expensive**

**At 200,000 reviews/month:**
- Gemini 3.0 Pro: $31,600/month
- Devstral2: $32,766/month
- **Devstral2 is 3.7% more expensive**

**At 250,000 reviews/month:**
- Gemini 3.0 Pro: $39,500/month
- Devstral2: $32,766/month
- **Devstral2 is 17% cheaper** ✅

## Key Considerations

### Devstral2 Advantages:
1. **No usage caps** - Unlimited requests
2. **Predictable costs** - Fixed monthly cost regardless of volume
3. **Better performance** - 72.2% SWE-Bench (close to GPT-4-Turbo)
4. **Data privacy** - Model runs in your GCP project

### Devstral2 Disadvantages:
1. **High fixed costs** - $32,766/month even with zero usage
2. **Infrastructure management** - Requires DevOps expertise
3. **Scaling challenges** - Fixed capacity (need to add more GPUs to scale)
4. **Opportunity cost** - Capital tied up in infrastructure

### Hybrid Approach (Recommended)
**Use Gemini 2.5 Pro as primary, Devstral2 as fallback:**
- Most reviews: Gemini 2.5 Pro (cheap, managed)
- When hitting caps: Devstral2 (unlimited, but expensive)
- **Cost:** Gemini costs + Devstral2 only when needed

**Break-even for hybrid:**
- If you hit caps on <2,000 reviews/month: Devstral2 not worth it
- If you hit caps on >10,000 reviews/month: Consider Devstral2
- If you hit caps on >100,000 reviews/month: Devstral2 makes sense

## Recommendations

### If You're Hitting Usage Caps:
1. **First:** Check if you can increase Gemini quota
2. **Second:** Optimize token usage (you already have context caching)
3. **Third:** Use fallback to Llama 4/Codestral (free, already implemented)
4. **Fourth:** Consider Devstral2 only if:
   - Volume > 200,000 reviews/month
   - Caps are hard limits (can't increase)
   - Quality is critical enough to justify cost

### Cost-Effective Alternatives:
1. **Llama 4** (already available): Free fallback, good quality
2. **Codestral** (already available): Free fallback, code-focused
3. **Request quota increase** from Google
4. **Optimize prompts** to reduce token usage

## Next Steps

To make an informed decision, you need:
1. **Current usage data:** How many reviews/month? How many tokens?
2. **Cap details:** What are your exact Gemini quotas?
3. **Growth projection:** Expected volume in 6-12 months?
4. **Quality requirements:** Is Devstral2's quality improvement worth the cost?

Would you like me to:
- Create a script to analyze your current token usage?
- Help request a quota increase from Google?
- Set up better cost monitoring/alerting?
