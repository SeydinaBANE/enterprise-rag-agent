# Enterprise RAG Agent — Frontend

Interface Next.js 16 pour l'agent RAG d'entreprise.

## Prérequis

- Node.js >= 20
- Backend démarré (`make docker-up && make run` dans le dossier parent)

## Démarrage rapide

```bash
cp .env.local.example .env.local
npm install
npm run dev    # http://localhost:3000
```

1. Aller sur `/settings`, renseigner la clé API (valeur de `API_KEY` dans votre `.env` backend)
2. Aller sur `/documents` pour uploader des fichiers ou ingérer des URLs
3. Aller sur `/chat` pour interroger la knowledge base

## Commandes

| Commande | Description |
|---|---|
| `npm run dev` | Serveur de développement (hot reload) |
| `npm run build` | Build de production |
| `npm run lint` | ESLint |
| `npx tsc --noEmit` | Vérification des types |

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL du backend FastAPI |
