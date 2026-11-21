#!/usr/bin/env bash
# Phase B: key-only sshd, no root login, root password locked. Run as root.
# Run ONLY after a human has confirmed, from a new terminal, that
#   ssh <TARGET_USER>@<server>  and  sudo whoami  both work.
#
#   CONFIRM_KEY_LOGIN=yes TARGET_USER=ubuntu [ALLOW_USERS="ubuntu"] [LOCK_ROOT=yes] \
#     sudo -E bash lockdown-ssh.sh
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
[[ "${CONFIRM_KEY_LOGIN:-}" == yes ]] || {
  echo "Refusing: set CONFIRM_KEY_LOGIN=yes only after a human tested key login + sudo in a new session." >&2; exit 1; }
TARGET_USER="${TARGET_USER:?Set TARGET_USER}"
LOCK_ROOT="${LOCK_ROOT:-yes}"
ALLOW_USERS="${ALLOW_USERS:-}"
CONF=/etc/ssh/sshd_config.d/00-hardening.conf

# Pre-flight: the user we're about to depend on must really be usable.
id "$TARGET_USER" >/dev/null
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"
AK="$TARGET_HOME/.ssh/authorized_keys"
[[ -s "$AK" ]] || { echo "Refusing: $AK is empty or missing." >&2; exit 1; }
ssh-keygen -l -f "$AK" >/dev/null || { echo "Refusing: $AK has no valid key." >&2; exit 1; }
sudo_rights="$(sudo -l -U "$TARGET_USER")"
grep -qE '\(ALL(:ALL)?\) (NOPASSWD: )?ALL' <<<"$sudo_rights" || {
  echo "Refusing: $TARGET_USER has no full sudo rights." >&2; exit 1; }
grep -qE '^\s*Include\s+/etc/ssh/sshd_config\.d/\*\.conf' /etc/ssh/sshd_config || {
  echo "Refusing: sshd_config does not Include sshd_config.d/*.conf, so $CONF would be ignored." >&2; exit 1; }

# 00- so it is read before cloud-init's 50-cloud-init.conf (first value wins for most keywords).
{
  echo "# Managed by harden-vps: key-only logins, no root"
  echo "PermitRootLogin no"
  echo "PasswordAuthentication no"
  echo "KbdInteractiveAuthentication no"
  echo "PubkeyAuthentication yes"
  echo "X11Forwarding no"
  if [[ -n "$ALLOW_USERS" ]]; then echo "AllowUsers $ALLOW_USERS"; fi
} >"$CONF.new"
chmod 644 "$CONF.new"
mv -f "$CONF.new" "$CONF"

if ! sshd -t; then
  echo "sshd -t failed; removing $CONF so nothing changes." >&2
  rm -f "$CONF"; exit 1
fi

# Debian/Ubuntu call the unit "ssh", RHEL/Fedora "sshd". Reload keeps open sessions alive.
# With socket activation (Ubuntu 22.10+) the service may be idle; new connections read the new config anyway.
if systemctl list-unit-files ssh.service >/dev/null 2>&1; then SVC=ssh; else SVC=sshd; fi
if systemctl is-active -q "$SVC"; then systemctl reload "$SVC"; fi

echo "--- effective sshd settings"
eff="$(sshd -T)"
grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|allowusers) ' <<<"$eff"
for want in "permitrootlogin no" "passwordauthentication no" "kbdinteractiveauthentication no" "pubkeyauthentication yes"; do
  grep -qix "$want" <<<"$eff" || { echo "MISMATCH: expected '$want'. Check for Match blocks or other drop-ins." >&2; exit 1; }
done

if [[ "$LOCK_ROOT" == yes ]]; then passwd -l root; fi
passwd -S root
echo "Done. Keep this session open until a NEW session as $TARGET_USER works."
echo "Rollback: rm $CONF && sshd -t && systemctl reload $SVC"
