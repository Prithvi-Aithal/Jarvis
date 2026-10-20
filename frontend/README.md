# Jarvis: frontend

The Jarvis dashboard: React 19 and TypeScript, built with Vite, Tailwind CSS v4, Recharts and Framer Motion.

```bash
npm install
npm run dev      # start the dev server (Vite prints the local URL)
npm run build    # type-check and build to dist/
npm run lint
```

In development, Vite proxies `/api` requests to the Flask backend on port 5000. To point the dashboard at a different API, set `VITE_API_URL` in `frontend/.env`.

See the [main README](../README.md) for the full setup, including the backend and the activity trackers.
