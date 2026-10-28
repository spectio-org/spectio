import { existsSync } from 'node:fs';
import { join } from 'node:path';

const BOARDS = join(__dirname, '..', '..', 'design', 'ui-canvas');

/** screens/<Board>--<project>.png, where <Board> names a board of design/ui-canvas (<Board>.dc.html). */
export function boardShotPath(board: string, project: string): string {
  if (!/^[A-Za-z0-9]+$/.test(board) || !existsSync(join(BOARDS, `${board}.dc.html`))) {
    throw new Error(`no board design/ui-canvas/${board}.dc.html: name screenshots after a board`);
  }
  return join(__dirname, 'screens', `${board}--${project}.png`);
}
