#!/usr/bin/env bash
# A real one-node Slurm with accounting, native in a Claude Code cloud session (FU-P3-66, inbox #120 (a)).
#
#   bash dev/slurm/native.sh up       install the packages if missing, configure, start, wait until the node
#                                     is idle and the cluster `local` is in the accounting database
#   bash dev/slurm/native.sh down     stop the daemons; the packages and the configs stay
#   bash dev/slurm/native.sh status   which daemons run, the node and the cluster
#
# sind (cluster.sh) needs Docker on cgroup v2 and cloud sessions are cgroup v1 (spike D2), so this installs
# Slurm, slurmdbd, MariaDB and munge from the Ubuntu 24.04 packages (Slurm 23.11.4, MariaDB 10.11) into the
# container itself, as root. It is for a throwaway container only: it refuses to run unless it is root, and
# refuses when a slurm.conf or slurmdbd.conf it did not write (no marker line) is there, before any apt,
# daemon start or file write. The database password is generated per install into a root-only file; it is
# never printed, never on a command line and never in a shell variable. MariaDB listens on 127.0.0.1 only.
# NATIVE_SLURM_ETC (default /etc/slurm) is for the tests (tests/slurm/test_native.py).
set -euo pipefail
ETC=${NATIVE_SLURM_ETC:-/etc/slurm}
[[ $ETC =~ ^/[A-Za-z0-9._/-]+$ ]] || { echo "NATIVE_SLURM_ETC must be a plain absolute path: $ETC" >&2; exit 1; }
[ "$ETC" = /etc/slurm ] || export SLURM_CONF=$ETC/slurm.conf
MARK='# Written by dev/slurm/native.sh'
PASS=$ETC/native-db.pass
LOGS=/var/log/slurm
PACKAGES=(slurm-wlm slurmdbd mariadb-server munge)

log() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }
die() { echo "native.sh: $*" >&2; exit 1; }

# Builtins and `id` only: nothing runs, starts or is written before these pass.
guard() {
  [ "$(id -u)" = 0 ] || die "run it as root, in a throwaway container"
  local f first
  for f in "$ETC/slurm.conf" "$ETC/slurmdbd.conf"; do
    [ -e "$f" ] || continue
    first=
    IFS= read -r first <"$f" || true
    [[ $first == "$MARK"* ]] || die "$f exists and was not written by dev/slurm/native.sh; leaving this Slurm alone"
  done
}

wait_for() { # what command...
  local what=$1 i
  shift
  for ((i = 0; i < 60; i++)); do "$@" && return 0; sleep 1; done
  die "timed out waiting for $what"
}
running() { pgrep -x "$1" >/dev/null; }
stopped() { ! running "$1"; }
db_up() { mysqladmin --protocol=socket ping >/dev/null 2>&1; }
dbd_up() { sacctmgr -n list cluster >/dev/null 2>&1; }
has_cluster() { sacctmgr -n -P list cluster format=cluster | grep -qx local; }
node_idle() { [ "$(sinfo -h -n "$NODE" -o %t)" = idle ]; }

