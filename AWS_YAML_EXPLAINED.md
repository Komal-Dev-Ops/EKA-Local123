# `aws.yaml` Explained — English + मराठी

This file explains `.github/workflows/aws.yaml`: why it exists, how to create it from scratch, and what every line does.

ही फाईल `.github/workflows/aws.yaml` समजावते: ती का आहे, सुरुवातीपासून कशी बनवायची, आणि प्रत्येक ओळ काय करते.

---

## 1. Why does this file exist? / ही फाईल का आहे?

**English:**
Without this file, every deployment is manual. You would build two Docker images on your laptop, upload them to AWS, SSH into EC2, download them, and restart the containers. You would repeat all of that for every code change.

`aws.yaml` is a **recipe** that GitHub follows automatically. Every time you push code to `main`, GitHub reads this recipe and does all those steps for you. This is called **CI/CD**:
- **CI (Continuous Integration)** — build the images and store them in AWS ECR.
- **CD (Continuous Deployment)** — take those images and run them on EC2.

Analogy: it is like a restaurant order ticket. You (the developer) just place the order (`git push`). The kitchen (GitHub) cooks (build), and the waiter (runner on EC2) serves it (deploy).

**मराठी:**
ही फाईल नसेल तर प्रत्येक deployment हाताने (manually) करावं लागेल. Laptop वर दोन Docker images बनवा, AWS वर upload करा, EC2 मध्ये SSH करा, images download करा आणि containers restart करा. प्रत्येक code बदलानंतर हे सगळं पुन्हा करावं लागेल.

`aws.yaml` ही एक **रेसिपी** आहे जी GitHub आपोआप पाळतं. तुम्ही `main` branch वर code push केला की GitHub ही रेसिपी वाचतं आणि सगळी कामं तुमच्यासाठी करतं. याला **CI/CD** म्हणतात:
- **CI (Continuous Integration)** — images build करून AWS ECR मध्ये ठेवणे.
- **CD (Continuous Deployment)** — त्या images EC2 वर चालवणे.

उदाहरण: हॉटेलमधल्या ऑर्डर-स्लिपसारखं. तुम्ही (developer) फक्त ऑर्डर देता (`git push`). किचन (GitHub) जेवण बनवतं (build), आणि वेटर (EC2 वरचा runner) ते वाढतो (deploy).

---

## 2. The big picture / संपूर्ण प्रवाह

```
 Your laptop          GitHub cloud machine            AWS ECR               EC2 (self-hosted runner)
 ───────────          ────────────────────            ───────               ────────────────────────
 git push  ────────▶  Job 1: Continuous-Integration
                      • checkout code
                      • login to AWS
                      • docker compose build
                      • docker compose push  ──────▶  eka-backend:latest
                                                      eka-frontend:latest
                                                            │
                      Job 2: Continuous-Deployment          │
                      (runs ON the EC2 machine) ◀───────────┘
                      • docker compose pull
                      • docker compose up -d
                                                                          App live on :8501
```

**मराठी:** तुम्ही push करता → GitHub च्या machine वर images बनतात → त्या ECR (AWS चं खाजगी image गोदाम) मध्ये जातात → EC2 वरचा runner त्या images खेचतो (pull) आणि app चालू करतो.

---

## 3. How to create this file / ही फाईल कशी बनवायची

### Rule 1: The location is fixed / जागा ठरलेली आहे
GitHub looks for workflows **only** in this folder:

GitHub फक्त याच folder मध्ये workflows शोधतं:

```
your-project/
└── .github/
    └── workflows/
        └── aws.yaml      ← any name is fine, but the extension must be .yml or .yaml
```

- The folder name must be exactly `.github` (with the dot) and `workflows` (plural).
- Folder चं नाव नेमकं `.github` (सुरुवातीला डॉट) आणि `workflows` (अनेकवचन) असलंच पाहिजे. चूक झाली तर GitHub फाईलकडे दुर्लक्ष करेल, आणि कोणतीही error दाखवणार नाही.

### Option A: From the terminal / Terminal मधून
```bash
mkdir -p .github/workflows          # create both folders at once / दोन्ही folders एकदम बनवा
touch .github/workflows/aws.yaml    # create an empty file / रिकामी फाईल बनवा
# open it in PyCharm / VS Code and write the content (Section 4)
```

### Option B: From the GitHub website / GitHub website वरून
Repo → **Actions** tab → **New workflow** → **set up a workflow yourself**. GitHub creates the folder for you. Paste the content and click **Commit changes**.

Repo → **Actions** tab → **New workflow** → **set up a workflow yourself**. GitHub स्वतः folder बनवतं. Content paste करा आणि **Commit changes** दाबा.

