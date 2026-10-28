import { test, expect } from '@playwright/test';
import { basename } from 'node:path';
import { boardShotPath } from './boards';

test('a screenshot is named after its board and project', () => {
  expect(basename(boardShotPath('RunsTable', 'phone'))).toBe('RunsTable--phone.png');
});

test('a name that is not a board is refused', () => {
  expect(() => boardShotPath('NoSuchBoard', 'desktop')).toThrow(/no board/);
  expect(() => boardShotPath('../RunsTable', 'desktop')).toThrow(/no board/);
});
