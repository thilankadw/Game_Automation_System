/**
 * Result returned by server actions that mutate API resources.
 *
 * Successful actions carry no payload because the pages re-render from the
 * backend after a router refresh.
 */
export type ActionResult =
  | { ok: true }
  | { ok: false; error: string };
