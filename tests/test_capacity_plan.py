import pytest

from scripts.capacity_plan import estimate
from training.provenance import software_manifest


def test_capacity_estimate_is_explicitly_not_an_sla_or_quality_claim():
    report = {"runs": [{"http_status": 200, "approx_decode_tokens_per_second": 5.85,
                        "first_content_seconds": 3.9135}]}
    result = estimate(report, 2048, 120)
    assert 353 < result["estimated_budget_seconds"] < 354
    assert result["required_decode_tokens_per_second"] > 17
    assert result["output_token_budget"] == 2048
    assert result["estimate_only"] and not result["quality_verified"] and not result["p95_measured"]


def test_no_capacity_claim_from_a_failed_measurement():
    with pytest.raises(ValueError, match="No usable"):
        estimate({"runs": [{"http_status": 503}]}, 2048, 120)


@pytest.mark.parametrize("tokens,target", [(0, 120), (8193, 120), (2048, 0), (2048, float("nan"))])
def test_invalid_capacity_inputs(tokens, target):
    with pytest.raises(ValueError):
        estimate({"runs": []}, tokens, target)


def test_software_manifest_has_no_secrets_or_claim_of_training():
    result = software_manifest()
    assert set(result) == {"python", "libraries"}
    assert "torch" in result["libraries"]
    assert "trained" not in result
