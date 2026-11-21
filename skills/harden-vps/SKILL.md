---
name: harden-vps
description: Locks down a Linux server (VPS) so only your own devices can reach it, or checks one you already have. It sets up a key-only admin user, turns off root and password logins, puts the server behind Tailscale and a firewall, and turns on nightly security updates, with a human check before each step that could lock you out. Use when someone says "harden my server," "lock down my VPS," "secure my new server," "is ssh exposed," "set up the firewall," "disable root login," "are security updates on," or "is this server up to date."
---

# Harden VPS (Tailscale-only)

This playbook covers three jobs: a Tailscale and ufw lockdown, a key-only admin user on a fresh server, and moving off an end-of-life release. It runs on Ubuntu and Debian first, with notes for the RHEL family. Use it to build a new server or to audit an existing one.

**Target end state**

| Area | End state |
|---|---|
| Admin user | Distro default name (see table below). Key-only SSH, full sudo, owns its home, `.ssh` 700 and `authorized_keys` 600 |
| Root | `PermitRootLogin no`, password locked |
| sshd | `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes`. Listens on 0.0.0.0, but the firewall blocks it publicly |
| Network | Inbound allowed only on `tailscale0`, `lo` and 41641/udp, over IPv4 and IPv6. No public 22 |
| Boot | Firewall, tailscaled and ssh are enabled. The Tailscale node key doesn't expire |
| Docker | Ports published only on `127.0.0.1` |
| Updates | Nightly security upgrades from a **supported** release. apt updates cleanly. Tailscale updates too |

**Default admin user by distro.** Read `ID` from `/etc/os-release`:

| ID | user | sudo group | ssh unit | firewall | auto-updates |
|---|---|---|---|---|---|
| ubuntu | `ubuntu` | sudo | `ssh` (socket-activated on 22.10+) | ufw | unattended-upgrades |
| debian | `debian` | sudo | `ssh` | ufw (install it) | unattended-upgrades |
| fedora / rocky / almalinux / centos | same as ID | wheel | `sshd` | firewalld | dnf-automatic |
| amzn | `ec2-user` | wheel | `sshd` | firewalld | dnf-automatic |

If the provider already created that user, reuse it rather than making a second admin. The rest of this file uses `$ADMIN` for the user.

## Golden rules (each one exists because of a lockout risk)

1. **Never run `ufw disable` or `ufw reset`, and never remove or loosen the tailscale0 rule, even briefly while debugging.** Many VPS providers have no external firewall, so ufw is the only thing keeping public ssh closed. Inspect with read-only commands first (`tailscale status`, `sudo ufw status verbose`, `sudo ss -tulnp`). If a change is needed, add one narrow rule.
2. **Two phases with a human check in between.** Never add a key and disable root/password login in the same run. A typo in the key, wrong permissions or the wrong user would lock everyone out. The same goes for the firewall: allow Tailscale and prove it works before denying everything else.
3. **Keep the current session open** until a *new* session works.
4. **Keep a way back in.** Have a provider snapshot, and a console login that works. The VNC or web console uses a local password, not sshd, so it only helps if `$ADMIN` has a password (`passwd -S $ADMIN` shows `P`). With every password locked, the only recovery is provider rescue mode. Recommendation: give `$ADMIN` a strong password even in vibe mode. sshd still refuses passwords.
5. **Run disruptive jobs detached** (`screen -dmS … -L -Logfile …` or `systemd-run --unit=…`). Restarting tailscaled or upgrading the release cuts your own connection.
6. **Never reboot without the user's explicit "reboot".** Re-run the audit first.
7. **Agent limits.** Claude can't log in to the provider panel, the VNC console or the Tailscale admin console for the user. Tell the user exactly what to click there instead.

## Step 0: Audit (read-only, always first)

