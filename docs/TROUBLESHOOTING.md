# Troubleshooting

Common issues and their concrete fixes.

## 🔑 Brave API Key Not Set

**Symptom**: Researcher fails or falls back to "DuckDuckGo (Mock)" constantly. Logs show `Brave not configured`.

**Fix**:
1.  Get a key from [Brave Search API](https://brave.com/search/api/).
2.  Add it to `.env`:
    ```ini
    BRAVE_SEARCH_API_KEY=BSPA-xxxxxxxxxxxxxxxxxxxx
    ```
3.  **Important**: Restart Docker to pick up the change.
    ```bash
    docker-compose down && docker-compose up --build
    ```

## 🚫 CORS Blocked

**Symptom**: Frontend shows "Network Error" or console says `Access to XMLHttpRequest... has been blocked by CORS policy`.

**Fix**:
Ensure your `backend/app/main.py` has the correct `allow_origins`.
By default, it allows `http://localhost:5173`.
If you are running the frontend on a different port (e.g., 3000), update `.env` or `main.py`:

```python
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]
```

## 🐘 Postgres Connection Failures

**Symptom**: Backend startup logs show `Connection refused` to port 5432.

**Fix**:
1.  Check if a local Postgres instance is already running on port 5432. It might conflict with Docker.
    -   **Windows**: `Get-Process postgres`
    -   **Linux/Mac**: `sudo lsof -i :5432`
2.  **Solution**: Stop local Postgres OR change the Docker port mapping in `docker-compose.yml`:
    ```yaml
    ports:
      - "5433:5432" # Map host 5433 to container 5432
    ```
    Then update `.env` to use port 5433.

## 🛑 Rate Limits (Brave/OpenAI)

**Symptom**: 429 Errors in logs.

**Fix**:
-   **Brave**: Free tier is 1 request/sec. The `Researcher` agent has a built-in linear retry, but heavy load will hit limits. Upgrade to paid tier if needed.
-   **OpenAI**: Check your usage dashboard.

## 🔄 "Workflow Ran Twice"

**Symptom**: You see two responses in the chat for one request.

**Explanation**: React 18+ in Strict Mode (development only) renders components twice to detect side effects.
**Fix**: This only happens in `npm run dev`. It will not occur in the production build (`npm run build`). You can disable Strict Mode in `main.tsx` if it's annoying, but it's not recommended for debugging.
