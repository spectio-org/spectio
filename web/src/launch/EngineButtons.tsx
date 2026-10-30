import { Button, Group, Text } from "@mantine/core";
import type { ReactNode } from "react";
import { ENGINES, type Engine } from "../api";

const NAMES: Record<Engine, string> = { nextflow: "Nextflow", snakemake: "Snakemake" };

interface Props {
  value: Engine | null;
  onChange: (engine: Engine) => void;
  note: ReactNode;
  error?: string;
}

/** Two native toggle buttons, one pressed at most (Assumption 2; UX-G2-07). The pressed one
 * shows a check mark and a heavier variant, so the state is not shown by colour alone. */
export function EngineButtons({ value, onChange, note, error }: Props) {
  const describedBy = ["engine-note", error ? "engine-error" : ""].filter(Boolean).join(" ");
  return (
    <div>
      <Text id="engine-label" fw={500} size="sm" mb={4}>
        Engine
      </Text>
      <Group role="group" aria-labelledby="engine-label" aria-describedby={describedBy} gap="xs">
        {ENGINES.map((engine) => (
          <Button
            key={engine}
            type="button"
            variant={value === engine ? "light" : "default"}
            aria-pressed={value === engine}
            leftSection={value === engine ? <span aria-hidden="true">✓</span> : null}
            onClick={() => onChange(engine)}
          >
            {NAMES[engine]}
          </Button>
        ))}
        <Text id="engine-note" size="sm" c="dimmed">
          {note}
        </Text>
      </Group>
      {error && (
        <Text id="engine-error" size="sm" c="red" role="alert" mt={4}>
          {error}
        </Text>
      )}
    </div>
  );
}
