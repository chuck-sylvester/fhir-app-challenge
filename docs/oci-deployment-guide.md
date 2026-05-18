# OCI Deployment Guide

The FHIR App Challenge application is deployed to and hosted within the Oracle Cloud Infrastructure (OCI) environment. The initial configuration mirrors the local development environment as a _Lift and Shift_ to a single VM.  

Create and start a single Oracle Compute instance, pull down the application from the GitHub public repository, complete some initial setup, such as populating the .env file, and you will be in a position to get started. Then, run the existing docker-compose stack (PostgreSQL + HAPI FHIR + Keycloak) plus uvicorn (FastAPI) on the OCI VM exactly as you do locally.  

Once you identify your public-facing URL, you can access the app from this URL, as opposed to the local development environment _localhost_.

## Deployment and Operations Notes

An SSH key pair is required to connect to your VM. If you already have one at `~/.ssh/id_rsa.pub` or `~/.ssh/id_ed25519.pub` you can use it. Otherwise generate one.  

Check to see if you have these files by viewing the contents of the `~/.ssh` directory.
```bash
cd ~/.ssh
ls -al
```

You will pasted the contents of the **public key** (`.pub` file) into the OCI console when creating the VM. Keep the private key on your Mac -- never share it.

### Set up your Virtual Cloud Network (VCN)

Every OCI compute instance must live inside a VCN. OCI provides a wizard that creates everything you need in one step. There are more details and specific settngs that you must provide, but the general steps are listed below:

- Create the VCN using the wizard
- Add firewall rules to the Security List

### Create the Compute Instance (VM)

- Launch the instance
- Find your instance's public IP

### Connect to the VM via SSH

- Connect as the `ubuntu` user (default for Ubuntu images on OCI)
- If your key is not the default (`~/.ssh/id_ed25519`), specify it explicitly
- Once connected, you will see the Ubuntu shell prompt

---

## Environment Configuration

After pulling the project to the VM, copy `.env.example` to `.env` and populate all values. Two variables must be set to the VM's **public IP address** rather than `localhost` for the application to work when accessed from a browser outside the VM:

```
APP_BASE_URL=http://<OCI_PUBLIC_IP>:8000
KEYCLOAK_URL=http://<OCI_PUBLIC_IP>:8180
```

**Why `KEYCLOAK_URL` must be the public IP**

FastAPI fetches the OIDC discovery document from `KEYCLOAK_URL` at login time. In `start-dev` mode, Keycloak reads the `Host` header of that request and uses it to build all authorization and token endpoint URLs in the discovery document. If FastAPI calls Keycloak via `localhost`, the returned authorization endpoint URL contains `localhost` — and a browser connecting from outside the VM cannot reach `localhost` on the server. Setting `KEYCLOAK_URL` to the public IP causes Keycloak to return public-IP-based URLs, which the browser can reach.

**Why `APP_BASE_URL` must be the public IP**

`APP_BASE_URL` is used as the `post_logout_redirect_uri` sent to Keycloak when a user logs out. Keycloak validates this value against the **Valid post logout redirect URIs** registered in the client configuration. The registered URI and the value in `.env` must match. See [Keycloak Authentication Setup](keycloak-auth-setup.md) for the required client settings.

---

## Docker Compose Infrastructure

Start all infrastructure services:

```bash
docker compose up -d
```

Verify all containers reach a healthy status:

```bash
docker compose ps
```

Expected startup times on an OCI VM:

| Container | Host Port | Typical time to `healthy` |
|---|---|---|
| `fac-postgres-db` | 5432 | ~10 seconds |
| `fac-hapi-fhir` | 8080 | ~60 seconds |
| `fac-keycloak` | 8180 | 60–120 seconds |

**Keycloak healthcheck**

The Keycloak 26 image (`quay.io/keycloak/keycloak:26.0`) is based on Red Hat UBI minimal and does not include `curl`. The `docker-compose.yaml` healthcheck therefore uses a pure-bash TCP check rather than a `curl` command. Keycloak's `start_period` is set to 120 seconds, so the container will report `starting` during that window and will not be marked `unhealthy` prematurely. On a resource-constrained VM, allow up to 3 minutes before expecting a `healthy` status.

### Disable Keycloak's SSL requirement for external IPs

Once Keycloak is healthy, you must disable its realm-level SSL policy before the admin console is accessible via the public IP.

**Root cause:** Every Keycloak realm has a `sslRequired` setting that defaults to `EXTERNAL`. In this mode, HTTP is allowed only for `localhost`; any other IP triggers a "HTTPS required" error page — even in `start-dev` mode and even if Keycloak itself has no HTTPS listener. Accessing the VM via its public IP is considered "external".

Run these commands from the VM (they target the container's internal port, so they bypass the external-IP restriction):

```bash
# Step 1: Authenticate with the Keycloak admin API (uses internal port 8080)
docker exec -it fac-keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 \
  --realm master \
  --user admin \
  --password <KEYCLOAK_ADMIN_PASSWORD>

# Step 2: Disable SSL requirement on the master realm
docker exec -it fac-keycloak /opt/keycloak/bin/kcadm.sh update realms/master \
  -s sslRequired=NONE
```

After step 2, `http://<OCI_PUBLIC_IP>:8180/admin` should load in the browser. Continue with the [Keycloak Authentication Setup](keycloak-auth-setup.md) guide (steps 3.1–3.4) to create the `fachallenge` realm and client. After step 3.1 (realm creation), immediately return to the VM and run:

```bash
# Step 3: Disable SSL requirement on the fachallenge realm
docker exec -it fac-keycloak /opt/keycloak/bin/kcadm.sh update realms/fachallenge \
  -s sslRequired=NONE
```

This must be done before continuing Keycloak configuration, as the browser will otherwise be blocked from any `fachallenge` realm page.

---

## Start the Application

Once all containers are healthy, start the FastAPI server. The `--host 0.0.0.0` flag is required on the VM so the app binds to the public network interface rather than loopback:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Navigate to `http://<OCI_PUBLIC_IP>:8000` to verify the login flow.