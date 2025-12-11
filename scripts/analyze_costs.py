#!/usr/bin/env python3
"""
Cost analysis tool for Gemini vs Devstral2 deployment.

Usage:
    python scripts/analyze_costs.py --reviews-per-month 10000
    python scripts/analyze_costs.py --tokens-per-review 50000 --reviews-per-month 5000
"""

import argparse

# Pricing (per million tokens)
GEMINI_25_PRO_PRICING = {
    "input_under_200k": 1.25,
    "output_under_200k": 10.00,
    "input_over_200k": 2.50,
    "output_over_200k": 15.00,
}

GEMINI_30_PRO_PRICING = {
    "input_under_200k": 2.00,
    "output_under_200k": 12.00,
    "input_over_200k": 4.00,
    "output_over_200k": 18.00,
}

# Devstral2 deployment costs
DEVSTRAL2_MONTHLY = 32766  # 4x H100 GPUs + management fees
DEVSTRAL2_OPS = 500  # Storage, monitoring, etc.
DEVSTRAL2_TOTAL = DEVSTRAL2_MONTHLY + DEVSTRAL2_OPS


def calculate_gemini_cost(
    reviews_per_month: int,
    tokens_per_review: int,
    input_ratio: float = 0.85,
    pricing: dict[str, float] = GEMINI_25_PRO_PRICING,
    context_over_200k: bool = False,
) -> dict[str, float]:
    """
    Calculate Gemini API costs.

    Args:
        reviews_per_month: Number of reviews per month
        tokens_per_review: Total tokens per review (input + output)
        input_ratio: Ratio of input tokens (default 0.85)
        pricing: Pricing dictionary
        context_over_200k: Whether context exceeds 200k tokens

    Returns:
        Dictionary with cost breakdown
    """
    tier = "over_200k" if context_over_200k else "under_200k"

    total_tokens = reviews_per_month * tokens_per_review
    input_tokens = int(total_tokens * input_ratio)
    output_tokens = total_tokens - input_tokens

    input_cost = (input_tokens / 1_000_000) * pricing[f"input_{tier}"]
    output_cost = (output_tokens / 1_000_000) * pricing[f"output_{tier}"]
    total_cost = input_cost + output_cost

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
        "cost_per_review": total_cost / reviews_per_month
        if reviews_per_month > 0
        else 0,
    }


