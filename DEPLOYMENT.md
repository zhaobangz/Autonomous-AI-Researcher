# Deployment Guide — GitHub Pages

This document outlines the steps to deploy the static landing page for the **Autonomous AI Researcher** project.

## 1. DNS Configuration (Apex Domain)

To point your custom domain (`research.autonomous-ai.io`) to GitHub Pages, configure the following DNS records with your provider:

### IPv4 Records (A)
| Type | Host | Value |
|------|------|-------|
| A | @ | 185.199.108.153 |
| A | @ | 185.199.109.153 |
| A | @ | 185.199.110.153 |
| A | @ | 185.199.111.153 |

### IPv6 Records (AAAA)
| Type | Host | Value |
|------|------|-------|
| AAAA | @ | 2606:50c0:8000::153 |
| AAAA | @ | 2606:50c0:8001::153 |
| AAAA | @ | 2606:50c0:8002::153 |
| AAAA | @ | 2606:50c0:8003::153 |

### Subdomain (CNAME)
| Type | Host | Value |
|------|------|-------|
| CNAME | www | <your-username>.github.io |

---

## 2. GitHub Pages Settings

1.  Navigate to **Settings → Pages** in the GitHub repository.
2.  Set the **Source** to `Deploy from a branch`.
3.  Select the `main` branch and the `/` (root) folder (or `docs` if files were moved).
4.  Enter the custom domain: `research.autonomous-ai.io`.
5.  **[CRITICAL]** Wait for the DNS records to propagate and for the TLS certificate (Let's Encrypt) to be issued.
6.  **[ACTION REQUIRED]** Once the certificate is ready, check the box **"Enforce HTTPS"** to ensure all traffic is secure.

---

## 3. Analytics & Monitoring

- **Analytics**: Plausible Analytics is pre-configured in `index.html`. Dashboard URL: `https://plausible.io/research.autonomous-ai.io`
- **Uptime Monitoring**: Configure a check for `https://research.autonomous-ai.io` using [Better Stack](https://betterstack.com/) or [UptimeRobot](https://uptimerobot.com/).
