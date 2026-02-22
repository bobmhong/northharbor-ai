# Auth0 Tenant Setup Guide

Step-by-step guide to configure Auth0 for NorthHarbor Sage.

## 1. Create Auth0 Tenant

1. Sign up at [auth0.com](https://auth0.com) (free tier: 25,000 MAU).
2. Create a new tenant (e.g., `northharbor-dev`).

## 2. Create SPA Application

1. Go to **Applications > Create Application**.
2. Name: `NorthHarbor Sage`
3. Type: **Single Page Web Applications**
4. Note the **Client ID** (you'll need it for `.env`).
5. Under **Settings**:
   - Allowed Callback URLs: `http://localhost:5173/callback`
   - Allowed Logout URLs: `http://localhost:5173`
   - Allowed Web Origins: `http://localhost:5173`

## 3. Create API

1. Go to **Applications > APIs > Create API**.
2. Name: `NorthHarbor Sage API`
3. Identifier (Audience): `https://sage-api.northharbor.dev`
4. Signing Algorithm: **RS256**

## 4. Enable Social Connections

1. Go to **Authentication > Social**.
2. Enable **Google**, **GitHub**, **Facebook** (or whichever you need).
3. For each, provide the OAuth client ID/secret from the respective provider's developer console.
4. Make sure each connection is enabled for the `NorthHarbor Sage` application.

## 5. Create Post-Login Action (Assign Roles)

1. Go to **Actions > Flows > Login**.
2. Create a custom action named `Assign Default Role`:

```javascript
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://northharbor.dev/roles';

  // First login: assign default client role
  if (event.stats.logins_count === 1) {
    api.user.setAppMetadata('roles', ['client']);
  }

  const roles = event.user.app_metadata?.roles || ['client'];
  api.accessToken.setCustomClaim(namespace, roles);
};
```

3. Drag the action into the Login flow.

## 6. Configure Password Policy

1. Go to **Authentication > Database > Username-Password-Authentication**.
2. Under **Password Policy**:
   - Minimum length: 12
   - Require uppercase, lowercase, numbers, special characters

## 7. Enable Attack Protection

1. Go to **Security > Attack Protection**.
2. Enable **Bot Detection**.
3. Enable **Brute-Force Protection** (default settings are good).
4. Enable **Breached Password Detection**.

## 8. Set Environment Variables

Copy `.env.example` and fill in your values:

```bash
cp .env.example .env
```

```
AUTH0_DOMAIN=northharbor-dev.auth0.com
AUTH0_API_AUDIENCE=https://sage-api.northharbor.dev
AUTH0_ALGORITHMS=RS256
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=northharbor_sage
```

## 9. Promote First Admin

To make a user an admin:

1. Go to **User Management > Users** in Auth0 Dashboard.
2. Find the user and click on them.
3. Scroll to **app_metadata** and set:

```json
{
  "roles": ["admin", "client"]
}
```

The Post-Login Action will inject this into the JWT on next login.

## 10. Verify

Start the backend and verify the health check:

```bash
source .venv/bin/activate
python -m backend.main
# GET http://localhost:8000/api/health -> {"status": "ok"}
```
