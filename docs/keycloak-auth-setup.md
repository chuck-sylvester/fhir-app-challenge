# Keycloak Authentication Setup

This guide covers configuring Keycloak as the OAuth2/OIDC identity provider for the FHIR App Challenge application. Follow the **Local macOS** section for development setup, or the **OCI** section for cloud deployment.

---

## Local macOS Setup

### Prerequisites

- Docker Desktop installed and running
- Python 3.11
- Project cloned and `.env` file created from `.env.example`

### 1. Generate a session secret key

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output into `.env` as the value for `SESSION_SECRET_KEY`.

### 2. Start infrastructure services

```bash
docker compose up -d
```

Wait for Keycloak to become healthy (~60–90 seconds):

```bash
docker compose ps
```

Keycloak admin console will be available at `http://localhost:8180/admin`.

### 3. Configure Keycloak

Log in to the admin console with:
- **Username:** `admin`
- **Password:** value of `KEYCLOAK_ADMIN_PASSWORD` in `.env`

---

#### 3.1 Create the realm

1. Click the realm dropdown (top-left, shows **master**) → **Create Realm**
2. **Realm name:** `fachallenge`
3. **Enabled:** On
4. Click **Create**

Optionally, update the display name shown on the login page:
- **Realm Settings → General → Display name:** `FHIR App Challenge`

---

#### 3.2 Create the client

1. Left nav → **Clients** → **Create client**
2. **Client type:** `OpenID Connect`
3. **Client ID:** `fhir-demo`
4. Click **Next**
5. Enable **Client authentication** (makes the client confidential — required for a server-side app)
6. **Authentication flow:** leave **Standard flow** checked; uncheck everything else
7. Click **Next**
8. Set the following URLs:

| Field | Value |
|---|---|
| Valid redirect URIs | `http://localhost:8000/auth/callback` |
| Valid post logout redirect URIs | `http://localhost:8000/login` |
| Web origins | `http://localhost:8000` |

9. Click **Save**

#### Retrieve the client secret

1. **Clients → fhir-demo → Credentials** tab
2. Copy the value under **Client secret**
3. Set it as `KEYCLOAK_CLIENT_SECRET` in `.env`

---

#### 3.3 Create client scopes

**fhirUser scope**

1. Left nav → **Client Scopes** → **Create client scope**
2. **Name:** `fhirUser` | **Type:** `Default` | **Protocol:** `openid-connect`
3. Click **Save**
4. Go to the **Mappers** tab → **Add mapper** → **By configuration** → **User Attribute**
5. Fill in:

| Field | Value |
|---|---|
| Name | `fhirUser` |
| User Attribute | `fhirUser` |
| Token Claim Name | `fhirUser` |
| Claim JSON Type | `String` |
| Add to ID token | On |
| Add to access token | On |
| Add to userinfo | On |

6. Click **Save**

