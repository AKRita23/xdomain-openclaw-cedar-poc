"""
Cedar Policy Engine for TBAC enforcement.

Evaluates Cedar policies either locally or via Amazon Verified Permissions
to enforce Task-Based Access Control on MCP tool calls.
"""
import logging
from typing import Any, Dict, List, Optional

from cedar.avp_client import AVPClient

logger = logging.getLogger(__name__)


class CedarPolicyDenied(Exception):
    """Raised when a Cedar policy denies an action."""

    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(reason)
        self.reason = reason
        self.details = details or {}


class CedarPolicyEngine:
    """
    Cedar-based TBAC enforcement engine.

    Translates MCP tool call context into Cedar authorization requests
    and evaluates them against the policy store.
    """

    def __init__(self, policy_store_id: str, aws_region: str = "us-east-1"):
        self.avp_client = AVPClient(
            policy_store_id=policy_store_id,
            aws_region=aws_region,
        )

    async def authorize(
        self,
        principal_id: str,
        action: str,
        resource_domain: str,
        scopes: List[str],
        badge: Dict[str, Any],
        delegating_user: str,
    ) -> None:
        """
        Evaluate Cedar policy for an MCP tool call.

        Raises CedarPolicyDenied if the policy denies the action.

        Cedar entity mapping:
          - Principal: Agent::{principal_id}
          - Action: Action::{action}
          - Resource: MCPServer::{resource_domain}
          - Context: scopes, badge_id, delegating_user, badge_valid
        """
        principal = {
            "entityType": "XDomainTBAC::Agent",
            "entityId": principal_id,
        }
        action_entity = {
            "actionType": "XDomainTBAC::Action",
            "actionId": action,
        }
        resource = {
            "entityType": "XDomainTBAC::MCPServer",
            "entityId": resource_domain,
        }
        context = {
            "scopes": scopes,
            "badge_id": badge.get("badge_id", ""),
            "delegating_user": delegating_user,
            "badge_valid": bool(badge.get("jwt")),
        }

        result = await self.avp_client.is_authorized(
            principal=principal,
            action=action_entity,
            resource=resource,
            context=context,
        )

        if not result.is_allowed:
            raise CedarPolicyDenied(
                reason=f"Cedar policy denied: {action} on {resource_domain}",
                details={
                    "principal": principal_id,
                    "action": action,
                    "resource": resource_domain,
                    "scopes": scopes,
                    "reasons": result.reasons,
                    "errors": result.errors,
                },
            )

        logger.info(
            "Cedar ALLOW: principal=%s action=%s resource=%s scopes=%s",
            principal_id, action, resource_domain, scopes,
        )