```bash
. /etc/os-release; echo "$PRETTY_NAME"; uname -r; uptime
# Network exposure
sudo ufw status verbose; grep ^IPV6 /etc/default/ufw
sudo ss -tulnp | grep -vE '127\.0\.0\.|\[::1\]|127\.0\.0\.5[34]'   # 0.0.0.0/[::] listeners: reachable from the whole tailnet
sudo docker ps --format '{{.Names}}\t{{.Ports}}' 2>/dev/null       # 0.0.0.0:PORT bypasses ufw entirely
tailscale status --self --peers=false; tailscale funnel status; tailscale serve status
tailscale debug prefs | grep -iE '"(ShieldsUp|RunSSH|WantRunning|AdvertiseRoutes|AutoUpdate)"'
tailscale status --json | python3 -c "import sys,json;print('node key expiry:',json.load(sys.stdin)['Self'].get('KeyExpiry'))"
# Accounts and root
awk -F: '$3==0{print "uid0:",$1}' /etc/passwd
for u in root "$ADMIN"; do sudo passwd -S "$u"; done
sudo ls -la /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>&1
getent group sudo wheel docker
sudo grep -rE 'NOPASSWD' /etc/sudoers /etc/sudoers.d/
sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|allowusers|x11forwarding) '
ls /etc/ssh/sshd_config.d/
# Updates
systemctl is-enabled ufw tailscaled ssh.socket ssh unattended-upgrades apt-daily.timer apt-daily-upgrade.timer fail2ban 2>&1
cat /etc/apt/apt.conf.d/20auto-upgrades
sudo unattended-upgrade --dry-run -d 2>&1 | grep -E 'Allowed origins|No packages|pkgs that look'
sudo apt-get update 2>&1 | grep -E '^(W|E):'; apt list --upgradable 2>/dev/null | tail -n +2
[ -f /var/run/reboot-required ] && cat /var/run/reboot-required.pkgs
```

Report results in plain language, one line per area of the end-state table (pass, gap or risk). Holes that have come up before:
- **Cloud-init re-enables passwords.** `50-cloud-init.conf` sets `PasswordAuthentication yes`. sshd keeps the first value it reads, and drop-ins load in alphabetical order, so the hardening file has to be `00-…`. Editing `sshd_config` alone does nothing.
- **Cloud-init grants NOPASSWD sudo** through `/etc/sudoers.d/90-cloud-init-users`. That's fine in vibe mode, but in safe mode it has to go.
- **The root password may be set by the provider**, and `PermitRootLogin yes` is common on VPS images.
- **"No packages found" doesn't mean the box is current.** On an EOL release the `-security` index stops changing. Check `grep ^Date /var/lib/apt/lists/*_dists_$(lsb_release -cs)-security_InRelease`. If it's months old, go to Step 7.
- **Mixed releases.** If the codenames in `sources.list.d` don't match `lsb_release -cs`, the pending "upgrades" belong to another release. Don't `apt upgrade`. Fix the sources first (Step 6).
- **Tailscale doesn't update.** It's a third-party origin, so unattended-upgrades skips it. A `tailscale.list` that holds only a comment means it has never updated at all.
- **Node key expiry.** When the key expires the box drops off the tailnet. The user disables it in the Tailscale admin console (Machines → ⋯ → Disable key expiry).
- **Docker group membership is root-equivalent.** List who's in it.
- **Tailnet services.** Anything bound to 0.0.0.0, such as a dev server or a database without a password, is open to every device on the tailnet. If any of those devices is shared or untrusted, restrict access with Tailscale ACLs or bind the service to 127.0.0.1.

## Fresh-server order

Password-guessing bots hit a new VPS's public ssh within minutes, so close that window quickly:

1. **Admin user** (Step 1, Phase A)
2. Human checkpoint
3. **Tailscale** (Step 2), then ssh over the Tailscale IP
4. **Firewall** (Step 3), then confirm the public IP times out
5. **SSH and root lockdown** (Step 4, Phase B)
6. **Updates** (Step 5)

