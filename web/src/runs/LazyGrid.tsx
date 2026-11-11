import { Button } from "@mantine/core";
import { Component, type ReactNode, Suspense, lazy, useState } from "react";
import type GridOf from "./DataGrid";
import type { GridProps } from "./DataGrid";

// AG Grid's lazy chunk (ui-spec §4.13), declared once for every table (CR-P3FU101A-05). A chunk
// that fails to load leaves the page as it is: the table's place says so, with Retry, which asks
// for the chunk again (CR-P3FU101A-07).

const loadGrid = () => lazy(() => import("./DataGrid")) as unknown as typeof GridOf;

class Fallback extends Component<{ retry: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    if (!this.state.failed) return this.props.children;
    const retry = () => {
      this.setState({ failed: false });
      this.props.retry();
    };
    return (
      <div role="alert" className="sp-empty">
        <p>The table could not be loaded.</p>
        <Button variant="default" onClick={retry}>
          Retry
        </Button>
      </div>
    );
  }
}

/** The data grid, loaded on first use; `loadingLine` is the line shown meanwhile. */
export function LazyGrid<T>({ loadingLine, ...props }: GridProps<T> & { loadingLine: string }) {
  const [Grid, setGrid] = useState(loadGrid);
  return (
    <Fallback retry={() => setGrid(loadGrid)}>
      <Suspense fallback={<p className="sp-muted">{loadingLine}</p>}>
        <Grid<T> {...props} />
      </Suspense>
    </Fallback>
  );
}
