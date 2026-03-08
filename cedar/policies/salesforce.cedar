// Salesforce TBAC Policies for Cross-Domain Agent Access
//
// Allows delegated agents to access Salesforce MCP server
// when they have a valid badge and appropriate scopes.

// Allow agents with valid badges to read Salesforce contacts
permit (
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"salesforce.access",
    resource == XDomainTBAC::MCPServer::"salesforce.com"
) when {
    context.badge_valid == true &&
    context.scopes.contains("contacts.read")
};

// Allow agents to write Salesforce contacts with explicit write scope
permit (
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"salesforce.write",
    resource == XDomainTBAC::MCPServer::"salesforce.com"
) when {
    context.badge_valid == true &&
    context.scopes.contains("contacts.write") &&
    context.delegating_user != ""
};

// Deny all Salesforce access if badge is invalid
forbid (
    principal is XDomainTBAC::Agent,
    action,
    resource == XDomainTBAC::MCPServer::"salesforce.com"
) when {
    context.badge_valid == false
};
