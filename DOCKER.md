# Docker & Docker Compose Guide

This project runs as **two containers**: one for the FastAPI backend and one for the
Streamlit frontend. Docker Compose starts them together, and the GitHub Actions pipeline
builds them, pushes them to Amazon ECR, and runs them on EC2.

---

## 1. Why two containers instead of one?

The rule of thumb in Docker is **one process per container**.

| One container (both apps) | Two containers (this setup) |
|---|---|
| If the backend crashes, Docker doesn't notice (it only watches the main process) | Each container is watched separately and restarted on its own |
| A frontend change rebuilds and redeploys everything | Each image is rebuilt only from its own files |
| One big image with every dependency | Frontend image only has Streamlit + requests |
| Logs from both apps are mixed together | `docker compose logs backend` / `frontend` show them separately |

---

## 2. The files

```
Enterprise-Knowledge-Assistant/
├── backend/
│   └── Dockerfile          # builds the API image
├── frontend/
│   ├── Dockerfile          # builds the UI image
│   └── requirements.txt    # UI-only dependencies (streamlit, requests)
├── requirements.txt        # backend dependencies
├── docker-compose.yml      # runs both containers together
├── .dockerignore           # keeps .env, venv, .git out of the backend image
└── .github/workflows/aws.yaml   # CI/CD pipeline
```

---

## 3. How each container is built

### Backend — `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Line by line:

1. **`FROM python:3.11-slim`**: starts from a small Linux image that already has Python 3.11.
2. **`WORKDIR /app`**: all later commands run inside `/app` in the container.
3. **`COPY requirements.txt` then `RUN pip install`**: installs the dependencies *before*
   copying the code. Docker caches each step (a "layer"). If you only change Python code,
   Docker reuses the cached install layer and the rebuild takes seconds, not minutes.
4. **`COPY backend/ ./backend/`**: copies the code, the documents and the FAISS index
   (`backend/data/`).
5. **`CMD uvicorn ... --host 0.0.0.0`**: the command the container runs. `0.0.0.0` is
   required. With `127.0.0.1`, the API would only be reachable from inside its own container.

**Why is the build context the project root, not `backend/`?**
The code uses imports like `from backend.rag...`, so the container needs a `backend/`
folder inside `/app`. It also needs the root `requirements.txt`. A Dockerfile can only
`COPY` files that are inside its build context, so the context has to be the root.

### Frontend — `frontend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]
```

The steps are the same, except the build context is just `frontend/`, because the UI
needs nothing else. `--server.headless=true` stops Streamlit from asking for an email
address on first start, which would hang a container.

### How does the frontend find the backend?

`frontend/app.py` reads the backend address from an environment variable:

```python
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
```

- **Running locally without Docker:** the variable isn't set, so it uses `localhost:8000` (unchanged behaviour).
- **Running in Compose:** it is set to `http://backend:8000` (explained below).

`localhost` does **not** work between containers. Inside the frontend container,
`localhost` means *the frontend container itself*, and nothing is listening on port 8000 there.

---

## 4. How Docker Compose uses the two Dockerfiles

`docker-compose.yml` describes both containers in one file:

```yaml
services:
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    image: ${BACKEND_IMAGE:-eka-backend:latest}
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "8000:8000"
    healthcheck: ...
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
    image: ${FRONTEND_IMAGE:-eka-frontend:latest}
    environment:
      BACKEND_URL: http://backend:8000
    ports:
      - "8501:8501"
    depends_on:
      backend:
        condition: service_healthy
    restart: unless-stopped
```

What each key does:

| Key | Meaning |
|---|---|
| `services:` | Each entry becomes one container. |
| `build:` | Which folder (`context`) and `Dockerfile` to build the image from. |
| `image:` | The image's name. `${BACKEND_IMAGE:-eka-backend:latest}` uses the `BACKEND_IMAGE` variable if it is set (the pipeline sets it to the ECR address), otherwise the local name `eka-backend:latest`. |
| `environment:` | Environment variables inside the container. `${OPENAI_API_KEY}` is read from your shell or a `.env` file next to `docker-compose.yml`. |
| `ports: "8501:8501"` | `HOST:CONTAINER`. Opens container port 8501 on the machine's port 8501. |
| `healthcheck:` | Every 10s, Docker calls `/api/health` inside the backend. The container is marked *healthy* once it answers. |
| `depends_on ... service_healthy` | The frontend doesn't start until the backend is healthy. |
| `restart: unless-stopped` | If a container crashes, or the EC2 instance reboots, Docker starts it again. |

### The Compose network (why `http://backend:8000` works)

When Compose starts, it creates a private network and attaches both containers to it.
On that network, **each service name is also a hostname**:

