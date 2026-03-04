def issue_token(username: str, role: str = "user") -> str:
    # TODO: sostituire con JWT vero o integrazione Keycloak
    return f"demo-token-for:{username}:role:{role}"