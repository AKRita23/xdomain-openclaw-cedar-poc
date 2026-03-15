"""Agent configuration for cross-domain identity PoC."""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    url: str
    auth_domain: str
    scopes: List[str] = field(default_factory=list)


@dataclass
class AgentConfig:
    """Top-level agent configuration."""
    agent_id: str = os.getenv("AGENT_ID", "openclaw-agent-001")
    agent_name: str = "OpenClaw Cross-Domain Agent"

    # AGNTCY Identity Service
    identity_service_url: str = os.getenv("AGNTCY_IDENTITY_SERVICE_URL", "http://localhost:8080")
    issuer_did: str = os.getenv("AGNTCY_ISSUER_DID", "")

    # AGNTCY Badge
    agntcy_badge_well_known: str = os.getenv("AGNTCY_BADGE_WELL_KNOWN", "")
    agntcy_badge_id: str = os.getenv("AGNTCY_BADGE_ID", "")
    agntcy_metadata_id: str = os.getenv("AGNTCY_METADATA_ID", "")

    # AWS
    aws_secrets_region: str = os.getenv("AWS_REGION", "us-east-1")

    # Okta XAA (ID-JAG)
    okta_domain: str = os.getenv("OKTA_DOMAIN", "")
    okta_client_id: str = os.getenv("OKTA_CLIENT_ID", "")
    okta_client_secret: str = os.getenv("OKTA_CLIENT_SECRET", "")
    okta_audience: str = os.getenv("OKTA_AUDIENCE", "")
    okta_auth_server_id: str = os.getenv("OKTA_AUTH_SERVER_ID", "default")
    okta_token_endpoint: str = os.getenv("OKTA_TOKEN_ENDPOINT", "")
    okta_issuer: str = os.getenv("OKTA_ISSUER", "")

    # Amazon Verified Permissions
    avp_policy_store_id: str = os.getenv("AVP_POLICY_STORE_ID", "")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")

    # Delegating user
    delegating_user: str = os.getenv("DELEGATING_USER", "sarah@example.com")

    # MCP Server targets
    mcp_servers: Dict[str, MCPServerConfig] = field(default_factory=lambda: {
        "weather": MCPServerConfig(
            name="weather",
            url=os.getenv("WEATHER_MCP_URL", ""),
            auth_domain="api.open-meteo.com",
            scopes=["weather:read"],
        ),
        "slack": MCPServerConfig(
            name="slack",
            url=os.getenv("SLACK_MCP_URL", "http://localhost:9003"),
            auth_domain="slack.com",
            scopes=["slack:chat:write", "slack:channels:read"],
        ),
    })
