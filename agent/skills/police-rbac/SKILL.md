---
name: npf-hierarchical-rbac
description: Enforces row-level security based on Officer Rank. Use this when writing Django views, viewsets, or overriding manager QuerySets.
---
# Hierarchical RBAC Pipeline
When writing query logic for incident reports, always filter based on `request.user.officer_profile`:

- **Divisional HQ:** Filter by exact division (`division=user.division`).
- **Area Commander:** Filter by divisions in area command (`division__area_command=user.area_command`).
- **Commissioner of Police (CP):** Filter by whole state command (`division__area_command__state=user.state`).
- **AIG (Zone):** Filter by states in their zone (`division__area_command__state__zone=user.zone`).
- **IGP:** Do not append geographic filters (`all()`).

*Exception:* Terrorist Biodata queries bypass geographic filters to allow global lookup by all commands.
