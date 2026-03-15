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

    VALID_TASKS = frozenset({
        "weather_slack_notification",
    })

    async def authorize(
        self,
        principal_id: str,
        action: str,
        resource_domain: str,
        scopes: List[str],
        badge: Dict[str, Any],
        delegating_user: str,
        task: str = "",
    ) -> None:
        """
        Evaluate Cedar policy for an MCP tool call.

        Validates all inputs before constructing Cedar context.
        Raises CedarPolicyDenied if the policy denies the action.
        Raises ValueError if required inputs are missing or invalid.

        Cedar entity mapping:
          - Principal: Agent::{principal_id}
          - Action: Action::{action}
          - Resource: MCPServer::{resource_domain}
          - Context: scopes, badge_id, delegating_user, badge_valid, task
        """
        if not principal_id:
            raise ValueError("principal_id is required")
        if not action:
            raise ValueError("action is required")
        if not resource_domain:
            raise ValueError("resource_domain is required")
        if not badge or not badge.get("badge_id"):
            raise ValueError("badge with badge_id is required")
        if not delegating_user:
            raise ValueError("delegating_user is required")
        if not task:
            raise ValueError("task is required for Cedar policy evaluation")
        if task not in self.VALID_TASKS:
            raise ValueError(f"task '{task}' is not in the allowed task list")

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
            "task": task,
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
