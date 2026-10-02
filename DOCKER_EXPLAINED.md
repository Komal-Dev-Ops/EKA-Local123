# Docker Setup Explained — English + मराठी

This file explains `DOCKER.md` and the Docker files in this project, section by section. Each point is in English first, then in Marathi.

ही फाईल `DOCKER.md` आणि project मधल्या Docker files भाग-भाग करून समजावते. प्रत्येक मुद्दा आधी English मध्ये, मग मराठीत.

> Related: the CI/CD pipeline is explained line by line in `AWS_YAML_EXPLAINED.md`.
> संबंधित: CI/CD pipeline ओळ-न्-ओळ `AWS_YAML_EXPLAINED.md` मध्ये समजावली आहे.

---

## 0. Why does Docker exist here? / इथे Docker का आहे?

**EN:**
Your app works on your Mac because Python 3.11, FastAPI, LangChain, FAISS and your `venv` are all installed there. The EC2 server has none of that. Without Docker you would install everything by hand on EC2, and one wrong version would give you "it works on my machine but not on the server".

Docker packs **the app + Python + all libraries** into one sealed box that runs the same way everywhere.

Two words to know:
- **Image** = the packed box (a recipe that is already cooked and frozen). It is built once and can be copied anywhere.
- **Container** = a running copy of an image (the box opened and in use). You can start, stop and delete it.

Analogy: an image is like a **tiffin that is packed and sealed**, and a container is that tiffin **opened and being eaten**. You can pack one tiffin recipe and open it in any office (Mac, EC2).

**MR:**
तुमचं app तुमच्या Mac वर चालतं कारण तिथे Python 3.11, FastAPI, LangChain, FAISS आणि `venv` install आहेत. EC2 server वर यातलं काहीच नाही. Docker शिवाय EC2 वर सगळं हाताने install करावं लागेल, आणि एक जरी version चुकली तर "माझ्या machine वर चालतं, server वर नाही" असा प्रॉब्लेम येतो.

Docker **app + Python + सगळ्या libraries** एका बंद डब्यात पॅक करतं. तो डबा सगळीकडे सारखाच चालतो.

दोन शब्द लक्षात ठेवा:
- **Image** = पॅक केलेला डबा (आधीच बनवून ठेवलेली रेसिपी). एकदा build होते आणि कुठेही copy करता येते.
- **Container** = image ची चालू असलेली copy (उघडून वापरात असलेला डबा). तो start, stop आणि delete करता येतो.

उदाहरण: image म्हणजे **पॅक करून सील केलेला डबा**, आणि container म्हणजे तोच डबा **उघडून जेवण चालू आहे**. एकच डबा कोणत्याही ऑफिसमध्ये (Mac, EC2) उघडता येतो.

---

## 1. Why two containers instead of one? / एक ऐवजी दोन containers का?

**EN:**
The Docker rule of thumb is **one process per container**. This project has two processes: the FastAPI backend (the brain) and the Streamlit frontend (the face).

| One container (both apps) | Two containers (this setup) |
|---|---|
| If the backend crashes, Docker doesn't notice (it only watches the main process) | Each container is watched separately and restarted on its own |
| A frontend change rebuilds everything | Each image is rebuilt only from its own files |
| One big image with every library | The frontend image only has Streamlit + requests |
| Logs from both apps are mixed | `docker compose logs backend` / `frontend` show them separately |

**MR:**
Docker चा साधा नियम: **एका container मध्ये एकच process**. या project मध्ये दोन processes आहेत: FastAPI backend (मेंदू) आणि Streamlit frontend (चेहरा).