### Rule 2: YAML is space-sensitive / YAML मध्ये spaces महत्त्वाचे
- Indentation (spaces at the start of a line) shows what belongs inside what, like folders inside folders.
- Use **2 spaces**. **Never use Tab**, or the file breaks.
- `-` (dash) at the start means "one item in a list".
- `key: value` means "this setting has this value".

- ओळीच्या सुरुवातीचे spaces (indentation) सांगतात की कोणती गोष्ट कशाच्या आत आहे, जसं folder च्या आत folder.
- **2 spaces** वापरा. **Tab कधीच वापरू नका**, नाहीतर फाईल तुटते.
- सुरुवातीचा `-` (dash) म्हणजे "list मधली एक वस्तू".
- `key: value` म्हणजे "या setting ची ही किंमत".

### Rule 3: Build it in this order / या क्रमाने लिहा
1. `name` → the workflow's display name / workflow चं नाव
2. `on` → **when** it runs / **कधी** चालायचं
3. `jobs` → **what** runs / **काय** करायचं
4. Inside each job: `runs-on` (**where**) + `steps` (**how**, one by one) / प्रत्येक job मध्ये: `runs-on` (**कुठे**) + `steps` (**कसं**, एकेक करून)

---

## 4. Line-by-line explanation / ओळ-न्-ओळ स्पष्टीकरण

### Part 1 — Name and trigger / नाव आणि trigger

```yaml
name: Deploy Application Docker Images to EC2 instance
```
- **EN:** The label shown in the GitHub **Actions** tab. It is only for humans and has no effect on how the workflow runs.
- **MR:** GitHub च्या **Actions** tab मध्ये दिसणारं नाव. हे फक्त माणसांसाठी आहे; कामावर याचा परिणाम होत नाही.

```yaml
on:
  push:
    branches: [main]
  workflow_dispatch:   # adds a "Run workflow" button in the GitHub Actions tab
```
- **EN:** `on` = the **trigger**, meaning when to start.
  - `push` + `branches: [main]` → run whenever code is pushed to `main`. Pushes to other branches do not deploy.
  - `workflow_dispatch` → adds a manual **Run workflow** button, so you can deploy without changing code.
- **MR:** `on` = **trigger**, म्हणजे काम कधी सुरू करायचं.
  - `push` + `branches: [main]` → `main` वर code push झाला की चालेल. दुसऱ्या branch वरचा push deploy करत नाही.
  - `workflow_dispatch` → **Run workflow** बटण मिळतं, म्हणजे code न बदलता हाताने deploy करता येतं.

### Part 2 — Job 1: Continuous-Integration (build + push)

```yaml
jobs:
  Continuous-Integration:
    runs-on: ubuntu-latest
```
- **EN:** `jobs` holds all the jobs. `Continuous-Integration` is the job's name (you choose it). `runs-on: ubuntu-latest` means GitHub lends you a **fresh, free Linux machine** for this job and deletes it afterwards.
- **MR:** `jobs` मध्ये सगळे jobs असतात. `Continuous-Integration` हे job चं नाव (तुम्ही ठेवलेलं). `runs-on: ubuntu-latest` म्हणजे GitHub या job साठी एक **नवीन, मोफत Linux machine** उधार देतं आणि काम झाल्यावर ती नष्ट करतं.

```yaml
    steps:
      - name: Checkout
        uses: actions/checkout@v4
```
- **EN:** `steps` = the to-do list, run top to bottom. The borrowed machine starts **empty**, so the first step downloads your repo code onto it. `uses:` means "use a ready-made action someone else wrote" (like importing a library). `@v4` is its version.
- **MR:** `steps` = कामांची यादी, वरून खाली क्रमाने. उधार machine **रिकामी** असते, म्हणून पहिली step तुमच्या repo चा code त्यावर download करते. `uses:` म्हणजे "दुसऱ्याने आधीच लिहिलेली action वापरा" (library import करण्यासारखं). `@v4` म्हणजे तिची version.

```yaml
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ secrets.AWS_DEFAULT_REGION }}
```
- **EN:** Logs this machine in to your AWS account. `with:` passes inputs to the action.
  `${{ secrets.X }}` means "read X from GitHub's encrypted secret store" (Settings → Secrets and variables → Actions). The real key is **never written in this file**. If it were, anyone who can read the repo could use your AWS account. GitHub also hides secrets as `***` in the logs.
- **MR:** ही step machine ला तुमच्या AWS account मध्ये login करते. `with:` म्हणजे action ला दिलेले inputs.
  `${{ secrets.X }}` म्हणजे "X ची किंमत GitHub च्या encrypted तिजोरीतून घ्या" (Settings → Secrets and variables → Actions). खरी key **या फाईलमध्ये कधीच लिहायची नाही**. लिहिली तर repo पाहणारा कोणीही तुमचं AWS account वापरू शकेल. GitHub logs मध्येही secrets `***` असे लपवतं.

