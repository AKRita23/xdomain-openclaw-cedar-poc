"""
Okta XAA — Identity Assertion Authorization Grant (ID-JAG).

Implements the Okta ID-JAG flow to obtain domain-specific access tokens
for cross-domain delegation. The agent obtains an Identity Assertion JWT,
then exchanges it (with AGNTCY badge as actor proof) for a scoped access token.
"""
import logging
from typing import Any, Dict, List, Optional

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

    def __init__(
        self,
        domain: str,
        client_id: str,
        client_secret: str,
        auth_server_id: str = "default",
        audience: str = "",
        token_endpoint: str = "",
        issuer: str = "",
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

    async def exchange_token(
        self,
        subject_token: str,
        target_audience: str,
        scopes: Optional[List[str]] = None,
        badge_jwt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Perform Okta ID-JAG token exchange.

        1. Request Identity Assertion JWT via client_credentials
        2. Exchange ID-JAG + badge JWT for scoped access token

        Returns token response with access_token, token_type, expires_in, scope.

        Raises:
            TokenExchangeError: If token exchange fails or validation fails
        """
        # TODO: Replace with real HTTP calls to Okta
        logger.info(
            "ID-JAG exchange: endpoint=%s audience=%s scopes=%s",
            self.token_endpoint, target_audience, scopes,
        )
        result = {
            "access_token": f"id-jag-placeholder-{target_audience}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "scope": " ".join(scopes) if scopes else "",
        }
        self._validate_token_response(result, target_audience)
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
