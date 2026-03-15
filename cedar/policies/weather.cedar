// Allow weather read access with valid badge
permit(
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"weather.access",
    resource is XDomainTBAC::MCPServer
) when {
    context.badge_valid == true &&
    context.scopes.contains("weather:read")
};

// Deny all weather access if badge is invalid
forbid(
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"weather.access",
    resource is XDomainTBAC::MCPServer
) when {
    context.badge_valid == false
};
