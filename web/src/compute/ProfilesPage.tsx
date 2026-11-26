import { type Compute, type ExecutionProfile, deleteExecutionProfile, getExecutionProfile, listComputes, listExecutionProfiles } from "../api";
import { label, resolve, summary } from "../environments/fields";
import { EMPTY_PROFILE, profileFromItem } from "./fields";
import { type Kind, ManagedItem, ManagedList } from "./Managed";
import { ProfileForm } from "./ProfileForm";

// The Profiles pages (#408; ui-spec §4.8.1): what a run asks for on a compute.

const KIND: Kind<ExecutionProfile, Compute[]> = {
  path: "/profiles",
  noun: "profile",
  nounPlural: "profiles",
  title: "Profiles",
  newLabel: "New profile",
  sub: "What a run asks for on a compute: partition, memory, time and GPU · a pipeline lists the profiles it runs with",
  deleteNote: "A profile that a catalog entry lists cannot be deleted: remove it from the entry first.",
  emptyHint: "Only the built-in profiles so far. New profile saves the resources a pipeline needs on a compute under a name.",
  icon: "sliders",
  list: (signal) =>
    Promise.all([listExecutionProfiles(signal), listComputes(signal)]).then(([profiles, computes]) => ({ ...profiles, context: computes.items })),
  get: getExecutionProfile,
  remove: deleteExecutionProfile,
  kindHeading: "Compute",
  kindOf: (p, computes) => {
    const c = computes.find((x) => x.name === p.compute);
    return { key: c?.executor ?? "slurm", icon: c?.executor === "local" ? "terminal" : "server", chip: c ? label(c) : p.compute };
  },
  summary: (p, computes, server) => {
    const c = computes.find((x) => x.name === p.compute);
    return c ? summary(resolve(p, c), server?.node ?? "the server", server?.executor ?? "slurm") : `Compute ${p.compute} is not in the list`;
  },
  extra: (p) => {
    const { nextflow, snakemake } = p.engine_profiles;
    return nextflow || snakemake ? `Profiles: ${[nextflow && `Nextflow ${nextflow}`, snakemake && `Snakemake ${snakemake}`].filter(Boolean).join(" · ")}` : null;
  },
  unusable: (p, computes) => {
    const c = computes.find((x) => x.name === p.compute);
    if (!c) return `its compute ${p.compute} does not exist`;
    return c.usable ? null : `its compute ${p.compute} is not usable: ${c.unusable_reason}`;
  },
  form: ({ item, duplicate, ...rest }) => (
    <ProfileForm
      initial={{ ...(item ? profileFromItem(item) : EMPTY_PROFILE), ...(duplicate && { name: duplicate.name, ...(duplicate.clearLabel && { label: "" }) }) }}
      {...rest}
    />
  ),
};

export const ProfilesPage = () => <ManagedList kind={KIND} />;
export const ProfileItemPage = ({ name, from }: { name: string | null; from?: string }) => <ManagedItem kind={KIND} name={name} from={from} />;
