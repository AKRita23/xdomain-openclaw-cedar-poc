// Google Calendar TBAC Policies for Cross-Domain Agent Access
//
// Allows delegated agents to access Google Calendar MCP server
// when they have a valid badge and appropriate scopes.

// Allow agents with valid badges to read calendar events
permit (
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"gcal.access",
    resource == XDomainTBAC::MCPServer::"googleapis.com"
) when {
    context.badge_valid == true &&
    context.scopes.contains("calendar.events.read")
};

// Allow agents to create/modify calendar events with write scope
permit (
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"gcal.write",
    resource == XDomainTBAC::MCPServer::"googleapis.com"
) when {
    context.badge_valid == true &&
    context.scopes.contains("calendar.events.write") &&
    context.delegating_user != ""
};

// Deny all GCal access if badge is invalid
forbid (
    principal is XDomainTBAC::Agent,
    action,
    resource == XDomainTBAC::MCPServer::"googleapis.com"
) when {
    context.badge_valid == false
};
