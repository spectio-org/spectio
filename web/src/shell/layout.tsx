import { Link } from "@tanstack/react-router";
import { type ReactNode, type Ref, createContext, useContext } from "react";
import { createPortal } from "react-dom";
import { ICONS, Icon } from "../icons";

// The shell's layout for the pages (ui-spec §4.11): whether this is the phone, and there the top
// bar's second row (MLiteTopbar `hasTitle`), where a page puts its title (UX-PAR-08).

interface Layout {
  phone: boolean;
  /** The phone top bar's title row, once mounted; null elsewhere. */
  titleRow: HTMLElement | null;
}

export const LayoutContext = createContext<Layout>({ phone: false, titleRow: null });

/** True below 768 px, where the pages show cards instead of tables (UX-PAR-10). */
export const usePhone = () => useContext(LayoutContext).phone;

interface Props {
  title: ReactNode;
  sub?: ReactNode;
  /** A 44 px back link named "Back to <label>". */
  back?: { to: "/" | "/runs"; label: string };
  titleRef?: Ref<HTMLHeadingElement>;
}

/** On the phone, the page's title as the h1 of the top bar's second row, with its subtitle and a
 * back link; the row stays in view while the page scrolls. Elsewhere nothing. */
export function PhoneTitle({ title, sub, back, titleRef }: Props) {
  const { phone, titleRow } = useContext(LayoutContext);
  if (!phone || !titleRow) return null;
  return createPortal(
    <>
      {back && (
        <Link to={back.to} className="sp-key sp-back" aria-label={`Back to ${back.label}`}>
          <Icon path={ICONS.chevronLeft} size={22} stroke={2} />
        </Link>
      )}
      <div className="sp-mtitle-text">
        <h1 ref={titleRef} tabIndex={titleRef ? -1 : undefined} className="sp-page-title">
          {title}
        </h1>
        {sub && <p className="sp-sub sp-page-sub">{sub}</p>}
      </div>
    </>,
    titleRow,
  );
}