| एकच container (दोन्ही apps) | दोन containers (हा setup) |
|---|---|
| Backend crash झाला तरी Docker ला कळत नाही (तो फक्त main process वर लक्ष ठेवतो) | प्रत्येक container वर वेगळं लक्ष, आणि तो स्वतंत्रपणे restart होतो |
| Frontend मधल्या छोट्या बदलासाठी सगळं पुन्हा build | प्रत्येक image फक्त तिच्या files बदलल्यावर build होते |
| सगळ्या libraries असलेली एक मोठी image | Frontend image मध्ये फक्त Streamlit + requests |
| दोन्ही apps चे logs एकत्र मिसळतात | `docker compose logs backend` / `frontend` वेगवेगळे logs दाखवतात |

Analogy / उदाहरण: in a restaurant, the cook and the waiter are separate people. If the cook is sick, you replace only the cook. / हॉटेलमध्ये आचारी आणि वेटर वेगळे असतात. आचारी आजारी पडला तर फक्त आचारी बदलायचा, संपूर्ण हॉटेल नाही.

---

## 2. The files / Files ची ओळख

```
Enterprise-Knowledge-Assistant/
├── backend/
│   └── Dockerfile          # builds the API image / API ची image बनवते
├── frontend/
│   ├── Dockerfile          # builds the UI image / UI ची image बनवते
│   └── requirements.txt    # UI-only libraries / फक्त UI च्या libraries
├── requirements.txt        # backend libraries / backend च्या libraries
├── docker-compose.yml      # runs both containers together / दोन्ही containers एकत्र चालवते
├── .dockerignore           # keeps .env, venv, .git out of the image / .env, venv, .git image बाहेर ठेवते
└── .github/workflows/aws.yaml   # CI/CD pipeline
```

- **Dockerfile** = the recipe for **one** image. / **एका** image ची रेसिपी.
- **docker-compose.yml** = the manager that runs **many** containers together. / **अनेक** containers एकत्र चालवणारा manager.
- **.dockerignore** = the "do not pack" list, like `.gitignore` but for Docker. / "पॅक करू नका" यादी, `.gitignore` सारखीच पण Docker साठी.

---

## 3. How each container is built / प्रत्येक container कसा बनतो

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

**Line by line / ओळ-न्-ओळ:**

1. **`FROM python:3.11-slim`**
   - **EN:** Start from a small Linux image that already has Python 3.11. You don't install Python yourself. `slim` = a smaller size.
   - **MR:** Python 3.11 आधीच असलेल्या छोट्या Linux image पासून सुरुवात. Python स्वतः install करावा लागत नाही. `slim` = कमी size.

2. **`WORKDIR /app`**
   - **EN:** Creates the `/app` folder inside the container and "cd"s into it. All later commands run there.
   - **MR:** Container मध्ये `/app` folder बनवतो आणि त्यात "cd" करतो. पुढच्या सगळ्या commands तिथेच चालतात.

3. **`COPY requirements.txt .` then `RUN pip install ...`**
   - **EN:** Installs libraries **before** copying the code. Docker saves each step as a **layer** (cache). If you change only Python code, Docker reuses the saved install layer, so a rebuild takes seconds instead of minutes. `--no-cache-dir` keeps pip's download cache out of the image so the image is smaller.
   - **MR:** Code copy करण्याच्या **आधी** libraries install करतो. Docker प्रत्येक step एक **layer** (cache) म्हणून साठवतो. फक्त Python code बदलला तर Docker साठवलेला install layer पुन्हा वापरतो, त्यामुळे rebuild मिनिटांऐवजी सेकंदात होतं. `--no-cache-dir` मुळे pip चा download cache image मध्ये जात नाही, म्हणून image लहान राहते.

4. **`COPY backend/ ./backend/`**
   - **EN:** Copies the code, the policy documents and the FAISS index (`backend/data/`) into the image.
   - **MR:** Code, policy documents आणि FAISS index (`backend/data/`) image मध्ये copy करतो.

5. **`EXPOSE 8000`**
   - **EN:** A note saying "this app listens on port 8000". It is documentation only. The real port opening happens in `docker-compose.yml` under `ports:`.
   - **MR:** "हे app port 8000 वर ऐकतं" अशी नोंद. हे फक्त माहितीसाठी आहे. खरं port उघडणं `docker-compose.yml` मधल्या `ports:` मध्ये होतं.

