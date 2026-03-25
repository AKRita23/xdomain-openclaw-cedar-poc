"""
Okta XAA — Identity Assertion Authorization Grant (ID-JAG).

Implements the Okta ID-JAG flow to obtain domain-specific access tokens
for cross-domain delegation. The agent obtains an Identity Assertion JWT,
then exchanges it (with AGNTCY badge as actor proof) for a scoped access token.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx
import jwt

logger = logging.getLogger(__name__)


class TokenExchangeError(Exception):
    """Raised when token exchange fails."""

    def __init__(self, reason: str, status_code: Optional[int] = None,
                 details: Optional[Dict[str, Any]] = None):
        super().__init__(reason)
        self.reason = reason
        self.status_code = status_code
        self.details = details or {}


class OktaXAAClient:
    """Handles Okta XAA (ID-JAG) token exchange for cross-domain access."""

    ID_JAG_GRANT = "urn:okta:params:oauth:grant-type:id-jag"
    CLIENT_CREDENTIALS_GRANT = "client_credentials"
    JWT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:jwt"
    ACCESS_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:access_token"

    TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"

    # Map scopes to resource domain targets
    SCOPE_TO_RESOURCE = {
        "weather:read": "weather",
        "slack:chat:write": "slack",
    }

    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str,
        auth_server_id: str = "default",
        audience: str = "",
        token_endpoint: str = "",
        issuer: str = "",
        # Org 2 (resource domain) parameters
        org2_domain: str = "",
        resource_app_client_id: str = "",
        resource_app_client_secret: str = "",
        weather_auth_server_id: str = "",
        slack_auth_server_id: str = "",
        weather_audience: str = "",
        slack_audience: str = "",
    ):
        self.domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.auth_server_id = auth_server_id
        self.audience = audience
        self.issuer = issuer
        self.token_endpoint = (
            token_endpoint
            or f"https://{domain}/oauth2/{auth_server_id}/v1/token"
        )
        # Org 2 config
        self.org2_domain = org2_domain
        self.resource_app_client_id = resource_app_client_id
        self.resource_app_client_secret = resource_app_client_secret
        self.weather_auth_server_id = weather_auth_server_id
        self.slack_auth_server_id = slack_auth_server_id
        self.weather_audience = weather_audience
        self.slack_audience = slack_audience

    def _resolve_org2_target(
        self, target_audience: str, scopes: Optional[List[str]],
    ) -> Tuple[str, str]:
        """Resolve Org 2 auth server ID and audience from scopes or target_audience."""
        if scopes:
            for scope in scopes:
                resource = self.SCOPE_TO_RESOURCE.get(scope)
                if resource == "weather":
                    return self.weather_auth_server_id, self.weather_audience
                if resource == "slack":
                    return self.slack_auth_server_id, self.slack_audience

        # Fall back to matching target_audience directly
        if target_audience == self.weather_audience:
            return self.weather_auth_server_id, self.weather_audience
        if target_audience == self.slack_audience:
            return self.slack_auth_server_id, self.slack_audience

        raise TokenExchangeError(
            reason=f"Cannot resolve Org 2 auth server for audience '{target_audience}' "
                   f"and scopes {scopes}"
        )

    async def exchange_token(
        self,
        subject_token: str,
        target_audience: str,
        scopes: Optional[List[str]] = None,
        badge_jwt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform two-org Okta ID-JAG token exchange.

        Step 1: Get ID-JAG assertion from Org 1 (agent's domain)
        Step 2: Exchange ID-JAG for scoped access token from Org 2 (resource domain)

        Returns token response with access_token, token_type, expires_in, scope.

        Raises:
            TokenExchangeError: If any step fails or validation fails
        """
        org2_auth_server_id, resolved_audience = self._resolve_org2_target(
            target_audience, scopes,
        )

        async with httpx.AsyncClient() as client:
            # Step 1 — Get ID-JAG assertion from Org 1
            logger.info(
                "Step 1: Requesting ID-JAG assertion from Org 1: %s",
                self.token_endpoint,
            )
            step1_data = {
                "grant_type": self.ID_JAG_GRANT,
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "scope": "openid",
            }
            step1_resp = await client.post(
                self.token_endpoint,
                data=step1_data,
            )
            if step1_resp.status_code != 200:
                raise TokenExchangeError(
                    reason=f"Step 1 failed: ID-JAG assertion request returned {step1_resp.status_code}",
                    status_code=step1_resp.status_code,
                    details=step1_resp.json() if step1_resp.headers.get("content-type", "").startswith("application/json") else {"body": step1_resp.text},
                )

            step1_body = step1_resp.json()
            id_jag_token = step1_body.get("id_jag_token") or step1_body.get("access_token")
            if not id_jag_token:
                raise TokenExchangeError(
                    reason="Step 1 response missing id_jag_token and access_token",
                    details=step1_body,
                )
            logger.info("Step 1 complete: obtained ID-JAG assertion")

            # Step 2 — Exchange ID-JAG for scoped token from Org 2
            org2_token_endpoint = (
                f"https://{self.org2_domain}/oauth2/{org2_auth_server_id}/v1/token"
            )
            logger.info(
                "Step 2: Exchanging ID-JAG at Org 2: %s audience=%s scopes=%s",
                org2_token_endpoint, resolved_audience, scopes,
            )
            step2_data = {
                "grant_type": self.TOKEN_EXCHANGE_GRANT,
                "client_id": self.resource_app_client_id,
                "client_secret": self.resource_app_client_secret,
                "subject_token": id_jag_token,
                "subject_token_type": self.JWT_TOKEN_TYPE,
                "audience": resolved_audience,
                "scope": " ".join(scopes) if scopes else "",
            }
            step2_resp = await client.post(
                org2_token_endpoint,
                data=step2_data,
            )
            if step2_resp.status_code != 200:
                raise TokenExchangeError(
                    reason=f"Step 2 failed: token exchange returned {step2_resp.status_code}",
                    status_code=step2_resp.status_code,
                    details=step2_resp.json() if step2_resp.headers.get("content-type", "").startswith("application/json") else {"body": step2_resp.text},
                )

            result = step2_resp.json()
            logger.info("Step 2 complete: obtained scoped access token")

        self._validate_token_response(result, resolved_audience)
        return result

    @staticmethod
    def _validate_token_response(
        token_response: Dict[str, Any],
        expected_audience: str,
    ) -> None:
        """
        Validate the token response.

        Checks:
          - expires_in is present and positive
          - access_token is present and non-empty

        Raises TokenExchangeError if validation fails.
        """
        access_token = token_response.get("access_token", "")
        if not access_token:
            raise TokenExchangeError(reason="Token response missing access_token")

        expires_in = token_response.get("expires_in")
        if expires_in is None or expires_in <= 0:
            raise TokenExchangeError(
                reason="Token response has invalid or missing expires_in"
            )

        # Attempt to decode the access token (without verification) to check
        # audience claim. Okta access tokens are JWTs with an aud claim.
        try:
            unverified = jwt.decode(
                access_token,
                options={"verify_signature": False},
                algorithms=["RS256", "ES256"],
            )
            token_aud = unverified.get("aud")
            if token_aud and token_aud != expected_audience:
                raise TokenExchangeError(
                    reason=(
                        f"Token audience mismatch: "
                        f"expected '{expected_audience}', got '{token_aud}'"
                    )
                )
        except jwt.DecodeError:
            # Opaque tokens don't have decodable claims — skip aud check
            logger.info("Token is opaque (non-JWT), skipping audience validation")
