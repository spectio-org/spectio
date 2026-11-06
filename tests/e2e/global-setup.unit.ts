import { test, expect } from '@playwright/test';
import { portOf, sessionCookie, statePath, withoutTicket } from './global-setup';

test('the port of a URL, explicit or the default of its scheme (CR-P3T12-05)', () => {
  expect(portOf('http://127.0.0.1:8765')).toBe('8765');
  expect(portOf('http://127.0.0.1/')).toBe('80');
  expect(portOf('https://spectio.example/')).toBe('443');
  expect(statePath('http://127.0.0.1/')).toMatch(/[/\\]80\.state\.json$/);
});

test('the session cookie is named as the server names it: no port in Host means 80 (CR-P3T13-01)', () => {
  expect(sessionCookie('http://127.0.0.1:8765')).toBe('spectio_session_8765');
  expect(sessionCookie('http://127.0.0.1/')).toBe('spectio_session_80');
  expect(sessionCookie('https://spectio.example/')).toBe('spectio_session_80');
  expect(sessionCookie('https://spectio.example:8443/')).toBe('spectio_session_8443');
});

test('an error of opening the link does not carry the ticket (CR-P3T12-03)', () => {
  const ticket = 'Tk_secret-43chars';
  const cause = new Error(`page.goto: net::ERR_CONNECTION_REFUSED at http://127.0.0.1:1/auth/link#${ticket}\n  navigating to "http://127.0.0.1:1/auth/link#${ticket}"`);
  const error = withoutTicket(cause, ticket);
  expect(error.message).toContain('ERR_CONNECTION_REFUSED');
  expect(error.message).not.toContain(ticket);
  expect(String(error.stack)).not.toContain(ticket);
  expect(error.cause).toBeUndefined();
  expect(withoutTicket('a string', ticket).message).toContain('a string');
});