install_packages() {
  local p missing=()
  for p in "${PACKAGES[@]}"; do
    # shellcheck disable=SC2016 # a dpkg-query field, not a shell expansion
    [ "$(dpkg-query -W -f='${db:Status-Status}' "$p" 2>/dev/null)" = installed ] || missing+=("$p")
  done
  [ ${#missing[@]} = 0 ] && return 0
  log "installing ${missing[*]}"
  DEBIAN_FRONTEND=noninteractive apt-get update -q
  DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends "${missing[@]}"
}

start_munge() {
  running munged && return 0
  [ -s /etc/munge/munge.key ] || runuser -u munge -- mungekey -c
  install -d -o munge -g munge -m 755 /run/munge
  runuser -u munge -- munged --force # --force: a socket left by a stopped munged
}

start_db() {
  db_up && return 0
  install -d -o mysql -g mysql -m 755 /run/mysqld
  setsid nohup mysqld_safe --bind-address=127.0.0.1 >>"$LOGS/native-mariadb.log" 2>&1 </dev/null &
  wait_for MariaDB db_up
}

# The password goes from its file to the database and to slurmdbd.conf through sed, never through a
# variable or an argument, so neither `ps` nor `set -x` shows it.
db_user() {
  [ -s "$PASS" ] || (umask 077 && head -c 48 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' >"$PASS")
  sed "s/.*/CREATE USER IF NOT EXISTS 'slurm'@'localhost'; ALTER USER 'slurm'@'localhost' IDENTIFIED BY '&'; \
GRANT ALL ON slurm_acct_db.* TO 'slurm'@'localhost';/" "$PASS" | mysql --protocol=socket
}

configure() {
  local mem_kib
  mem_kib=$(sed -n 's/^MemTotal: *\([0-9]*\) kB$/\1/p' /proc/meminfo)
  CPUS=$(nproc)
  MEM=$((mem_kib / 1024 - 512))
  install -d -m 755 "$ETC" /var/spool/slurmd
  install -d -o slurm -g slurm -m 755 /var/spool/slurmctld "$LOGS"
  install -m 600 -o slurm -g slurm /dev/null "$ETC/slurmdbd.conf"
  {
    cat <<EOF
$MARK: a dev-only one-node Slurm (FU-P3-66); never on a site.
AuthType=auth/munge
DbdHost=localhost
SlurmUser=slurm
StorageType=accounting_storage/mysql
StorageHost=localhost
StorageUser=slurm
StorageLoc=slurm_acct_db
LogFile=$LOGS/slurmdbd.log
PidFile=/run/slurmdbd.pid
EOF
    sed 's/^/StoragePass=/' "$PASS"
  } >"$ETC/slurmdbd.conf"
  install -m 644 /dev/null "$ETC/slurm.conf"
  cat >"$ETC/slurm.conf" <<EOF
$MARK: a dev-only one-node Slurm (FU-P3-66); never on a site.
ClusterName=local
SlurmctldHost=$NODE
AuthType=auth/munge
SlurmUser=slurm
StateSaveLocation=/var/spool/slurmctld
SlurmdSpoolDir=/var/spool/slurmd
ProctrackType=proctrack/linuxproc
TaskPlugin=task/none
JobAcctGatherType=jobacct_gather/linux
JobAcctGatherFrequency=5
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageHost=localhost
SelectType=select/cons_tres
SelectTypeParameters=CR_Core_Memory
SlurmctldLogFile=$LOGS/slurmctld.log
SlurmdLogFile=$LOGS/slurmd.log
NodeName=$NODE CPUs=$CPUS RealMemory=$MEM State=UNKNOWN
PartitionName=debug Nodes=$NODE Default=YES MaxTime=INFINITE State=UP
EOF
}

start_daemon() { # slurmdbd|slurmctld|slurmd; each forks into the background itself
  running "$1" && return 0
  rm -f "/run/$1.pid" # a stale one from a stopped container
  "$1"
}

up() {
  local t=$SECONDS version
  install_packages
  NODE=$(hostname -s)
  start_munge
  start_db
  db_user
  configure
  start_daemon slurmdbd
  wait_for slurmdbd dbd_up
  has_cluster || sacctmgr -i add cluster local >/dev/null
  start_daemon slurmctld
  start_daemon slurmd
  wait_for "node $NODE idle" node_idle
  has_cluster || die "the cluster local is not in the accounting database"
  version=$(sinfo -V)
  log "native Slurm ${version##* } up in $((SECONDS - t)) s: cluster local, node $NODE ($CPUS CPUs, $MEM MiB), partition debug"
}

stop_daemon() {
  running "$1" || return 0
  pkill -x "$1"
  wait_for "$1 to stop" stopped "$1"
}

down() {
  local d
  for d in slurmd slurmctld slurmdbd; do stop_daemon "$d"; done
  ! db_up || mysqladmin --protocol=socket shutdown
  stop_daemon munged
  log "native Slurm down; packages and configs kept"
}

status() {
  local d rc=0
  for d in munged slurmdbd slurmctld slurmd; do
    if running "$d"; then echo "$d: running"; else echo "$d: stopped"; rc=1; fi
  done
  if db_up; then echo "mariadb: running"; else echo "mariadb: stopped"; rc=1; fi
  if [ $rc = 0 ]; then
    sinfo -N -o '%N %P %t %c %m'
    sacctmgr -n -P list cluster format=cluster,controlhost
  fi
  return $rc
}

case "${1:-}" in
  up) guard && up ;;
  down) guard && down ;;
  status) status ;;
  *) echo "usage: bash dev/slurm/native.sh up|down|status" >&2; exit 2 ;;
esac
