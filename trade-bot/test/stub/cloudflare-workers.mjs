// Minimal stand-in for "cloudflare:workers" so index.js can run under plain Node in tests.
export class DurableObject {
  constructor(ctx, env) { this.ctx = ctx; this.env = env; }
}
