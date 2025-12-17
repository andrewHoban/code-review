# Webhook Service (DEPRECATED)

⚠️ **This service is deprecated and no longer in use.**

The code review system now uses GitHub Actions workflows instead of webhooks. This provides:
- Simpler setup (no infrastructure needed)
- No organization policy issues
- Easier adoption for teams

## Migration

If you were using the webhook service, please migrate to the GitHub Actions approach:

1. See [Team Adoption Guide](../docs/TEAM_ADOPTION_GUIDE.md) for setup instructions
2. Copy the workflow file from `.github/workflows/STARTER-pr-review.yml`
3. Add the required secret: `GCP_PROJECT_NUMBER`

## Why Deprecated?

The webhook-based GitHub App approach required:
- Cloud Run service deployment
- Load balancer setup (due to organization policies)
- Complex infrastructure configuration
- Ongoing maintenance

The GitHub Actions approach is:
- ✅ Zero infrastructure
- ✅ 5-minute setup
- ✅ Organization policy compliant
- ✅ Self-service for teams

## Historical Reference

This directory contains the original webhook service implementation. It's kept for reference but should not be used for new deployments.

For questions or issues, see the main project documentation.