On an existing server, run the audit and fix only the gaps it finds.

## Step 1: Admin user (Phase A, safe to re-run)

Ask the user for their **public** key (`cat ~/.ssh/id_ed25519.pub` on the laptop) and a sudo mode:
- **vibe:** NOPASSWD sudo, which agents need.
- **safe:** sudo asks for a password.

Then run the bundled script. It creates the user, adds them to the sudo or wheel group (and docker if it exists), fixes home ownership, appends the keys (it refuses private keys, invalid keys and symlinks) and writes a sudoers file checked with visudo:

```bash
SSH_PUBKEY='ssh-ed25519 AAAA… me@laptop' SUDO_MODE=vibe sudo -E bash <skill-dir>/scripts/setup-admin-user.sh
# TARGET_USER defaults to the distro's user (ubuntu on Ubuntu). Override with TARGET_USER=name.
```

On a fresh VPS both `authorized_keys` files are often empty, because the provider gave root a password. So always add the operator's key explicitly instead of copying root's keys.

**Checkpoint (the human does this).** Keep the root session open. From a new laptop terminal, run `ssh $ADMIN@<ip>` and then `sudo whoami`, which must print `root`. An agent can pre-check with `su - $ADMIN -c 'sudo -n whoami'`.

## Step 2: Tailscale (install, connect, survive reboots)

```bash
curl -fsSL https://tailscale.com/install.sh | sh      # adds the official repo
sudo systemctl enable --now tailscaled
sudo tailscale up                                     # the user opens the auth URL
sudo tailscale set --auto-update                      # Tailscale updates itself; unattended-upgrades won't
tailscale ip -4
```
- Keep `RunSSH` off. This setup uses plain sshd over the tailnet.
- Have the user disable key expiry for this machine in the admin console.
- **If ssh to the 100.x address times out**, check the laptop first: `tailscale ping <host>`, and `route -n get <100.x>` (macOS) should show a `utun` interface. A consumer VPN like NordVPN takes over the 100.64/10 route; disconnect it. That is a far more common cause than an attack.
- Don't bind sshd to the Tailscale IP with `ListenAddress`. sshd can start before tailscale0 exists, and then it doesn't listen at all after a reboot. Let the firewall do the filtering.

## Step 3: Firewall: Tailscale only

Only do this once ssh over Tailscale works. **Ubuntu/Debian (ufw):**
```bash
sudo sed -i 's/^IPV6=.*/IPV6=yes/' /etc/default/ufw
sudo ufw allow in on tailscale0 comment 'Tailscale network'
sudo ufw allow 41641/udp comment 'Tailscale WireGuard'   # direct peer connections instead of DERP relays
sudo ufw allow in on lo comment 'loopback'
sudo ufw default deny incoming; sudo ufw default allow outgoing; sudo ufw default deny routed
sudo ufw --force enable; sudo systemctl enable ufw
sudo ufw status verbose
```
Don't add `allow OpenSSH` or `allow 22`. Public ssh stays closed on purpose. (Generic guides add it, but that's for servers without Tailscale.)

**RHEL family (firewalld):** `firewall-cmd --permanent --zone=trusted --add-interface=tailscale0`, then `--zone=public --remove-service=ssh` and `--add-port=41641/udp`, then `--reload`.

**Verify from outside** (the user runs these on the laptop):
- `ssh -o ConnectTimeout=8 $ADMIN@<PUBLIC_IP>` should time out.
- `ssh $ADMIN@<TAILSCALE_IP>` should work.

For Docker, publish ports as `127.0.0.1:PORT:PORT`, because 0.0.0.0 bypasses ufw. To expose a web app, prefer `tailscale serve` (tailnet only). Open a narrow public port only when the user explicitly asks for one.

## Step 4: SSH and root lockdown (Phase B, only after the checkpoint passed)