6. **`CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", ...]`**
   - **EN:** The command the container runs when it starts. `uvicorn` is the server that runs FastAPI. `0.0.0.0` means "accept connections from anywhere". With `127.0.0.1`, the API would only answer from inside its own container, and the frontend could not reach it.
   - **MR:** Container सुरू झाल्यावर चालणारी command. `uvicorn` हा FastAPI चालवणारा server आहे. `0.0.0.0` म्हणजे "कुठूनही आलेलं connection स्वीकारा". `127.0.0.1` ठेवलं तर API फक्त स्वतःच्या container च्या आतूनच उत्तर देईल, आणि frontend पोहोचू शकणार नाही.

**Why is the build context the project root, not `backend/`? / Build context project root का, `backend/` का नाही?**

- **EN:** The **build context** is the folder Docker is allowed to see while building. The code imports `from backend.rag...`, so the container needs a `backend/` folder inside `/app`. It also needs the root `requirements.txt`. A Dockerfile can only `COPY` files inside its context, so the context must be the root.
- **MR:** **Build context** म्हणजे build करताना Docker ला दिसू शकणारा folder. Code मध्ये `from backend.rag...` असे imports आहेत, म्हणून container मध्ये `/app` च्या आत `backend/` folder लागतो. Root मधली `requirements.txt` सुद्धा लागते. Dockerfile फक्त context च्या आतल्या files `COPY` करू शकते, म्हणून context root असायला हवा.

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

- **EN:** Same steps as the backend. Here the context is only `frontend/`, because the UI needs nothing else. It uses its own small `requirements.txt` (Streamlit + requests), so the image is much lighter. `--server.headless=true` stops Streamlit from asking for an email on first start. That question would make the container hang forever, because nobody is there to type an answer.
- **MR:** Backend सारख्याच steps. इथे context फक्त `frontend/` आहे, कारण UI ला दुसरं काही लागत नाही. त्याची स्वतःची छोटी `requirements.txt` (Streamlit + requests) आहे, म्हणून image खूप हलकी आहे. `--server.headless=true` मुळे Streamlit पहिल्या वेळी email विचारत नाही. तो प्रश्न विचारला तर container कायमचा अडकेल, कारण उत्तर type करायला तिथे कोणीच नसतं.

### How does the frontend find the backend? / Frontend ला backend कसा सापडतो?

```python
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
```

- **EN:** `frontend/app.py` reads the backend address from an environment variable.
  - **Without Docker:** the variable isn't set, so it uses `localhost:8000`.
  - **In Compose:** it is set to `http://backend:8000`.
  - `localhost` does **not** work between containers. Inside the frontend container, `localhost` means *the frontend container itself*, and nothing listens on port 8000 there.
- **MR:** `frontend/app.py` backend चा पत्ता environment variable मधून वाचतो.
  - **Docker शिवाय:** variable set नसतो, म्हणून `localhost:8000` वापरतो.
  - **Compose मध्ये:** तो `http://backend:8000` असा set होतो.
  - Containers मध्ये आपापसात `localhost` **चालत नाही**. Frontend container च्या आत `localhost` म्हणजे *frontend container स्वतः*, आणि तिथे port 8000 वर कोणीच ऐकत नाही.

Analogy / उदाहरण: two flats in one building. Saying "my home" (`localhost`) from flat A means flat A, not flat B. To visit B you must say "flat B" (`backend`). / एका इमारतीतले दोन फ्लॅट. फ्लॅट A मधून "माझं घर" (`localhost`) म्हटलं तर ते A च असतं, B नाही. B कडे जायचं तर "फ्लॅट B" (`backend`) म्हणावं लागतं.

---

## 4. How Docker Compose uses the two Dockerfiles / Docker Compose दोन Dockerfiles कसे वापरतो

**EN:** Without Compose you would type long `docker build` and `docker run` commands for each container, in the right order, with the right network. `docker-compose.yml` writes all of that down once, and `docker compose up` does it for you.

