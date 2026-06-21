# YFIC API

Backend FastAPI pour la boutique YFIC (PostgreSQL via Neon).

## Démarrage

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
python -m app.seed       # crée les tables + insère les produits
uvicorn app.main:app --reload --port 8000
```

L'API tourne sur `http://localhost:8000`, docs interactives sur `/docs`.

## Endpoints

- `GET /api/products` — liste (filtres `category`, `featured`)
- `GET /api/products/{slug}` — détail produit
- `GET /api/products/{slug}/related` — produits liés
- `GET /api/categories` — catégories avec compteur
- `POST /api/contact` — message de contact
- `POST /api/newsletter` — inscription newsletter
- `POST /api/orders` — création de commande

## Frontend

Le frontend Next.js (`Frontend/yfic`) consomme cette API via `NEXT_PUBLIC_API_URL`
(voir `.env.local`).

## Performance / montée en charge

- Cache en mémoire (TTL 60s) sur `/api/products` et `/api/categories` : ces données
  changent rarement, donc une rafale de requêtes concurrentes ne déclenche qu'une
  seule requête DB.
- En-têtes `Cache-Control` sur les routes publiques en lecture pour permettre au
  navigateur/CDN de réutiliser les réponses.
- Compression GZip activée sur toutes les réponses.
- Pool de connexions DB dimensionné (`pool_size=20`, `max_overflow=20`) pour absorber
  les pics de concurrence ; ajuster selon le plan Neon.

**En production**, pour tenir une charge de plusieurs milliers d'utilisateurs simultanés :
- Lancer avec plusieurs workers : `gunicorn -k uvicorn.workers.UvicornWorker -w 4 app.main:app`
  (ou plusieurs instances derrière un load balancer).
- Mettre l'API derrière un reverse proxy / CDN (Cloudflare, etc.) qui respecte les
  en-têtes `Cache-Control` ci-dessus pour servir le trafic répété sans toucher le backend.
- Si la charge dépasse largement le cache en mémoire (plusieurs instances), remplacer
  le cache process-local par Redis pour qu'il soit partagé entre workers/instances.