```bash
CONFIRM_KEY_LOGIN=yes TARGET_USER=$ADMIN ALLOW_USERS=$ADMIN sudo -E bash <skill-dir>/scripts/lockdown-ssh.sh
```

The script first checks that `$ADMIN` has a valid key and full sudo, and that `sshd_config` includes `sshd_config.d`. Then it:
1. Writes `/etc/ssh/sshd_config.d/00-hardening.conf`. That sets `PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes` and `X11Forwarding no`, plus `AllowUsers` if you pass `ALLOW_USERS`.
2. Runs `sshd -t`, and rolls back if it fails.
3. Reloads `ssh` or `sshd`. Open sessions survive.
4. Checks `sshd -T` for the effective values.
5. Locks the root password (`LOCK_ROOT=no` skips this).

Before it locks root, remind the user about the console fallback (golden rule 4).

**Final checks from the laptop, over the Tailscale IP:**
- `ssh $ADMIN@ts-ip` works.
- `ssh root@ts-ip` is refused with "Permission denied (publickey)".
- `ssh -o PubkeyAuthentication=no $ADMIN@ts-ip` is refused, with no password prompt.

On the server, `journalctl -u ssh --since "10 min ago" | grep -E 'Accepted|Failed'` should show only key logins. `who` still lists sessions opened before the reload, which is expected.

**Rollback** from the open session or rescue mode: `rm /etc/ssh/sshd_config.d/00-hardening.conf && sshd -t && systemctl reload ssh`, plus `passwd root` if needed.

Changing the ssh port on socket-activated Ubuntu also means editing `ssh.socket` (`systemctl edit ssh.socket`), not just `Port`. Behind Tailscale there's no reason to change it.

## fail2ban: decide, don't reflexively install

fail2ban bans IPs that keep failing logins. After Step 3, ufw drops every public packet to port 22 before sshd sees it, so there's nothing to ban, and tailnet peers are trusted devices. **Skip it on a Tailscale-only box.** It's worth installing (`apt install fail2ban`; the default `sshd` jail plus `banaction = ufw` in `jail.local`) when:
- public ssh stays open (no Tailscale), or the box sits exposed for a while before Step 3, or
- a public service with a login gets opened (a web admin page, mail).

Either way, key-only sshd (Step 4) is the real defense, and fail2ban only cuts down log noise.

## Step 5: Nightly security updates

```bash
sudo apt-get install -y unattended-upgrades
sudo dpkg-reconfigure -f noninteractive unattended-upgrades
cat /etc/apt/apt.conf.d/20auto-upgrades     # Update-Package-Lists "1"; Unattended-Upgrade "1"
systemctl is-enabled apt-daily.timer apt-daily-upgrade.timer unattended-upgrades
sudo unattended-upgrade --dry-run -d 2>&1 | grep 'Allowed origins'   # must name the CURRENT codename-security
```
- `Automatic-Reboot` is off by default. Ask the user. Off is the usual choice on a server that runs agents or tmux sessions, because an automatic reboot kills them. Reboot by hand when `/var/run/reboot-required` appears; the login banner also says "System restart required".
- `needrestart` (`$nrconf{restart} = 'a'`) restarts services after library updates. Kernel fixes still need a reboot.
- Third-party repos (Tailscale, Docker, pgdg…) aren't upgraded unattended unless their origins are added. Cover Tailscale with `tailscale set --auto-update`. For other repos, either add their origins or rely on manual `apt upgrade`.
- RHEL family: `dnf install dnf-automatic`, set `upgrade_type = security` and `apply_updates = yes`, then `systemctl enable --now dnf-automatic.timer`.
- Separate tool updaters, such as a nightly timer that updates dev tools, do **not** update OS packages.

## Step 6: apt hygiene (sources, keys, third-party repos)

