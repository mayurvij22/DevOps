# DevTools Lab: GitHub Actions + JFrog Artifactory

A hands-on practice project for the **Intuit Platform Support Engineer** interview.
You will build a real pipeline that pulls dependencies from Artifactory, scans them
with Xray, and publishes a JAR and Docker image back to Artifactory, all from GitHub
Actions. Then you will break it on purpose and fix it, like a support engineer.

**Time needed:** about 3 hours (Saturday afternoon is perfect).

---

## 1. What this lab covers (mapped to the job description)

| JD requirement | Where you practice it |
|---|---|
| Administering GitHub | Repo setup, branch protection, CODEOWNERS, secrets vs variables |
| Administering Artifactory | Local, remote, virtual repos, access tokens, Docker registry |
| CI/CD workflows | `.github/workflows/ci.yml` (triggers, jobs, `needs`, conditions) |
| Security and vulnerability alerts | Xray scan (`jf audit`), Dependabot, secret scanning |
| Scripting and automation | `scripts/github_audit.py` (API, pagination, rate limits) |
| Support and troubleshooting | Section 6: Break-it labs (401, 403, 404, failing test) |

---

## 2. How the pipeline flows

```
Developer pushes code / opens PR
            |
            v
   GitHub Actions starts (ci.yml)
            |
     +------+----------------+
     |                       |
 [Build & Test]        [Xray Scan]        <- run in PARALLEL
 deps from VIRTUAL     checks CVEs
 repo (local+remote)   and licenses
     |                       |
     +----------+------------+
                |  (only on main, never on PRs)
                v
          [Publish]
  JAR   -> demo-maven-local
  Image -> demo-docker-local
  Build-info -> Artifactory (traceability)
```

---

## 3. Setup Part A: JFrog Artifactory (about 45 min)

1. Go to **jfrog.com** and start the **free cloud trial**. You get a URL like
   `https://yourname.jfrog.io`. The trial includes Artifactory and Xray.
2. Go to **Administration > Repositories** and create these four repositories:

   | Type | Package type | Repository key | Purpose |
   |---|---|---|---|
   | Local | Maven | `demo-maven-local` | Stores JARs your team builds |
   | Remote | Maven | `demo-maven-remote` | Proxy and cache for Maven Central (URL: `https://repo1.maven.org/maven2/`) |
   | Virtual | Maven | `demo-maven-virtual` | Combines the two above; include both |
   | Local | Docker | `demo-docker-local` | Stores Docker images |

3. Create an access token: click your profile icon, open **Edit Profile**, and
   **Generate an Identity Token**. Copy it immediately; it is shown only once.
4. (Optional, for Xray) Go to **Xray > Indexed Resources** and add your repos
   so Xray scans them.

**Interview line:** *"Developers configure only the virtual repo URL. It searches the
local repo first, then the remote repo, which caches Maven Central, so builds are
faster and still work if Maven Central is down."*

---

## 4. Setup Part B: GitHub (about 30 min)

1. Create a **public** GitHub repo named `devtools-lab` (branch protection is free
   on public repos) and push this project to it:
   ```bash
   git init && git add . && git commit -m "Initial lab"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/devtools-lab.git
   git push -u origin main
   ```
2. Edit `.github/CODEOWNERS` and replace `YOUR_GITHUB_USERNAME`.
3. Go to **Settings > Secrets and variables > Actions**.

   Under the **Secrets** tab, add:
   - `JF_ACCESS_TOKEN` = the token from step A3

   Under the **Variables** tab, add:
   - `JF_URL` = `https://yourname.jfrog.io`
   - `JF_USER` = your JFrog login email
   - `MAVEN_VIRTUAL_REPO` = `demo-maven-virtual`
   - `MAVEN_LOCAL_REPO` = `demo-maven-local`
   - `DOCKER_LOCAL_REPO` = `demo-docker-local`

   **Interview line:** *"Secrets are encrypted and masked in logs. Variables are for
   non-sensitive config like URLs and repo names. Never put a token in a variable."*

4. Go to **Settings > Branches > Add branch protection rule** (or **Rules > Rulesets**)
   for `main` and enable:
   - Require a pull request before merging (1 approval)
   - Require review from Code Owners
   - Require status checks to pass (select **Build & Test** after the first run)
   - Do not allow force pushes

5. Go to **Settings > Code security** and enable **Dependabot alerts**,
   **Dependabot security updates**, and **Secret scanning with push protection**.

---

## 5. Run it

1. Open the **Actions** tab. The first run starts automatically from your push.
2. Watch **Build & Test** and **Xray Scan** run side by side, then **Publish**.
3. In JFrog, check:
   - `demo-maven-remote-cache` now holds JUnit (proof the remote repo cached it)
   - `demo-maven-local` holds `demo-app-1.0.0-SNAPSHOT.jar`
   - `demo-docker-local` holds `demo-app:<run number>`
   - **Builds** shows your build-info (which commit produced which artifact)
4. Create a branch, change something, and open a PR. Notice **Publish** is skipped
   on PRs, and you cannot merge until checks pass and a Code Owner approves.

---

## 6. Break-it labs (the most valuable part for a support interview)

