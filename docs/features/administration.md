# Administration

!!! note "Later: not in 0.0.1"
    0.0.1 serves one user, under their own Unix account, with no sign-in beyond a single-use link ([Signing in](../usage/sign-in.md)). Everything below is planned for later versions, in no set order. See the [roadmap](../roadmap/index.md).

- **Users and groups,** as in depictio, with roles per project.
- **Sign-in:** passwords, email sign-in links, OIDC and SAML single sign-on, and depictio accounts. Tokens for robots and links that open a single run.
- **Plugins** for engines, schedulers, sign-in, storage and notifications, installed like Python packages.
- **Backups and restore,** and moving an instance to another server.
- **Branding** of the interface.
- **Logs, background tasks and health** in one place.

What exists today is the [Profile page](../usage/profile.md), which says who the server runs as and where its files are, and `spectio doctor`, which checks a machine.
