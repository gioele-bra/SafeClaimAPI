def issue_token(username: str, role: str = "user") -> str:
    # TODO: sostituire con JWT vero o integrazione Keycloak
    return f"demo-token-for:{username}:role:{role}"

def revoke_token(token: str) -> bool:
    """
    Invalida un token esistente.
    Attualmente è un mock. In futuro, aggiungerà il JWT a una blacklist (es. Redis)
    o eliminerà il token dal database (se stateful).
    """
    # TODO: Implementare la logica reale di revoca quando si passerà a JWT/Database
    print(f"Mock: Token {token} invalidato con successo.")
    return True