**MR:** Compose शिवाय प्रत्येक container साठी लांबलचक `docker build` आणि `docker run` commands योग्य क्रमाने आणि योग्य network सह type कराव्या लागतील. `docker-compose.yml` हे सगळं एकदाच लिहून ठेवतं, आणि `docker compose up` ते तुमच्यासाठी करतं.

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

| Key | English | मराठी |
|---|---|---|
| `services:` | Each entry becomes one container. | प्रत्येक entry चा एक container बनतो. |
| `build:` | Which folder (`context`) and `Dockerfile` to build from. | कोणत्या folder (`context`) आणि `Dockerfile` मधून build करायचं. |
| `image:` | The image name. `${BACKEND_IMAGE:-eka-backend:latest}` uses `BACKEND_IMAGE` if it is set (the pipeline sets it to the ECR address), otherwise the local name. | Image चं नाव. `BACKEND_IMAGE` set असेल तर ते (pipeline ते ECR पत्त्यावर set करते), नाहीतर local नाव. |
| `environment:` | Environment variables inside the container. `${OPENAI_API_KEY}` comes from your shell or a `.env` file next to `docker-compose.yml`. | Container मधले environment variables. `${OPENAI_API_KEY}` तुमच्या shell मधून किंवा `docker-compose.yml` शेजारच्या `.env` मधून येतो. |
| `ports: "8501:8501"` | `HOST:CONTAINER`. Connects the machine's port 8501 to the container's port 8501. | `HOST:CONTAINER`. Machine चा port 8501 container च्या port 8501 ला जोडतो. |
| `healthcheck:` | Every 10s Docker calls `/api/health` inside the backend. Once it answers, the backend is marked *healthy*. | दर 10 सेकंदांनी Docker backend मध्ये `/api/health` ला call करतो. उत्तर आलं की backend *healthy* मानला जातो. |
| `depends_on ... service_healthy` | The frontend waits until the backend is healthy. | Backend healthy होईपर्यंत frontend थांबतो. |
| `restart: unless-stopped` | If a container crashes or EC2 reboots, Docker starts it again, unless you stopped it yourself. | Container crash झाला किंवा EC2 reboot झाला तर Docker तो पुन्हा सुरू करतो, तुम्ही स्वतः बंद केला असेल तरच नाही. |

**Why the healthcheck matters / Healthcheck का महत्त्वाचा:**
- **EN:** At startup the backend loads the documents and the FAISS index, which takes some seconds. Without the healthcheck, the UI would start first and show "backend not reachable".
- **MR:** सुरू होताना backend documents आणि FAISS index load करतो, त्याला काही सेकंद लागतात. Healthcheck नसेल तर UI आधी सुरू होईल आणि "backend not reachable" दाखवेल.

### The Compose network / Compose network (`http://backend:8000` का चालतं)

