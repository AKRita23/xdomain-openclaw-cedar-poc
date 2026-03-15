# Cross-Domain Agent Identity PoC — Version B: Cedar + Amazon Verified Permissions TBAC

> OpenClaw agent executing cross-domain tasks on behalf of a human user (Sarah),
> with identity attestation via AGNTCY Identity badges and Task-Based Access
> Control (TBAC) enforcement via Cedar policies evaluated by Amazon Verified Permissions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Human User (Sarah)                          │
│                     delegates task to agent                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      OpenClaw Agent                                 │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────────────┐ │
│  │ AGNTCY Badge │  │  Okta XAA        │  │ Cedar Policy Engine  │ │
│  │ (Identity)   │  │  (ID-JAG)        │  │ (Amazon Verified     │ │
│  │              │  │                  │  │  Permissions)         │ │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬────────────┘ │
└─────────┼───────────────────┼───────────────────────┼──────────────┘
          │                   │                       │
          ▼                   ▼                       ▼
┌──────────────┐                             ┌──────────────┐
│   Weather    │                             │    Slack     │
│  MCP Server  │                             │  MCP Server  │
│              │                             │              │
│ Domain:      │                             │ Domain:      │
│ api.open-    │                             │ slack.com    │
│ meteo.com    │                             │              │
└──────────────┘                             └──────────────┘
```

## Layers

### 1. AGNTCY Identity Badge
- The agent obtains a verifiable identity badge from the AGNTCY Identity Service
- Badge contains: agent_id, delegating user, issuer DID, signed JWT
- Badge proves the agent is authorized to act on Sarah's behalf

### 2. Okta XAA — Identity Assertion Authorization Grant (ID-JAG)
- Agent uses Okta's ID-JAG flow to obtain identity assertions, then exchanges them (with AGNTCY badge as actor proof) for scoped access tokens
- Each target domain (Open-Meteo, Slack) receives a scoped token
- All credentials loaded from AWS Secrets Manager at runtime.

### 3. Cedar Policy Engine (Amazon Verified Permissions)
- Cedar policies define fine-grained TBAC rules per domain
- Amazon Verified Permissions evaluates policies in the cloud
- Entity model: `Agent` → `Action` → `MCPServer` with scoped context
- Policies enforce: badge validity, scope alignment, delegation constraints

## Cedar Policies

Each MCP server domain has its own Cedar policy file:

| File | Domain | Key Rules |
|------|--------|-----------|
| `weather.cedar` | api.open-meteo.com | Read weather data with valid badge + scopes |
| `slack.cedar` | slack.com | Post messages / read channels with valid badge + scopes |
| `schema.cedarschema` | — | Entity types, actions, and context shape |

### Cedar Entity Model

```
namespace XDomainTBAC {
    entity Agent { agent_name, delegating_user, badge_id }
    entity MCPServer { domain, description }

    action "weather.access"  appliesTo { principal: Agent, resource: MCPServer }
    action "slack.access"    appliesTo { principal: Agent, resource: MCPServer }
    action "slack.read"      appliesTo { principal: Agent, resource: MCPServer }
}
```

## Project Structure

```
├── agent/                    # Agent orchestrator
│   ├── openclaw_agent.py     # Main agent logic
│   ├── task_context.py       # Delegation chain tracking
│   └── config.py             # Configuration
├── identity/                 # AGNTCY Identity layer
│   ├── badge_issuer.py       # Badge issuance
│   ├── badge_verifier.py     # Badge verification
│   ├── okta_xaa.py           # Okta XAA token exchange
│   └── secrets.py            # AWS Secrets Manager helpers
├── cedar/                    # Cedar policy engine
│   ├── avp_client.py         # Amazon Verified Permissions client
│   ├── policy_engine.py      # Policy evaluation engine
│   └── policies/             # Cedar policy files
│       ├── weather.cedar
│       ├── slack.cedar
│       └── schema.cedarschema
├── mcp_servers/               # MCP server stubs
│   ├── weather_mcp.py
│   └── slack_mcp.py
├── tests/                    # Test suite
├── docker-compose.yml
├── Dockerfile
├── .env.example
└── requirements.txt
```

## Quick Start

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (optional, for full stack)
- Okta developer account (for XAA ID-JAG token exchange)
- AWS account with Amazon Verified Permissions (for Cedar policy evaluation)
- AGNTCY Identity Service instance

### Local Development

```bash
# Clone and enter the repo
cd xdomain-openclaw-cedar-poc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your credentials

# Run tests
pytest tests/ -v

# Run the agent
python -m agent.openclaw_agent
```

### Docker Compose

```bash
# Copy and configure environment
cp .env.example .env

# Start all services
docker-compose up --build

# Run tests in container
docker-compose run openclaw-agent pytest tests/ -v
```

## Auth Flow

1. **Sarah** delegates a task to the OpenClaw agent
2. **Agent** requests an identity badge from AGNTCY Identity Service
3. For each MCP server (Weather, Slack):
   - **Agent** obtains an Identity Assertion JWT via Okta ID-JAG flow, then exchanges it (with AGNTCY badge as actor proof) for a domain-specific scoped access token
   - **Cedar policy engine** evaluates TBAC authorization via AVP
   - **MCP server** receives the scoped token and executes the tool call
4. **Agent** aggregates results and returns them to Sarah

All credentials loaded from AWS Secrets Manager at runtime.

## Delegation Chain Example

```
Sarah (human)
  └─▶ OpenClaw Agent [badge: badge-openclaw-agent-001]
        ├─▶ Weather MCP [xaa-token: api.open-meteo.com, scopes: weather:read]
        └─▶ Slack MCP [xaa-token: slack.com, scopes: slack:chat:write]
```

## Version A vs Version B

| Aspect | Version A (AGNTCY) | Version B (Cedar) |
|--------|--------------------|--------------------|
| TBAC Engine | IdentityServiceMCPMiddleware | Cedar + Amazon Verified Permissions |
| Policy Format | Programmatic Python checks | Declarative Cedar policies |
| Scope Check | Set-based in middleware | Cedar `context.scopes.contains()` |
| Cloud Service | — | Amazon Verified Permissions |
| Policy Files | — | `.cedar` + `.cedarschema` |

## License

Apache 2.0 — see [LICENSE](LICENSE).
