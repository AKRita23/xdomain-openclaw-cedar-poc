// Slack TBAC Policies for Cross-Domain Agent Access
//
// Allows delegated agents to access Slack MCP server
// when they have a valid badge and appropriate scopes.

// Allow agents with valid badges to post messages
permit (
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"slack.access",
    resource == XDomainTBAC::MCPServer::"slack.com"
) when {
    context.badge_valid == true &&
    context.scopes.contains("chat.write")
};

// Allow agents to read Slack channels
permit (
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"slack.read",
    resource == XDomainTBAC::MCPServer::"slack.com"
) when {
    context.badge_valid == true &&
    context.scopes.contains("channels.read")
};

// Deny all Slack access if badge is invalid
forbid (
    principal is XDomainTBAC::Agent,
    action,
    resource == XDomainTBAC::MCPServer::"slack.com"
) when {
    context.badge_valid == false
};
