from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def client_ip(request: Request) -> str:
    """Clé de rate limiting : IP réelle du client.

    Derrière Vercel, request.client.host est l'IP du proxy — tous les visiteurs
    partageraient la même limite. Vercel écrit x-forwarded-for à l'edge (une
    valeur spoofée par le client y est écrasée), donc le premier élément est
    fiable dans ce déploiement. Sans proxy, on retombe sur l'IP de connexion.
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=client_ip)