def calculate_break_even(
    tokens_per_review: int,
    input_ratio: float = 0.85,
    gemini_pricing: dict[str, float] = GEMINI_25_PRO_PRICING,
    context_over_200k: bool = False,
) -> int:
    """
    Calculate break-even point (reviews/month) for Devstral2.

    Args:
        tokens_per_review: Total tokens per review
        input_ratio: Ratio of input tokens
        gemini_pricing: Gemini pricing
        context_over_200k: Whether context exceeds 200k tokens

    Returns:
        Number of reviews per month needed to break even
    """
    tier = "over_200k" if context_over_200k else "under_200k"

    # Cost per review with Gemini
    input_tokens_per_review = int(tokens_per_review * input_ratio)
    output_tokens_per_review = tokens_per_review - input_tokens_per_review

    input_cost_per_review = (input_tokens_per_review / 1_000_000) * gemini_pricing[
        f"input_{tier}"
    ]
    output_cost_per_review = (output_tokens_per_review / 1_000_000) * gemini_pricing[
        f"output_{tier}"
    ]
    cost_per_review = input_cost_per_review + output_cost_per_review

    # Break-even: DEVSTRAL2_TOTAL = reviews * cost_per_review
    if cost_per_review == 0:
        # Infinite break-even - return a very large number as sentinel
        return 999_999_999

    break_even = DEVSTRAL2_TOTAL / cost_per_review
    return int(break_even)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze costs for Gemini vs Devstral2"
    )
    parser.add_argument(
        "--reviews-per-month",
        type=int,
        default=10000,
        help="Number of reviews per month (default: 10000)",
    )
    parser.add_argument(
        "--tokens-per-review",
        type=int,
        default=46500,
        help="Total tokens per review (default: 46500, with context caching)",
    )
    parser.add_argument(
        "--input-ratio",
        type=float,
        default=0.85,
        help="Ratio of input tokens (default: 0.85)",
    )
    parser.add_argument(
        "--context-over-200k",
        action="store_true",
        help="Use pricing for context > 200k tokens",
    )

    args = parser.parse_args()

    print("=" * 70)
    print("Cost Analysis: Gemini vs Devstral2")
    print("=" * 70)
    print("\nAssumptions:")
    print(f"  Reviews per month: {args.reviews_per_month:,}")
    print(f"  Tokens per review: {args.tokens_per_review:,}")
    print(f"  Input ratio: {args.input_ratio:.1%}")
    print(
        f"  Context tier: {'> 200k tokens' if args.context_over_200k else '< 200k tokens'}"
    )
    print()

    # Calculate Gemini 2.5 Pro costs
    gemini_25 = calculate_gemini_cost(
        args.reviews_per_month,
        args.tokens_per_review,
        args.input_ratio,
        GEMINI_25_PRO_PRICING,
        args.context_over_200k,
    )

    # Calculate Gemini 3.0 Pro costs
    gemini_30 = calculate_gemini_cost(
        args.reviews_per_month,
        args.tokens_per_review,
        args.input_ratio,
        GEMINI_30_PRO_PRICING,
        args.context_over_200k,
    )

    # Devstral2 costs
    devstral2_cost_per_review = (
        DEVSTRAL2_TOTAL / args.reviews_per_month
        if args.reviews_per_month > 0
        else DEVSTRAL2_TOTAL
    )

    print("Monthly Costs:")
    print("-" * 70)
    print(
        f"Gemini 2.5 Pro:  ${gemini_25['total_cost']:,.2f} (${gemini_25['cost_per_review']:.4f} per review)"
    )
    print(
        f"Gemini 3.0 Pro:  ${gemini_30['total_cost']:,.2f} (${gemini_30['cost_per_review']:.4f} per review)"
    )
    print(
        f"Devstral2:       ${DEVSTRAL2_TOTAL:,.2f} (${devstral2_cost_per_review:.4f} per review)"
    )
    print()

    print("Comparison:")
    print("-" * 70)
    gemini_25_multiplier = (
        DEVSTRAL2_TOTAL / gemini_25["total_cost"]
        if gemini_25["total_cost"] > 0
        else float("inf")
    )
    gemini_30_multiplier = (
        DEVSTRAL2_TOTAL / gemini_30["total_cost"]
        if gemini_30["total_cost"] > 0
        else float("inf")
    )

    print(
        f"Devstral2 is {gemini_25_multiplier:.1f}x more expensive than Gemini 2.5 Pro"
    )
    print(
        f"Devstral2 is {gemini_30_multiplier:.1f}x more expensive than Gemini 3.0 Pro"
    )
    print()

    # Break-even analysis
    print("Break-Even Analysis:")
    print("-" * 70)
    be_25 = calculate_break_even(
        args.tokens_per_review,
        args.input_ratio,
        GEMINI_25_PRO_PRICING,
        args.context_over_200k,
    )
    be_30 = calculate_break_even(
        args.tokens_per_review,
        args.input_ratio,
        GEMINI_30_PRO_PRICING,
        args.context_over_200k,
    )

    print(f"Break-even vs Gemini 2.5 Pro: {be_25:,} reviews/month")
    print(f"Break-even vs Gemini 3.0 Pro: {be_30:,} reviews/month")
    print()

    if args.reviews_per_month < be_25:
        print(
            f"✅ At {args.reviews_per_month:,} reviews/month, Gemini 2.5 Pro is cheaper"
        )
    elif args.reviews_per_month < be_25 * 1.2:
        print(f"⚠️  At {args.reviews_per_month:,} reviews/month, approaching break-even")
    else:
        print(
            f"💰 At {args.reviews_per_month:,} reviews/month, Devstral2 becomes cost-effective"
        )

    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
