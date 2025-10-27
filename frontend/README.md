# Frontend

The frontend is a React + TypeScript single-page application that authenticates users, collects tee time preferences, and surfaces notifications from the backend.

## Local Development

```bash
cd frontend
npm install
npm start
```

The dev server runs on http://localhost:3000 and proxies API calls to the FastAPI service (`REACT_APP_API_URL`, default `http://localhost:8000`).

## Scripts

- `npm start` – run the development server with hot reload
- `npm test` – execute unit tests via Jest
- `npm run build` – produce a production build under `build/`

## Linting and Formatting

This project relies on the default Create React App tooling. Add project-specific ESLint or Prettier rules as needed.
