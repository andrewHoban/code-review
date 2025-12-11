# Model Strategy: GCP/Vertex AI Only

## Current Situation

**Primary:** Gemini 3.0 Pro (when available)
**Current:** Gemini 2.5 Pro (fallback until 3.0 available)
**Need:** Better than 2.5, cheaper than 3.0, **available in GCP/Vertex AI**

## What's Available in Vertex AI Model Garden

Based on our earlier check, your GCP project has access to:

### ✅ Available Now:
- **Llama 4** - `publishers/google/models/llama-4` (free)
- **Llama 3.3 70B** - `publishers/google/models/llama-3.3-70b` (free)
- **Llama 3 70B** - `publishers/google/models/llama-3-70b` (free)
- **Codestral** - `publishers/mistral-ai/models/codestral` (free)

### ❌ NOT Available in Vertex AI:
- **Devstral2** - Only available via Mistral AI API (not in Vertex AI)
- **Claude Sonnet 4.5** - Only available via Anthropic API (not in Vertex AI)

## Answer to Your Questions

### Q: Better than 2.5, cheaper than 3.0 (in GCP)?
**A: No direct option available in Vertex AI Model Garden**

**Available options:**
- **Llama 4** - Free, but quality is similar/slightly lower than Gemini 2.5
- **Codestral** - Free, code-focused, but quality similar to Gemini 2.5
- **Llama 3.3 70B** - Free, potentially better reasoning than Llama 4

**None are clearly better than Gemini 2.5 AND cheaper than 3.0 in GCP.**

### Q: When Gemini 3.0 hits limits, what to default to?
**A: Llama 4** (best available free option in Vertex AI)

**Fallback Chain:**
```
Gemini 3.0 Pro (primary)
    ↓ (hits limits)
Llama 4 (free, best reasoning in Vertex AI)
    ↓ (if Llama 4 fails)
Codestral (free, code-focused backup)
```

## Cost Comparison (GCP Only)

At 7,200 reviews/month:

| Model | Cost/Month | Quality | Available in GCP |
|-------|------------|---------|------------------|
| Gemini 3.0 | $1,958 | Excellent | ✅ Yes |
| Gemini 2.5 | $1,408 | Good | ✅ Yes |
| **Llama 4** | **$0** | Good | ✅ Yes (free) |
| Codestral | **$0** | Good (code) | ✅ Yes (free) |

## Recommendation for GCP-Only Strategy

### Current Setup (Already Implemented):
1. **Primary:** Gemini 3.0 Pro (when available)
2. **Fallback 1:** Gemini 2.5 Pro (current)
3. **Fallback 2:** Llama 4 (free, via Vertex AI)
4. **Fallback 3:** Codestral (free, code-focused)

### When Gemini 3.0 Hits Limits:
**Use Llama 4** - It's:
- ✅ Free (no cost)
- ✅ Available in Vertex AI
- ✅ Good quality (similar to Gemini 2.5)
- ✅ No usage caps

### To Get Better Than 2.5, Cheaper Than 3.0:
**This requires Devstral2 or Claude Sonnet 4.5, which are NOT in Vertex AI.**

**Options:**
1. **Wait for Google to add Devstral2 to Model Garden** (aspiration, not plan)
2. **Deploy Devstral2 as custom model** (requires infrastructure, $33k/month)
3. **Use current fallback chain** (Gemini 3.0 → Gemini 2.5 → Llama 4)

## Updated Fallback Strategy

Your current implementation already handles this correctly:
- Gemini 3.0 → Llama 4 (when 3.0 hits limits)
- Gemini 2.5 → Llama 4 (when 2.5 hits limits)

**No changes needed** - your router already uses the best available options in GCP.

## Summary

**Within GCP/Vertex AI:**
- ✅ Gemini 3.0 Pro: Best quality, $1,958/month
- ✅ Gemini 2.5 Pro: Good quality, $1,408/month
- ✅ Llama 4: Free fallback, similar quality to 2.5
- ❌ Devstral2: Not available (would need custom deployment)
- ❌ Claude 4.5: Not available (would need external API)

**When Gemini 3.0 hits limits → Use Llama 4 (free, available in GCP)**