```
          your browser / तुमचा browser
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

- **EN:** When Compose starts, it creates a private network and connects both containers to it. On that network **each service name is also a hostname**, like a phone contact name. The browser talks only to the frontend. The frontend talks to the backend inside the private network, so port 8000 doesn't need to be public. It is published only so you can open `/docs`.
- **MR:** Compose सुरू झाल्यावर एक खाजगी network बनवतो आणि दोन्ही containers त्याला जोडतो. त्या network वर **प्रत्येक service चं नाव हेच hostname असतं**, जसं phone मधलं contact नाव. Browser फक्त frontend शी बोलतो. Frontend खाजगी network मधून backend शी बोलतो, म्हणून port 8000 public असण्याची गरज नाही. तो फक्त `/docs` उघडण्यासाठी publish केला आहे.

---

## 5. Running it locally / Local वर चालवणे

```bash
export OPENAI_API_KEY=sk-...        # or put it in a .env file in the project root / किंवा project root मधल्या .env मध्ये टाका
docker compose up --build           # builds both images, then starts backend → (healthy) → frontend
```

- **EN:** First start **Docker Desktop** on your Mac. Then run the commands above from the project root. `--build` rebuilds the images with your latest code.
- **MR:** आधी Mac वर **Docker Desktop** सुरू करा. मग project root मधून वरच्या commands चालवा. `--build` तुमच्या नवीन code सह images पुन्हा बनवतो.

Open / उघडा:
- Chat UI: http://localhost:8501
- API docs: http://localhost:8000/docs

**Useful commands / उपयोगी commands:**

| Command | English | मराठी |
|---|---|---|
| `docker compose ps` | Status of both containers (look for "healthy") | दोन्ही containers ची स्थिती ("healthy" पाहा) |
| `docker compose logs -f backend` | Follow backend logs live (`-f` = follow) | Backend चे logs live पाहा (`-f` = follow) |
| `docker compose up -d --build frontend` | Rebuild and restart only the frontend | फक्त frontend पुन्हा build करून restart |
| `docker compose down` | Stop and remove both containers | दोन्ही containers बंद करून काढून टाका |

**Security note / सुरक्षा नोंद:**
- **EN:** The backend image does **not** contain `backend/.env`, because `.dockerignore` blocks it. Otherwise your OpenAI key would sit inside an image uploaded to ECR. The key is always given at run time through `environment:`.
- **MR:** Backend image मध्ये `backend/.env` **नसते**, कारण `.dockerignore` ती अडवतं. नाहीतर तुमची OpenAI key ECR वर upload झालेल्या image मध्ये बसून राहिली असती. Key नेहमी चालू होताना `environment:` मधूनच दिली जाते.

---

## 6. How the CI/CD pipeline uses Compose / CI/CD pipeline Compose कसा वापरते

```
git push ──▶ Job 1: Continuous-Integration (GitHub's ubuntu machine)
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
               └─ docker image prune -f  → deletes old images so the disk doesn't fill up
```

- **EN:** The **same** `docker-compose.yml` is used on your Mac, in Job 1 and in Job 2. The only difference is the `BACKEND_IMAGE` / `FRONTEND_IMAGE` variables, which point `image:` at ECR (e.g. `123456789012.dkr.ecr.ap-south-1.amazonaws.com/eka-backend:latest`). `--no-build` makes sure EC2 never builds and only runs what CI pushed.
- **MR:** **एकच** `docker-compose.yml` तुमच्या Mac वर, Job 1 मध्ये आणि Job 2 मध्ये वापरली जाते. फरक फक्त `BACKEND_IMAGE` / `FRONTEND_IMAGE` variables चा. ते `image:` ला ECR कडे वळवतात (उदा. `123456789012.dkr.ecr.ap-south-1.amazonaws.com/eka-backend:latest`). `--no-build` मुळे EC2 कधीच build करत नाही; CI ने push केलेलं तेच चालवतो.

### One-time setup / एकदाच करायचा setup

**AWS**
1. **EN:** Create two ECR repositories: `eka-backend` and `eka-frontend`. / **MR:** दोन ECR repositories बनवा: `eka-backend` आणि `eka-frontend`.
2. **EN:** Launch a Linux EC2 instance. In its security group allow inbound **8501** (UI), **22** (SSH), and optionally **8000** (API docs). / **MR:** Linux EC2 instance सुरू करा. Security group मध्ये inbound **8501** (UI), **22** (SSH), आणि हवं असल्यास **8000** (API docs) उघडा.
3. **EN:** Install Docker and the Compose plugin on the instance. / **MR:** Instance वर Docker आणि Compose plugin install करा.
   ```bash
   # Ubuntu
   sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
   sudo usermod -aG docker $USER && newgrp docker   # run docker without sudo / sudo शिवाय docker
   docker compose version                           # check / तपासा
   ```

**GitHub → Settings → Actions → Runners → New self-hosted runner → Linux**
- **EN:** Run the commands GitHub shows on EC2, then `sudo ./svc.sh install && sudo ./svc.sh start` so the runner keeps running after you log out. The runner connects **out** to GitHub, so no webhook is needed.
- **MR:** GitHub दाखवत असलेल्या commands EC2 वर चालवा, मग `sudo ./svc.sh install && sudo ./svc.sh start` करा, म्हणजे logout केल्यावरही runner चालू राहील. Runner स्वतः GitHub कडे **बाहेर** connection करतो, म्हणून webhook ची गरज नाही.

**GitHub → Settings → Secrets and variables → Actions**

| Secret | Example / उदाहरण |
|---|---|
| `AWS_ACCESS_KEY_ID` | IAM user key with ECR permissions / ECR permission असलेली IAM key |
| `AWS_SECRET_ACCESS_KEY` | (secret part of the key / key चा गुप्त भाग) |
| `AWS_DEFAULT_REGION` | `ap-south-1` |
| `ECR_REPO_BACKEND` | `eka-backend` |
| `ECR_REPO_FRONTEND` | `eka-frontend` |
| `OPENAI_API_KEY` | `sk-...` |

**EN:** Then push to `main` and open `http://<ec2-public-ip>:8501`.
**MR:** मग `main` वर push करा आणि `http://<ec2-public-ip>:8501` उघडा.

---

## 7. Things to know / लक्षात ठेवण्यासारख्या गोष्टी

1. **Uploaded documents are not permanent / Upload केलेले documents कायमचे नाहीत**
   - **EN:** Files added through `/api/ingest` are saved **inside** the backend container. The next deploy replaces the container, and those files are lost. To keep them, add documents to `backend/data/sample_docs/` in git, or mount a **volume** (a folder on EC2 that survives container replacement) for `backend/data`.
   - **MR:** `/api/ingest` मधून टाकलेल्या files backend container च्या **आत** साठतात. पुढच्या deploy मध्ये container बदलतो आणि त्या files जातात. त्या टिकवायच्या असतील तर documents git मधल्या `backend/data/sample_docs/` मध्ये टाका, किंवा `backend/data` साठी **volume** mount करा (EC2 वरचा folder, जो container बदलला तरी टिकतो).

2. **Tag `latest` only / फक्त `latest` tag**
   - **EN:** Every deploy overwrites `latest`, so you can't roll back to an old version. A common improvement is to also tag each image with the git commit SHA (a unique id for each commit).
   - **MR:** प्रत्येक deploy `latest` वर overwrite करतो, त्यामुळे जुन्या version वर परत जाता येत नाही. नेहमीची सुधारणा म्हणजे प्रत्येक image ला git commit SHA (प्रत्येक commit चा unique id) चा tag पण देणे.

3. **Other settings / इतर settings**
   - **EN:** `OPENAI_MODEL`, `RETRIEVAL_TOP_K`, etc. can be added under the backend's `environment:` the same way as `OPENAI_API_KEY`. If they are not set, the code uses its built-in defaults.
   - **MR:** `OPENAI_MODEL`, `RETRIEVAL_TOP_K` वगैरे `OPENAI_API_KEY` सारखेच backend च्या `environment:` खाली टाकता येतात. Set केले नाहीत तर code त्याचे default वापरतो.

---

## Quick summary / थोडक्यात

**EN:** Dockerfile = recipe for one image. Image = packed box. Container = running box. `docker-compose.yml` = runs both boxes together on a private network, where `backend` is the backend's address. `.dockerignore` keeps secrets out. The same compose file runs on your Mac and on EC2.

**MR:** Dockerfile = एका image ची रेसिपी. Image = पॅक केलेला डबा. Container = चालू असलेला डबा. `docker-compose.yml` = दोन्ही डबे एका खाजगी network वर एकत्र चालवतो, जिथे `backend` हाच backend चा पत्ता आहे. `.dockerignore` secrets बाहेर ठेवतो. एकच compose फाईल तुमच्या Mac वर आणि EC2 वर चालते.
