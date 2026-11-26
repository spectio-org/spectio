import { Badge, Button, Checkbox, MultiSelect, Select, TextInput } from "@mantine/core";
import { useState } from "react";
import type { ClusterFacts } from "../api";
import { type NodeGroup, type Need, NO_NEED, constraintOf, featureUnion, fittingGroups, gpuTypes, gresOf } from "./placement";

// The placement picker (#401; ui-spec §4.8.1): partition, constraint and GPU by need. The
// filters narrow the partitions of `GET /cluster/facts`; choosing one fills the form's three text
// fields, which stay editable and stay the source of truth. Native controls only, all labelled.

export interface Placement {
  partition: string;
  constraint: string | null;
  gres: string | null;
}

const gib = (mib: number) => `${Math.round(mib / 1024)} GiB`;
const hoursOf = (min: number | null) => (min === null ? "no time limit" : min % 60 ? `${min} min` : `${min / 60} h`);
const gpuWords = (g: NodeGroup) => g.gpus.map((x) => `${x.count} × ${x.type ?? "GPU"}`).join(", ");
const groupWords = (g: NodeGroup) =>
  [`${g.idle} of ${g.nodes} nodes idle`, `${g.cpus} CPUs`, gib(g.mem_mib), g.features.join(", "), gpuWords(g)].filter(Boolean).join(" · ");

interface Props {
  facts: ClusterFacts;
  /** The form's partition now, to mark the chosen one. */
  partition: string;
  onPick: (placement: Placement) => void;
}

export function PlacementPicker({ facts, partition, onPick }: Props) {
  const [need, setNeed] = useState<Need>(NO_NEED);
  const [showBlocked, setShowBlocked] = useState(false);
  const types = gpuTypes(facts);
  const rows = facts.partitions
    .map((p) => ({ p, groups: fittingGroups(p, need) }))
    .filter(({ p, groups }) => groups.length > 0 && (p.allowed || showBlocked));
  const blocked = facts.partitions.filter((p) => !p.allowed).length;
  return (
    <section className="sp-placement" aria-label="Find a partition by need">
      <h3>Find a partition by need</h3>
      <div className="sp-env-pair">
        <Select
          label="GPU"
          allowDeselect={false}
          data={[{ value: "none", label: "No GPU needed" }, { value: "any", label: "Any GPU" }, ...types.map((t) => ({ value: t, label: t }))]}
          value={need.gpu}
          onChange={(v) => setNeed({ ...need, gpu: v ?? "none" })}
          w={180}
        />
        <TextInput
          label="Memory per node ≥ GB"
          inputMode="decimal"
          value={need.memGb}
          onChange={(e) => setNeed({ ...need, memGb: e.currentTarget.value })}
          w={180}
        />
        <TextInput
          label="Time ≥ h"
          inputMode="decimal"
          value={need.hours}
          onChange={(e) => setNeed({ ...need, hours: e.currentTarget.value })}
          w={120}
        />
      </div>
      <MultiSelect
        label="CPU features"
        data={featureUnion(facts)}
        value={need.features}
        onChange={(features) => setNeed({ ...need, features })}
        placeholder={need.features.length ? undefined : "Any"}
        clearable
      />
      {blocked > 0 && (
        <Checkbox
          label="Show partitions your accounts can't use"
          checked={showBlocked}
          onChange={(e) => setShowBlocked(e.currentTarget.checked)}
        />
      )}
      <p className="sp-env-hint" role="status">
        {rows.length ? `${rows.length} of ${facts.partitions.length} partitions fit` : "No partition fits: relax a filter"}
      </p>
      <ul className="sp-placement-list" aria-label="Partitions that fit">
        {rows.map(({ p, groups }) => (
          <li key={p.name} className="sp-placement-row" data-chosen={p.name === partition ? true : undefined}>
            <div className="sp-env-pair">
              <Button
                variant={p.name === partition ? "filled" : "default"}
                size="xs"
                aria-pressed={p.name === partition}
                aria-label={`Use partition ${p.name}`}
                onClick={() => onPick({ partition: p.name, constraint: constraintOf(need), gres: gresOf(need) })}
              >
                {p.name}
              </Button>
              {p.default && <Badge variant="light">Default</Badge>}
              {!p.allowed && <Badge variant="light" color="gray">Not for your accounts</Badge>}
              <span className="sp-env-hint">max time {hoursOf(p.max_time_min)}</span>
            </div>
            <ul className="sp-placement-groups">
              {groups.map((g, i) => (
                <li key={i} className="sp-env-hint">{groupWords(g)}</li>
              ))}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  );
}
