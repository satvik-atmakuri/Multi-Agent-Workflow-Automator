# Frontend - Multi-Agent Workflow Automator

A generic chat interface built with **React 19**, **Vite**, and **Tailwind CSS**. It communicates with the FastAPI backend via REST.

## ⚡ Quick Start

1.  **Install**:
    ```bash
    cd frontend
    npm install
    ```

2.  **Dev Server**:
    ```bash
    npm run dev
    ```
    Opens at http://localhost:5173.

3.  **Build**:
    ```bash
    npm run build
    npm run preview
    ```

## 🌍 Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Backend URL | `http://localhost:8000` |

To change this, create a `.env` file in `frontend/`:
```ini
VITE_API_BASE_URL=http://production-api.com
```

## 🔄 Polling & State Logic

The frontend does not use WebSockets. It uses **Smart Polling** to simulate real-time updates:

1.  **Creation**: User sends request -> Backend returns `workflow_id`.
2.  **Polling**: The `StatusDashboard` component calls `GET /api/workflows/{id}` every 2 seconds.
3.  **Updates**:
    -   It checks `status` (`running`, `completed`, `failed`).
    -   It renders the current node (e.g., "Researching...") based on the `last_active_node` field.
4.  **Completion**: When `status === 'completed'`, it stops polling and renders `final_output`.

## 📁 Key Components

-   `Sidebar.tsx`: History management (Delete Logic included).
-   `ChatInterface.tsx`: Main chat bubble rendering.
-   `StatusDashboard.tsx`: Progress bar and agent activity visualizer.
