"""Tests for Cedar policy engine and AVP client."""
import pytest
from cedar.policy_engine import CedarPolicyEngine, CedarPolicyDenied
from cedar.avp_client import AVPClient, AVPAuthorizationResult


@pytest.fixture
def engine():
    return CedarPolicyEngine(
        policy_store_id="test-policy-store",
        aws_region="us-east-1",
    )


def _make_badge(valid=True):
    return {
        "badge_id": "badge-test",
        "jwt": "eyJ.test.token" if valid else "",
        "task_scopes": [],
    }


@pytest.mark.asyncio
async def test_authorize_allows_valid_request(engine):
    await engine.authorize(
        principal_id="test-agent",
        action="weather.access",
        resource_domain="api.open-meteo.com",
        scopes=["weather:read"],
        badge=_make_badge(),
        delegating_user="sarah@example.com",
        task="weather_slack_notification",
    )


@pytest.mark.asyncio
async def test_avp_result_allow():
    result = AVPAuthorizationResult(decision="ALLOW", reasons=["policy-1"])
    assert result.is_allowed is True


@pytest.mark.asyncio
async def test_avp_result_deny():
    result = AVPAuthorizationResult(decision="DENY", reasons=["no-matching-policy"])
    assert result.is_allowed is False


@pytest.mark.asyncio
async def test_avp_client_placeholder():
    client = AVPClient(policy_store_id="test", aws_region="us-east-1")
    result = await client.is_authorized(
        principal={"entityType": "Agent", "entityId": "test"},
        action={"actionType": "Action", "actionId": "test.access"},
        resource={"entityType": "MCPServer", "entityId": "test.com"},
    )
    assert result.is_allowed  # placeholder always allows
