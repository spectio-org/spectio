import { type Compute, listComputes, getCompute, deleteCompute } from "../api";
import { summary } from "../environments/fields";
import { ComputeForm } from "./ComputeForm";
import { EMPTY_COMPUTE, computeFromItem } from "./fields";
import { type Kind, ManagedItem, ManagedList } from "./Managed";

// The Compute pages (#408; ui-spec §4.8.1): the backends a run goes to.

const KIND: Kind<Compute, null> = {
  path: "/compute",
  noun: "compute",
  nounPlural: "computes",
  title: "Compute",
  newLabel: "New compute",
  sub: "Where the tasks of a run go: the executor, its account and the software it has",
  deleteNote: "A compute that a profile uses cannot be deleted: delete or move its profiles first.",
  emptyHint: "Only the built-in computes so far. New compute saves a backend, its SLURM account and its software under a name; Profiles then say what a run asks for on it.",
  icon: "server",
  list: (signal) => listComputes(signal).then((l) => ({ ...l, context: null })),
  get: getCompute,
  remove: deleteCompute,
  kindHeading: "Kind",
  kindOf: (c) => (c.executor === "slurm" ? { key: "slurm", icon: "server", chip: "SLURM" } : { key: "local", icon: "terminal", chip: "Local" }),
  // The account and the caps are the compute's; the partition and the rest are a profile's
  summary: (c, _, server) =>
    summary(
      { executor: c.executor, local: c.local, software: c.software, slurm: c.slurm && { partition: null, account: c.slurm.account, time_min: null, mem_mib: null } },
      server?.node ?? "the server",
      server?.executor ?? "slurm",
    ),
  extra: (c) => (c.apptainer_args ? `Apptainer arguments: ${c.apptainer_args}` : null),
  unusable: (c) => (c.usable ? null : c.unusable_reason),
  form: ({ item, duplicate, ...rest }) => (
    <ComputeForm
      initial={{ ...(item ? computeFromItem(item) : EMPTY_COMPUTE), ...(duplicate && { name: duplicate.name, ...(duplicate.clearLabel && { label: "" }) }) }}
      {...rest}
    />
  ),
};

export const ComputePage = () => <ManagedList kind={KIND} />;
export const ComputeItemPage = ({ name, from }: { name: string | null; from?: string }) => <ManagedItem kind={KIND} name={name} from={from} />;
