#!/bin/sh
set -eu

# Setăm și ceasul folosit de daemonul cron, nu doar de comenzile Python.
TZ=${TZ:-Europe/Chisinau}
export TZ
if [ ! -f "/usr/share/zoneinfo/$TZ" ]; then
    echo "Fus orar necunoscut: $TZ" >&2
    exit 1
fi
ln -snf "/usr/share/zoneinfo/$TZ" /etc/localtime
printf '%s\n' "$TZ" > /etc/timezone

# Cron nu moștenește automat toate variabilele primite prin Compose.
# Salvăm doar configurația necesară, cu citare corectă pentru /bin/sh.
umask 077
/usr/local/bin/python - <<'PY'
import os
import shlex
from pathlib import Path

lines = []
for name in ("API_URL", "API_KEY", "TZ", "PYTHONUNBUFFERED"):
    if name in os.environ:
        lines.append(f"export {name}={shlex.quote(os.environ[name])}\n")
Path("/run/cron-env.sh").write_text("".join(lines), encoding="utf-8")
PY
umask 022

mkdir -p /app/data /app/logs
touch /app/logs/cron.log /app/logs/error.log
ln -sf /app/logs/cron.log /var/log/cron.log
ln -sf /app/logs/error.log /app/error.log
chmod 644 /app/logs/cron.log /app/logs/error.log

# Instalăm o singură dată: crontab de utilizator, fără câmpul "root".
crontab /app/lab03/cronjob
echo "Cron configurat. Ora containerului: $(date -Iseconds)"

# cron se desprinde și rulează în fundal; tail menține containerul activ
# și trimite conținutul fișierului în docker compose logs.
/usr/sbin/cron
echo "Cron pornit în fundal. Monitorizare /var/log/cron.log"
exec tail -n +1 -F /var/log/cron.log
