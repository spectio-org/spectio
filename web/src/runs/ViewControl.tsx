import { ActionIcon, Tooltip } from "@mantine/core";
import { Icon, type IconName } from "../icons";
import { usePhone } from "../shell/layout";

/** A viewer's control as an icon button (ui-spec §12.4, UI-17): lg beside the sm controls, xl
 * (44 px) on the phone, named by `label`, with the same words in a tooltip on hover and focus.
 * `pressed` makes it a toggle. */
export function ViewControl({ label, icon, pressed, onClick }: { label: string; icon: IconName; pressed?: boolean; onClick: () => void }) {
  const phone = usePhone();
  return (
    <Tooltip label={label} events={{ hover: true, focus: true, touch: false }}>
      <ActionIcon variant={pressed ? "light" : "default"} size={phone ? "xl" : "lg"} aria-label={label} aria-pressed={pressed} onClick={onClick}>
        <Icon name={icon} size="button" />
      </ActionIcon>
    </Tooltip>
  );
}