```
          your browser
               │
      http://<host>:8501
               │
┌──────────────┼───────── Docker host (your Mac / EC2) ───────────────┐
│              ▼                                                      │
│   ┌─────────────────────┐   http://backend:8000   ┌──────────────┐  │
│   │ frontend container  │ ──────────────────────▶ │  backend     │  │
│   │ Streamlit :8501     │                         │  FastAPI     │  │
│   └─────────────────────┘                         │  :8000       │──┼──▶ OpenAI API
│                                                   └──────────────┘  │
│              Compose network  (eka_default)                         │
└─────────────────────────────────────────────────────────────────────┘
```

The browser only talks to the frontend. The frontend calls the backend over the
internal network, so port 8000 doesn't need to be public. It's published only so you
can open `/docs`.

---

## 5. Running it locally

Start Docker Desktop, then from the project root:

```bash
export OPENAI_API_KEY=sk-...        # or put OPENAI_API_KEY=sk-... in a .env file in the project root
docker compose up --build           # builds both images, then starts backend → (healthy) → frontend
```

- Chat UI: http://localhost:8501
- API docs: http://localhost:8000/docs

Useful commands:

```bash
docker compose ps                   # status of both containers (look for "healthy")
docker compose logs -f backend      # follow backend logs
docker compose up -d --build frontend   # rebuild and restart only the frontend
docker compose down                 # stop and remove both containers
```

> The backend image does **not** include `backend/.env`, because `.dockerignore` excludes it.
> Otherwise your OpenAI key would be stored inside an image pushed to ECR.
> The key is always passed in at runtime through `environment:`.

---

## 6. How the CI/CD pipeline uses Compose

`.github/workflows/aws.yaml` runs on every push to `main`:

```
git push ──▶ Job 1: Continuous-Integration (GitHub's ubuntu runner)
               ├─ checkout code
               ├─ log in to ECR
               ├─ docker compose build   → builds both images, named with the ECR address
               └─ docker compose push    → uploads both images to ECR
                        │
                        ▼
             Job 2: Continuous-Deployment (self-hosted runner ON the EC2 instance)
               ├─ checkout code          → puts docker-compose.yml on EC2
               ├─ log in to ECR
               ├─ docker compose pull    → downloads the new images
               ├─ docker compose up -d --no-build
               │                          → replaces only the containers whose image changed
               └─ docker image prune -f  → deletes old images so the disk doesn't fill up
```

The same `docker-compose.yml` is used in both jobs. The only difference is the
`BACKEND_IMAGE` / `FRONTEND_IMAGE` variables, which make `image:` point at ECR, e.g.
`123456789012.dkr.ecr.ap-south-1.amazonaws.com/eka-backend:latest`.
`--no-build` makes sure EC2 never tries to build: it only runs what CI pushed.

### One-time setup

**AWS**
1. Create two ECR repositories, e.g. `eka-backend` and `eka-frontend`.
2. Launch a Linux EC2 instance. In its security group, allow inbound **8501** (UI),
   **22** (SSH), and optionally **8000** (API docs).
3. On the instance, install Docker and the Compose plugin:
   ```bash
   # Ubuntu
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER && newgrp docker
   docker compose version
   ```
   (On Amazon Linux 2023, `docker` is installed with `dnf`, but the Compose plugin has
   to be downloaded separately from the docker/compose GitHub releases.)

**GitHub → Settings → Actions → Runners → New self-hosted runner → Linux**
Run the commands it shows on the EC2 instance, then run `sudo ./svc.sh install && sudo ./svc.sh start`
so the runner stays up after you log out. The runner connects *out* to GitHub, so you
don't need to set up a webhook.

**GitHub → Settings → Secrets and variables → Actions**

| Secret | Example |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user key with ECR push/pull permissions |
| `AWS_SECRET_ACCESS_KEY` | |
| `AWS_DEFAULT_REGION` | `ap-south-1` |
| `ECR_REPO_BACKEND` | `eka-backend` |
| `ECR_REPO_FRONTEND` | `eka-frontend` |
| `OPENAI_API_KEY` | `sk-...` |

Then push to `main` and open `http://<ec2-public-ip>:8501`.

---

## 7. Things to know

- **Uploaded documents are not permanent.** Files added through `/api/ingest` are written
  inside the backend container. The next deploy replaces the container, and those files
  are lost. To keep them, add documents to `backend/data/sample_docs/` in git, or mount a
  volume for `backend/data`.
- **Tag `latest` only.** Every deploy overwrites `latest`, so you can't roll back to an
  older version. A common improvement is to also tag each image with the git commit SHA.
- **Other settings.** `OPENAI_MODEL`, `RETRIEVAL_TOP_K`, etc. can be added under the
  backend's `environment:` in the same way as `OPENAI_API_KEY`.
