import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api/client.js';

const UNREACHABLE = /Cannot reach the CineMatch AI server/;

function respond(status, body, isJson = true) {
  return vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: isJson ? () => Promise.resolve(body) : () => Promise.reject(new SyntaxError('not json')),
  });
}

afterEach(() => vi.unstubAllGlobals());

describe('api client error mapping', () => {
  it('surfaces FastAPI string details', async () => {
    vi.stubGlobal('fetch', respond(422, { detail: 'Unknown genre: Nope' }));
    await expect(api.recommend({})).rejects.toMatchObject({ message: 'Unknown genre: Nope', status: 422 });
  });

  it('joins validation error lists', async () => {
    vi.stubGlobal('fetch', respond(422, { detail: [{ msg: 'a' }, { msg: 'b' }] }));
    await expect(api.recommend({})).rejects.toThrow('a; b');
  });

  it('treats network failures and proxy gateway errors as "server unreachable"', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api.health()).rejects.toMatchObject({ status: 0, message: expect.stringMatching(UNREACHABLE) });
    vi.stubGlobal('fetch', respond(502, null, false));
    await expect(api.health()).rejects.toThrow(UNREACHABLE);
    vi.stubGlobal('fetch', respond(504, null, false));
    await expect(api.health()).rejects.toThrow(UNREACHABLE);
  });

  it('does not mislabel a genuine backend error as "unreachable"', async () => {
    vi.stubGlobal('fetch', respond(500, null, false));
    await expect(api.health()).rejects.toMatchObject({ status: 500, message: 'Request failed (500)' });
  });

  it('keeps 404s distinguishable for "not found" pages', async () => {
    vi.stubGlobal('fetch', respond(404, { detail: 'Movie 9 not found' }));
    await expect(api.getMovie(9)).rejects.toMatchObject({ status: 404 });
  });

  it('DELETE succeeds on 204 without parsing a body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, status: 204 }));
    await expect(api.clearFeedback(6)).resolves.toBeUndefined();
  });
});