Do each one, read the error in the logs, fix it, and practice explaining it out loud.

### Lab 1: 401 Unauthorized (expired or wrong token)
**Break:** Edit the `JF_ACCESS_TOKEN` secret and change one character. Re-run the workflow.
**What you'll see:** Maven or JFrog CLI fails with `401`.
**Fix:** Generate a new token and update the secret.
**Say in the interview:** *"401 is authentication. If it worked yesterday, the most likely
cause is an expired or rotated token. I check the CI secret, token expiry, and whether the
service account is still active. To prevent repeats, I'd set up alerts before tokens expire."*

### Lab 2: 404 Not Found (wrong repository)
**Break:** Change the `MAVEN_VIRTUAL_REPO` variable to `demo-maven-wrong`. Re-run.
**Fix:** Restore the correct repo key.
**Say:** *"404 means the path or repository doesn't exist, or the remote repo can't find the
package upstream. I verify the repo key and the artifact path in Artifactory."*

### Lab 3: 403 Forbidden (missing permission)
**Break:** In JFrog, create a new user with read-only permission on `demo-maven-local`,
generate a token for that user, and put it in the secret. The Publish job will fail.
**Fix:** Grant deploy permission (Administration > Permissions) or use the correct user.
**Say:** *"403 means authenticated but not allowed. I check the permission target for that
user or group and the repositories it covers, following least privilege."*

### Lab 4: Failing test blocks the merge
**Break:** In `AppTest.java`, change `5` to `6`. Push to a branch and open a PR.
**What you'll see:** Build & Test fails and the PR merge button is blocked.
**Say:** *"Branch protection requires status checks to pass, so broken code never
reaches main. The developer fixes the test and pushes again."*

### Lab 5: Dependabot and Xray find a vulnerability
**Break:** In `pom.xml`, add an old dependency with known CVEs, for example
`commons-collections:commons-collections:3.2.1`. Push it.
**What you'll see:** Xray lists CVEs in the scan job, and Dependabot raises an alert.
**Say:** *"I'd check the severity and whether the vulnerable code is actually used, find
the fixed version, raise or merge the Dependabot PR, and track it until it's closed. For
critical CVEs, Xray policies can block the artifact from being downloaded at all."*

**Tip:** Take screenshots of each error. Seeing the real error message once makes it
much easier to talk about confidently.

---

## 7. The script: `scripts/github_audit.py`

Finds stale repos (no push in N days) and repos whose default branch is not protected,
and writes a CSV. Run it:

```bash
pip install requests
export GITHUB_TOKEN=ghp_your_token
python scripts/github_audit.py --owner YOUR_USERNAME --days 90
```

**Interview line:** *"I'd use the GitHub REST API with a token from an environment variable.
GitHub returns at most 100 items per page, so I follow the pagination links, and I check the
rate-limit headers and wait if the limit runs out. The output is a CSV the team can review
before decommissioning repos."*

On GitHub Enterprise Server, the only change is the API URL: `https://YOUR-GHES-HOST/api/v3`.

---

## 8. Your 60-second answer: "Walk me through a pipeline you've built"

> "I built a practice pipeline in GitHub Actions integrated with JFrog Artifactory, to map
> my GitLab experience to GitHub and Artifactory. It triggers on pushes and pull requests to
> main. The first job builds and tests a Java Maven app, resolving dependencies through an
> Artifactory virtual repository that combines a local repo with a remote repo caching Maven
> Central. In parallel, a second job runs a JFrog Xray scan for vulnerable dependencies.
> Only on main, a publish job deploys the JAR to a Maven local repo, pushes a Docker image
> to a Docker local repo, and publishes build-info for traceability. Credentials are stored
> as GitHub secrets, and main is protected with required reviews from CODEOWNERS and
> required status checks. I also practiced troubleshooting by deliberately causing 401,
> 403, and 404 errors and fixing them."

**Be honest:** Say "I built a practice lab." Don't present it as production work at a client.
Interviewers respect initiative, and it's a strong answer to "How are you closing the gap?"

---

## 9. Quick-reference: concepts from this lab

| Concept | One-line explanation |
|---|---|
| `on:` triggers | Events that start the workflow (push, pull_request, manual) |
| Job vs step | Jobs run on separate runners (parallel by default); steps run in order inside a job |
| `needs:` | Makes a job wait for other jobs |
| `if:` | Condition to run or skip a job (here: publish only on main) |
| Runner | The machine that executes a job: GitHub-hosted or self-hosted |
| `permissions:` | Limits what the built-in `GITHUB_TOKEN` can do (least privilege) |
| Secret vs variable | Secret = encrypted and masked; variable = plain config |
| Local / remote / virtual | Your artifacts / cached external packages / one URL for both |
| Build-info | Record of which commit, dependencies, and artifacts made up a build |
| Xray | Scans artifacts for CVEs and license issues; policies can block them |
| Dependabot | Alerts and auto-PRs for vulnerable or outdated dependencies |
| CODEOWNERS | Auto-assigns required reviewers by file path |
| Branch protection / rulesets | Rules on branches: required reviews, checks, no force push |
| Better than tokens | OIDC: short-lived credentials issued per workflow run, no stored secret |
#   D e v O p s  
 