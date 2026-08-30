# Postgres

No custom config here yet — schema is applied automatically at runtime by
`brain/app/db/client.py`'s `_apply_schema()`, source of truth is
`brain/app/db/schema.sql`. This directory exists as a placeholder for init
scripts / custom `postgresql.conf` if that's ever needed; the actual data
lives in the `postgres_data` Docker volume, not here.