**patient/*.read scope**

1. **Client Scopes** → **Create client scope**
2. **Name:** `patient/*.read` | **Type:** `Optional` | **Protocol:** `openid-connect`
3. Click **Save** (no mapper needed)

**Assign both scopes to the client**

1. **Clients → fhir-demo → Client Scopes** tab
2. **Add client scope** → select `fhirUser` → **Add (Default)**
3. **Add client scope** → select `patient/*.read` → **Add (Optional)**

---

#### 3.4 Create test users

Repeat the following steps for each user in the table below.

1. Left nav → **Users** → **Create new user**
2. Set **Username**, **First name**, **Last name**, **Email** from the table
3. **Email verified:** On
4. Click **Create**
5. Go to the **Credentials** tab → **Set password**
6. Enter the password, disable **Temporary**, click **Save**

| Username | First | Last | Role |
|---|---|---|---|
| `clinician.alpha` | Alice | Anderson | MD |
| `clinician.bravo` | Bob | Brown | DO |
| `clinician.charlie` | Carol | Chen | RN |
| `clinician.delta` | David | Davis | PharmD |

**Shared password:** `fhir#2026!`

---

### 4. Verify `.env` settings

Confirm these values are set in `.env`:

```
APP_BASE_URL=http://localhost:8000
KEYCLOAK_URL=http://localhost:8180
KEYCLOAK_REALM=fachallenge
KEYCLOAK_CLIENT_ID=fhir-demo
KEYCLOAK_CLIENT_SECRET=<value from Credentials tab>
SESSION_SECRET_KEY=<generated value>
```

`APP_BASE_URL` is used as the `post_logout_redirect_uri` in the Keycloak logout redirect. It must match the **Valid post logout redirect URIs** value registered in the client (step 3.2).

### 5. Start the application

```bash
uvicorn app.main:app --reload --port 8000
```

Navigate to `http://localhost:8000` — the app should redirect to the Keycloak login page. Log in with any test user to confirm the flow completes successfully.

---

## OCI Deployment Setup

This section assumes a single OCI Compute VM running Docker Compose. The Keycloak configuration steps are identical to the local setup; only URLs and network rules differ.

### Prerequisites

- OCI Compute VM provisioned (Oracle Linux or Ubuntu)
- Docker and Docker Compose installed on the VM
- Project deployed to the VM (e.g., via `git clone` or `scp`)
- A public IP assigned to the VM (referred to as `<OCI_PUBLIC_IP>` below)

### 1. Open OCI security list rules

In the OCI Console, navigate to the VM's VCN → Security Lists and add the following **Ingress Rules**:

| Protocol | Source CIDR | Port | Purpose |
|---|---|---|---|
| TCP | `0.0.0.0/0` | `8000` | FastAPI application |
| TCP | `0.0.0.0/0` | `8180` | Keycloak admin + login |

> For a production deployment, restrict source CIDRs and place services behind a load balancer with HTTPS. Leave that for a later phase.

### 2. Configure `.env` for OCI

On the VM, edit `.env` and set these values using the VM's **public IP address** (not `localhost`):

```
APP_BASE_URL=http://<OCI_PUBLIC_IP>:8000
KEYCLOAK_URL=http://<OCI_PUBLIC_IP>:8180
KEYCLOAK_REALM=fachallenge
KEYCLOAK_CLIENT_ID=fhir-demo
KEYCLOAK_CLIENT_SECRET=<value from Credentials tab>
SESSION_SECRET_KEY=<freshly generated value>
```

Both `APP_BASE_URL` and `KEYCLOAK_URL` must use the public IP. See the [OCI Deployment Guide](oci-deployment-guide.md) for a full explanation of why.

Generate a new session secret on the VM:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start infrastructure services

```bash
docker compose up -d
```

Wait for Keycloak to become healthy before proceeding. On an OCI VM, Keycloak's JVM can take **up to 2 minutes** to fully initialize — the container will show `starting` during this window. Check status with:

```bash
docker compose ps
```

Once Keycloak shows `healthy`, access the admin console at:

```
http://<OCI_PUBLIC_IP>:8180/admin
```

### 4. Configure Keycloak

Follow **steps 3.1 through 3.4** from the local macOS section above, with one difference in step 3.2:

**Use OCI URLs instead of localhost for the client:**

| Field | Value |
|---|---|
| Valid redirect URIs | `http://<OCI_PUBLIC_IP>:8000/auth/callback` |
| Valid post logout redirect URIs | `http://<OCI_PUBLIC_IP>:8000/login` |
| Web origins | `http://<OCI_PUBLIC_IP>:8000` |

### 5. Start the application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The `--host 0.0.0.0` flag is required on the VM so the app binds to the public network interface, not just loopback. Navigate to `http://<OCI_PUBLIC_IP>:8000` to verify the login flow.

---

## Realm Export and Import

Once the `fachallenge` realm is fully configured, Keycloak can export it to a JSON file. On any future fresh deployment, Keycloak imports that file automatically at startup — eliminating all manual configuration steps in this guide.

### Export the realm

Run this from whichever environment has the fully configured realm (local or OCI):

```bash
docker exec -it fac-keycloak /opt/keycloak/bin/kc.sh export \
  --dir /tmp/export \
  --realm fachallenge \
  --users realm_file
```

Copy the file out of the container to the project:

```bash
# Create the destination directory first
mkdir -p keycloak

docker cp fac-keycloak:/tmp/export/fachallenge-realm.json ./keycloak/fachallenge-realm.json
```

> **Security note:** The exported file contains the `fhir-demo` client secret in plain text. Do not commit it to a public repository. Add `keycloak/` to `.gitignore` or store the file in a secrets manager for production use.

### What the export includes

- Realm settings, including `sslRequired=NONE` if already patched via `kcadm.sh`
- The `fhir-demo` client configuration
- Client scopes (`fhirUser`, `patient/*.read`) and their mappers
- Test users with hashed credentials

**Important — environment-specific redirect URIs:** The exported JSON contains the client redirect URIs from the environment where the export was done (e.g., `localhost` or an OCI public IP). After importing to a different environment, you must still update the `fhir-demo` client's redirect URIs to match the new host. See step 3.2 (local) or step 4 (OCI) of this guide.

### Import on a fresh deployment

Place the exported JSON in the `keycloak/` directory at the project root. Update `docker-compose.yaml` to mount the file and enable auto-import at startup:

```yaml
keycloak:
  command: start-dev --import-realm
  ...
  volumes:
    - keycloak_data:/opt/keycloak/data
    - ./keycloak/fachallenge-realm.json:/opt/keycloak/data/import/fachallenge-realm.json:ro
```

On first boot Keycloak imports the realm automatically. Because `sslRequired=NONE` is baked into the export, the OCI `kcadm.sh` SSL fix step is no longer needed on future deployments.

After startup, the only remaining manual steps are:

| Step | Local | OCI |
|---|---|---|
| Update `.env` with correct host values | Use `localhost` defaults | Set `KEYCLOAK_URL` and `APP_BASE_URL` to public IP |
| Update `fhir-demo` client redirect URIs | Only if exporting from OCI to local | Yes — update to public IP (step 4) |
| Set `KEYCLOAK_CLIENT_SECRET` in `.env` | Copy from Credentials tab | Copy from Credentials tab |

> Keycloak skips the import if the realm already exists in the persistent volume, so it is safe to leave `--import-realm` in the command permanently. To force a re-import on an existing deployment, first remove the volume: `docker volume rm <project-name>_keycloak_data`.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| Keycloak container shows `unhealthy` immediately after starting | The Keycloak 26 image is based on Red Hat UBI minimal and does not include `curl`. Any healthcheck that calls `curl` will always fail. | The `docker-compose.yaml` healthcheck uses a pure-bash TCP check instead. If you see this on an older copy of the repo, pull the latest and re-run `docker compose up -d`. |
| `We are sorry... HTTPS required` when accessing Keycloak via OCI public IP | Each Keycloak realm has a `sslRequired` setting that defaults to `EXTERNAL`. HTTP is permitted only from `localhost`; any other IP triggers this error — even in `start-dev` mode. | Run `kcadm.sh` inside the container to set `sslRequired=NONE` on the `master` and `fachallenge` realms. See the **Disable Keycloak's SSL requirement** section in the [OCI Deployment Guide](oci-deployment-guide.md). |
| `httpx.ConnectError: nodename nor servname provided` | `KEYCLOAK_URL` has a hostname that can't be resolved | Confirm `KEYCLOAK_URL` uses `localhost` (local) or the VM's public IP (OCI), not the Docker-internal hostname `keycloak` |
| Browser redirected to `localhost` Keycloak login page when accessing via OCI public IP | `KEYCLOAK_URL` is set to `localhost` on the VM — Keycloak builds redirect URLs from the incoming `Host` header | Set `KEYCLOAK_URL=http://<OCI_PUBLIC_IP>:8180` in `.env` on the VM |
| `OAuthError: invalid_redirect_uri` after logout | `post_logout_redirect_uri` not registered in Keycloak client | Ensure the client's **Valid post logout redirect URIs** includes `http://<host>:8000/login` (note the `/login` path) |
| `OAuthError: invalid_scope` | A requested scope doesn't exist in Keycloak | Create the missing client scope and assign it to the `fhir-demo` client (see 3.3) |
| `OAuthError: invalid_redirect_uri` | Callback URL not registered in Keycloak | Add the exact redirect URI to the client's **Valid redirect URIs** list |
| `500` after login, session not persisting | `SESSION_SECRET_KEY` missing or empty in `.env` | Generate and set a valid secret key |
