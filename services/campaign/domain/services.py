"""Campaign Domain — Domain Services (pure business logic, no infrastructure)."""

from __future__ import annotations

from services.campaign.domain.model.value_objects import ABVariant


class CampaignOptimizationService:
    """Pure domain logic for campaign optimization — segment matching and A/B analysis."""

    @staticmethod
    def match_segment(target_segment: str, customer_segment: str) -> bool:
        """Check whether a customer segment matches the campaign target.

        Supports exact match or wildcard 'all'.
        """
        if target_segment.lower() == "all":
            return True
        return target_segment.lower() == customer_segment.lower()

    @staticmethod
    def compare_variants(variants: list[ABVariant]) -> ABVariant | None:
        """Return the best-performing variant by conversion rate.

        Falls back to click rate when conversions are equal.
        Returns None if the list is empty.
        """
        if not variants:
            return None

        return max(variants, key=lambda v: (v.conversion_rate, v.click_rate))

    @staticmethod
    def calculate_variant_weights(variants: list[ABVariant]) -> dict[str, float]:
        """Re-balance variant weights based on performance (Thompson-sampling-like heuristic).

        Variants with higher conversion rates get proportionally more traffic.
        Returns a mapping of variant_id -> suggested weight.
        """
        if not variants:
            return {}

        total_conversions = sum(v.conversions for v in variants)

        # If no conversions yet, distribute evenly
        if total_conversions == 0:
            even_weight = 1.0 / len(variants)
            return {str(v.variant_id): round(even_weight, 4) for v in variants}

        weights: dict[str, float] = {}
        for v in variants:
            weights[str(v.variant_id)] = round(v.conversions / total_conversions, 4)
        return weights

    @staticmethod
    def generate_campaign_text_mock(
        campaign_name: str,
        campaign_type: str,
        target_segment: str,
        template: str,
    ) -> str:
        """Mock LLM-based campaign text generation.

        In production this would call the LLM via LangChain.
        """
        return (
            f"[Generated] Campaign '{campaign_name}' ({campaign_type}) "
            f"targeting '{target_segment}': {template or 'Exclusive offer for you!'}"
        )
