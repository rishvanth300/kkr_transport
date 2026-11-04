# Backup & Restore (SRS M-10, FR-BKP-001–005)

Placeholder for Module 5. Will document:
- Provider daily backups (Neon/Supabase) — retention ≥ 7 days (RPO ≤ 24h).
- Weekly encrypted `pg_dump` to second location.
- Quarterly restore drill to a scratch DB + row-count sanity check (RTO ≤ 4h).
- Pre-release checklist: backup verified before every migration/deploy.