- Back up first: `sudo mkdir -p /root/apt-sources-backup-<date>`, then `sudo cp -a /etc/apt/sources.list.d/. /etc/apt/keyrings …`.
- `ubuntu.sources` should list only the running codename: `<cn> <cn>-updates <cn>-backports`, plus `<cn>-security`. Disable leftovers with `Enabled: no` instead of deleting them.
- **Tailscale repo:**
  1. Fetch the key: `curl -fsSL https://pkgs.tailscale.com/stable/ubuntu/<cn>.noarmor.gpg | sudo tee /usr/share/keyrings/tailscale-archive-keyring.gpg`.
  2. Write a deb822 `tailscale.sources` for that repo.
  3. Upgrade Tailscale detached: `sudo systemd-run --unit=ts-upgrade --collect -E DEBIAN_FRONTEND=noninteractive apt-get install -y --only-upgrade tailscale`.
- **`NO_PUBKEY` errors:** fetch the vendor's current key and check that its fingerprint ends in the missing ID (`gpg --show-keys`). If some suites are still signed with the old key, concatenate the old and new binary keyrings into one file.
- Check that a vendor serves your codename before switching (`curl -s -o /dev/null -w '%{http_code}' …/dists/<cn>/InRelease`). pgdg uses `<cn>-pgdg`.
- Prefer deb822 `.sources` files. Release upgrades can't migrate `.list` files and disable them. The goal is `apt-get update` with no `W:` or `E:` lines.

## Step 7: EOL release → `do-release-upgrade`

1. The user takes a provider snapshot and confirms console login. Wait for their "go".
2. Finish Step 6. Upgrade Tailscale on its own first; that proves you can recover after tailscaled restarts.
3. Back up data. For Postgres: `sudo -u postgres pg_dumpall -f /var/lib/postgresql/dumpall-<date>.sql`, then gzip it and check that it contains `COPY` lines. Record manually installed packages: `zgrep -h '^Commandline:' /var/log/apt/history.log*`.
4. The upgrader refuses to start while updates are pending, and third-party repos that already offer next-release builds count as pending. Comment them out temporarily; packages from disabled repos are kept.
5. Run it detached: `sudo screen -dmS upgrade -L -Logfile /root/release-upgrade.log do-release-upgrade -f DistUpgradeViewNonInteractive --allow-third-party`. In this mode it won't reboot by itself.
6. **Before rebooting:**
   - Re-run the Step 0 audit
   - `sshd -t`, `dpkg --audit`, `systemctl --failed`
   - `GRUB_DEFAULT`
   - Every manually installed package. The upgrader can remove some of them, such as `-dev` library packages.
7. Re-enable third-party repos as `.sources` for the new codename and delete the `*.list.disabled` files. Drop repos pinned to EOL versions; For example, replace NodeSource node_18 with the distro nodejs.
8. Save a memory note with the post-reboot TODO and the session ID (`claude --resume <id>` from `~`). After the user says "reboot", run `sudo shutdown -r +1`. If the box isn't back on Tailscale within about 5 minutes, restore the snapshot.
9. **After the reboot:**
   - `uname -r`, then the audit again
   - Databases and containers. `--rm` containers don't come back.
   - Purge the old kernel
   - Fix obsolete-conffile conflicts, e.g. a duplicate logrotate entry from `/etc/logrotate.d/cloud-init`
   - Confirm Allowed origins now name the new codename

## "Do I need to worry about CVE X tonight?"

1. Confirm the lockdown with the audit. If only 41641/udp (tailscaled) is reachable from the internet, remote attack surface is minimal.
2. Still name the two paths the firewall doesn't cover:
   - untrusted input the box fetches or parses (git clone, npm install, downloads, pages agents read, email)
   - a compromised device on the tailnet
3. Ask for the CVE source and map it to packages. Don't guess.
4. Patch: `sudo apt-get update && sudo unattended-upgrade -d`, or `apt-get upgrade` if the sources are clean. On an EOL release no fix is coming, so say that plainly and go to Step 7.
