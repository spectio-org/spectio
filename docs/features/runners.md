# Runners

A runner starts the engine and reports back to the server. In 0.0.1 the runner is built into the server: there is no separate program to install.

- **SLURM, through a login node.** The server runs on a login node as you. Each run's engine (its head) starts in its own tmux session there, never in `sbatch`; the engine sends its tasks to SLURM through its own executor. Where a run's tasks go (partition and account) is set by an [environment](../usage/environments.md). Per job, the run page shows CPU and memory use from `sacct` once the job has ended ([details](../usage/states-outputs-efficiency.md)).
- **One machine.** `spectio init --local` sets Spectio up on one Linux machine with no scheduler, and the engines use their local executors.
- **On a shared host the server listens on a Unix socket,** never on a TCP port, and you reach it through an SSH tunnel ([why](../usage/open-from-your-laptop.md#why-a-socket-on-a-cluster)).

Not in 0.0.1, planned for later versions:

- **Kubernetes,** with queues through Kueue.
- **A shared server with remote runners** that make only outgoing HTTPS calls.
- **Full scheduler monitoring:** why jobs wait, partition capacity, checks of walltime against partition limits.
- **Other schedulers:** LSF, PBS, SGE.

See the [roadmap](../roadmap/index.md).

![The Environments page: the built-in and two environments of your own](../assets/shots/app-environments_light.webp#only-light)
![The Environments page: the built-in and two environments of your own](../assets/shots/app-environments_dark.webp#only-dark)
