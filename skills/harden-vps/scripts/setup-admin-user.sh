#!/usr/bin/env bash
# Phase A of the admin-user setup: create a key-only admin user with sudo.
# Safe to re-run. Changes nothing about sshd or root. Run as root.
#
#   SSH_PUBKEY="ssh-ed25519 AAAA... me@laptop" [TARGET_USER=ubuntu] [SUDO_MODE=vibe|safe] \
#     sudo -E bash setup-admin-user.sh
#
# TARGET_USER defaults to the distro's conventional cloud user (ubuntu, debian, fedora, ...).
set -euo pipefail

[[ $EUID -eq 0 ]] || { echo "Run as root (sudo -E bash $0)." >&2; exit 1; }
# shellcheck disable=SC1091
. /etc/os-release

default_user() {
  case "${ID:-}" in
    ubuntu) echo ubuntu ;; debian) echo debian ;; fedora) echo fedora ;;
    rocky) echo rocky ;; almalinux) echo almalinux ;; centos) echo centos ;;
    amzn) echo ec2-user ;; arch) echo arch ;; *) echo admin ;;
  esac
}

TARGET_USER="${TARGET_USER:-$(default_user)}"
SSH_PUBKEY="${SSH_PUBKEY:?Set SSH_PUBKEY to one or more PUBLIC keys, one per line}"
SUDO_MODE="${SUDO_MODE:-vibe}"

[[ "$TARGET_USER" =~ ^[a-z_][a-z0-9._-]*$ ]] || { echo "Bad user name: $TARGET_USER" >&2; exit 1; }
[[ "$SUDO_MODE" == vibe || "$SUDO_MODE" == safe ]] || { echo "SUDO_MODE must be vibe or safe" >&2; exit 1; }
[[ "$TARGET_USER" != root ]] || { echo "TARGET_USER must not be root" >&2; exit 1; }

# Refuse anything that is not a valid public key (catches pasted private keys and typos).
if grep -q 'PRIVATE KEY' <<<"$SSH_PUBKEY"; then echo "That is a PRIVATE key. Never paste it here." >&2; exit 1; fi
while IFS= read -r key; do
  [[ -n "$key" ]] || continue
  ssh-keygen -l -f /dev/stdin <<<"$key" >/dev/null 2>&1 || { echo "Not a valid public key: ${key:0:40}..." >&2; exit 1; }
done <<<"$SSH_PUBKEY"

# sudo group differs by family: Debian/Ubuntu use "sudo", RHEL/Fedora/Arch use "wheel".
if getent group sudo >/dev/null; then SUDO_GROUP=sudo; else SUDO_GROUP=wheel; fi

# 1. User (existing users keep their shell and password)
if ! id "$TARGET_USER" &>/dev/null; then
  useradd -m -s /bin/bash "$TARGET_USER"
  echo "Created user $TARGET_USER"
  if [[ "$SUDO_MODE" == safe ]]; then
    PW="$(openssl rand -base64 24)"
    { set +x; echo "$TARGET_USER:$PW" | chpasswd; } 2>/dev/null
    echo "SAVE THIS sudo password for $TARGET_USER (shown once): $PW" >&2
    unset PW
  fi
fi
TARGET_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

# 2. Groups. Note: docker group membership is root-equivalent.
usermod -aG "$SUDO_GROUP" "$TARGET_USER"
if getent group docker >/dev/null; then usermod -aG docker "$TARGET_USER"; fi

# 3. Home ownership (some cloud images leave it root-owned)
chown "$TARGET_USER:$TARGET_USER" "$TARGET_HOME"

# 4. authorized_keys: append, never overwrite; refuse symlinks
SSH_DIR="$TARGET_HOME/.ssh"; AK="$SSH_DIR/authorized_keys"
if [[ -L "$SSH_DIR" || -L "$AK" ]]; then echo "Refusing: symlink in $SSH_DIR" >&2; exit 1; fi
install -d -m 700 -o "$TARGET_USER" -g "$TARGET_USER" "$SSH_DIR"
touch "$AK"
while IFS= read -r key; do
  [[ -n "$key" ]] || continue
  grep -qxF "$key" "$AK" || printf '%s\n' "$key" >>"$AK"
done <<<"$SSH_PUBKEY"
chown "$TARGET_USER:$TARGET_USER" "$AK"; chmod 600 "$AK"

# 5. sudo
if [[ "$SUDO_MODE" == vibe ]]; then
  sudo_rights="$(sudo -l -U "$TARGET_USER")"
  if ! grep -q 'NOPASSWD: ALL' <<<"$sudo_rights"; then
    TMP="$(mktemp "/etc/sudoers.d/.90-${TARGET_USER}.XXXXXX")"   # dotfiles are ignored by sudo until renamed
    echo "$TARGET_USER ALL=(ALL) NOPASSWD:ALL" >"$TMP"
    chmod 0440 "$TMP"
    if visudo -c -f "$TMP" >/dev/null; then mv -f "$TMP" "/etc/sudoers.d/90-${TARGET_USER}"; else rm -f "$TMP"; exit 1; fi
  fi
else
  # Safe mode: group membership gives password-prompted sudo, but cloud-init may already grant NOPASSWD.
  if grep -rsqE "^\s*${TARGET_USER}\s.*NOPASSWD" /etc/sudoers.d/; then
    echo "WARNING: a file in /etc/sudoers.d still grants $TARGET_USER NOPASSWD (often 90-cloud-init-users). Remove or edit it for safe mode." >&2
  fi
fi

# Report
echo "--- result"
id "$TARGET_USER"
ls -ld "$SSH_DIR"; ls -l "$AK"; echo "keys: $(grep -c . "$AK")"
sudo -l -U "$TARGET_USER" | sed -n '/may run/,$p'
pw_state="$(passwd -S "$TARGET_USER" | awk '{print $2}')"
echo "password state for $TARGET_USER: $pw_state"
if [[ "$pw_state" != P ]]; then
  echo "NOTE: $TARGET_USER has no usable password, so the provider's VNC/web console cannot log in as it." >&2
  echo "      Set one (passwd $TARGET_USER) if you want a console fallback; sshd will still refuse passwords after Phase B." >&2
fi
echo "NEXT: from a NEW terminal, keep this session open:  ssh $TARGET_USER@<server>  then  sudo whoami  (must print root)"