```yaml
      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
```
- **EN:** Logs Docker in to **ECR** (Elastic Container Registry, AWS's private "Google Drive for Docker images"). `id: login-ecr` gives this step a nickname so later steps can read its **output**, which is the registry address (like `123456789.dkr.ecr.ap-south-1.amazonaws.com`).
- **MR:** Docker ला **ECR** मध्ये login करते (Elastic Container Registry, Docker images साठी AWS चं खाजगी "Google Drive"). `id: login-ecr` हे या step चं टोपणनाव आहे. त्यामुळे पुढच्या steps तिचं **output** वाचू शकतात, म्हणजे registry चा पत्ता (उदा. `123456789.dkr.ecr.ap-south-1.amazonaws.com`).

```yaml
      - name: Build and push backend + frontend images to Amazon ECR
        env:
          BACKEND_IMAGE: ${{ steps.login-ecr.outputs.registry }}/${{ secrets.ECR_REPO_BACKEND }}:latest
          FRONTEND_IMAGE: ${{ steps.login-ecr.outputs.registry }}/${{ secrets.ECR_REPO_FRONTEND }}:latest
        run: |
          docker compose build
          docker compose push
```
- **EN:**
  - `env:` sets environment variables for this step only. Each one builds a full image name: `registry-address/repo-name:latest`.
  - `docker-compose.yml` has `image: ${BACKEND_IMAGE:-eka-backend:latest}`. It uses `BACKEND_IMAGE` if it is set, otherwise the local default. So the **same compose file** works on your laptop and in the pipeline.
  - `run: |` runs shell commands. `|` means "multiple lines follow".
  - `docker compose build` builds both images. `docker compose push` uploads them to ECR.
- **MR:**
  - `env:` फक्त या step साठी environment variables ठेवतो. प्रत्येक variable पूर्ण image नाव बनवतो: `registry-पत्ता/repo-नाव:latest`.
  - `docker-compose.yml` मध्ये `image: ${BACKEND_IMAGE:-eka-backend:latest}` आहे. `BACKEND_IMAGE` दिलं असेल तर ते वापरतं, नसेल तर local default. म्हणून **एकच compose फाईल** laptop वर आणि pipeline मध्ये दोन्हीकडे चालते.
  - `run: |` shell commands चालवतो. `|` म्हणजे "पुढे अनेक ओळी आहेत".
  - `docker compose build` दोन्ही images बनवतं. `docker compose push` त्या ECR वर upload करतं.

### Part 3 — Job 2: Continuous-Deployment (on EC2)

```yaml
  Continuous-Deployment:
    needs: Continuous-Integration
    runs-on: self-hosted
```
- **EN:**
  - `needs:` means "wait until Continuous-Integration **succeeds**". If the build fails, nothing broken gets deployed.
  - `runs-on: self-hosted` means "run this job on **my own** machine", i.e. the EC2 instance where you installed the GitHub runner. The runner connects **out** to GitHub and asks "any work for me?". That's why no webhook or extra open port is needed.
- **MR:**
  - `needs:` म्हणजे "Continuous-Integration **यशस्वी** होईपर्यंत थांबा". Build fail झालं तर तुटलेलं काहीही deploy होत नाही.
  - `runs-on: self-hosted` म्हणजे "हा job **माझ्या स्वतःच्या** machine वर चालवा", म्हणजे ज्या EC2 वर तुम्ही GitHub runner install केला आहे ती. Runner स्वतः GitHub कडे **बाहेर** connection करून विचारतो "माझ्यासाठी काम आहे का?". म्हणून webhook किंवा जास्तीचा port उघडायची गरज नाही.

```yaml
    steps:
      # Needed so docker-compose.yml is present on the EC2 instance
      - name: Checkout
        uses: actions/checkout@v4
```
- **EN:** A different machine means a fresh checkout. EC2 needs `docker-compose.yml` to know how to run the two containers. Lines starting with `#` are comments that GitHub ignores.
- **MR:** वेगळी machine म्हणून पुन्हा checkout करावं लागतं. दोन containers कसे चालवायचे हे कळण्यासाठी EC2 ला `docker-compose.yml` लागतं. `#` ने सुरू होणाऱ्या ओळी comments आहेत; GitHub त्यांच्याकडे दुर्लक्ष करतं.

```yaml
      - name: Configure AWS credentials
        ...
      - name: Login to Amazon ECR
        id: login-ecr
        ...
```
- **EN:** Same as in Job 1. Each job is **separate**, so EC2 must log in to AWS and ECR on its own before it can download the private images.
- **MR:** Job 1 सारखंच. प्रत्येक job **स्वतंत्र** असतो, म्हणून खाजगी images download करण्याआधी EC2 ला स्वतः AWS आणि ECR मध्ये login करावं लागतं.

```yaml
      - name: Pull latest images and restart containers
        env:
          BACKEND_IMAGE: ...
          FRONTEND_IMAGE: ...
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          docker compose -p eka pull
          docker compose -p eka up -d --no-build --remove-orphans
          docker image prune -f
```
- **EN:**
  - `OPENAI_API_KEY` is passed at **run time**. It is never stored inside the image (`.dockerignore` also blocks `.env`), so anyone who gets the image does not get your key.
  - `-p eka` is the **project name**. It keeps container names the same across deployments, so the old containers get **replaced** instead of duplicated.
  - `pull` downloads the newest images from ECR.
  - `up -d` starts the containers in the background (`-d` = detached).
  - `--no-build` means "don't build here, only use the downloaded images". EC2 stays light.
  - `--remove-orphans` removes containers of services that no longer exist in the compose file.
  - `docker image prune -f` deletes old unused images so the EC2 disk doesn't fill up. `-f` means don't ask for confirmation.
- **MR:**
  - `OPENAI_API_KEY` **चालू होताना** दिली जाते. ती image मध्ये कधीच साठवली जात नाही (`.dockerignore` सुद्धा `.env` अडवतं), त्यामुळे image कोणाला मिळाली तरी key मिळत नाही.
  - `-p eka` हे **project नाव** आहे. त्यामुळे प्रत्येक deployment मध्ये container नावं तीच राहतात, आणि जुने containers दुप्पट न होता **बदलले** जातात.
  - `pull` ECR मधून नवीन images download करतो.
  - `up -d` containers background मध्ये चालू करतो (`-d` = detached).
  - `--no-build` म्हणजे "इथे build करू नका, download केलेल्या images च वापरा". EC2 वर भार कमी राहतो.
  - `--remove-orphans` compose फाईलमधून काढलेल्या services चे containers काढून टाकतो.
  - `docker image prune -f` जुन्या, न वापरलेल्या images हटवतो, म्हणजे EC2 ची disk भरत नाही. `-f` म्हणजे confirmation विचारू नका.

---

## 5. Secrets this file needs / या फाईलला लागणारे secrets

Add these in GitHub → **Settings → Secrets and variables → Actions → New repository secret**. The names must match **exactly** (capital letters, underscores).

हे GitHub → **Settings → Secrets and variables → Actions → New repository secret** मध्ये टाका. नावं **नेमकी** जुळली पाहिजेत (capital अक्षरं, underscore).

| Secret | Used for / कशासाठी |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS login (username सारखं) |
| `AWS_SECRET_ACCESS_KEY` | AWS login (password सारखं) |
| `AWS_DEFAULT_REGION` | e.g. `ap-south-1` (AWS चा प्रदेश) |
| `ECR_REPO_BACKEND` | `eka-backend` (backend image चं गोदाम) |
| `ECR_REPO_FRONTEND` | `eka-frontend` (frontend image चं गोदाम) |
| `OPENAI_API_KEY` | Backend calls OpenAI / backend OpenAI ला call करतो |

---

## 6. Common mistakes / नेहमीच्या चुका

| Mistake / चूक | What happens / काय होतं |
|---|---|
| Tab instead of spaces / spaces ऐवजी Tab | YAML error, workflow doesn't start / workflow सुरूच होत नाही |
| Folder named `.github/workflow` (no "s") | GitHub ignores the file silently / GitHub फाईलकडे गुपचूप दुर्लक्ष करतं |
| Secret name typo (`AWS_REGION` vs `AWS_DEFAULT_REGION`) | Value comes out empty → login fails / किंमत रिकामी येते → login fail |
| Real keys pasted into the yaml / yaml मध्ये खऱ्या keys | Security leak. Delete the key in AWS IAM immediately / AWS IAM मध्ये key लगेच delete करा |
| Runner offline on EC2 / EC2 वरचा runner बंद | Job 2 stuck on "Waiting for a runner" → run `sudo ./svc.sh start` |
| Runner can't use Docker / runner ला Docker वापरता येत नाही | `permission denied docker.sock` → add the user to the `docker` group and restart the runner |

---

## 7. Quick summary / थोडक्यात

**EN:** `on` = when, `jobs` = what, `runs-on` = where, `steps` = how. Job 1 builds on GitHub's machine and stores the images in ECR. Job 2 runs on your EC2 and starts the app. Secrets stay in GitHub's store, never in the file.

**MR:** `on` = कधी, `jobs` = काय, `runs-on` = कुठे, `steps` = कसं. Job 1 GitHub च्या machine वर images बनवून ECR मध्ये ठेवतो. Job 2 तुमच्या EC2 वर app चालू करतो. Secrets GitHub च्या तिजोरीत राहतात, फाईलमध्ये कधीच नाहीत.
