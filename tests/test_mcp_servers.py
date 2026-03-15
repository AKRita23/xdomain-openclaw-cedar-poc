"""Tests for MCP server client stubs."""
import pytest
from agent.config import MCPServerConfig
from mcp_servers.weather_mcp import WeatherMCPClient
from mcp_servers.slack_mcp import SlackMCPClient


@pytest.fixture
def weather_config():
    return MCPServerConfig(name="weather", url="",
                           auth_domain="api.open-meteo.com", scopes=["weather:read"])


@pytest.fixture
def slack_config():
    return MCPServerConfig(name="slack", url="http://localhost:9003",
                           auth_domain="slack.com", scopes=["slack:chat:write"])


@pytest.mark.asyncio
async def test_weather_mcp(weather_config):
    client = WeatherMCPClient(weather_config)
    result = await client.call(token="test-token-placeholder")
    assert result["tool"] == "weather.get_current"
    assert result["result"]["location"] == "Austin, TX"
    assert result["result"]["temperature"] == 72


@pytest.mark.asyncio
async def test_slack_mcp(slack_config):
    client = SlackMCPClient(slack_config)
    result = await client.call(token="test-token-placeholder")
    assert result["tool"] == "slack.chat.postMessage"
