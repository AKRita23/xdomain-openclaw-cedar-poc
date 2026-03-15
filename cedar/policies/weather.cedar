// Allow weather read access with valid badge and task context
permit(
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"weather.access",
    resource is XDomainTBAC::MCPServer
) when {
    context.badge_valid == true &&
    context.scopes.contains("weather:read") &&
    context.task == "weather_slack_notification"
};

// Deny all weather access if badge is invalid
forbid(
    principal is XDomainTBAC::Agent,
    action == XDomainTBAC::Action::"weather.access",
    resource is XDomainTBAC::MCPServer
) when {
    context.badge_valid == false
};
