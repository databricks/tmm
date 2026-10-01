import { Plugin, type PluginManifest } from '@databricks/appkit';
import { expectStream, createTestPluginContext } from '@databricks/appkit/testing';
import { describe, expect, test } from 'vitest';

/**
 * Example test using the AppKit testing kit (`@databricks/appkit/testing`).
 *
 * The kit lets you test a plugin with NO Databricks workspace, credentials, or
 * network — so these tests run anywhere, including CI. Delete this file, or use
 * it as a starting point for testing your own plugins.
 *
 * Two headline helpers are shown below:
 *  - `createTestPluginContext()` — a real PluginContext with faked edges, attachable
 *    to a plugin so its real code paths (routes, tool dispatch, user scoping)
 *    run under test.
 *  - `expectStream(...).toEmit(...)` — assert the ordered event types a
 *    streaming handler emits.
 *
 * Note: tests instantiate the plugin CLASS directly (`new GreeterPlugin()`).
 * The `analytics()` / `agents()` factory functions you pass to `createApp`
 * return a descriptor for the app to construct — for a unit test you want the
 * instance itself.
 */

// A tiny example plugin: it registers one route and streams two events.
class GreeterPlugin extends Plugin {
  static manifest = {
    name: 'greeter',
    displayName: 'Greeter',
    description: 'Example plugin for the testing-kit demo',
    resources: { required: [], optional: [] },
  } as PluginManifest<'greeter'>;

  async setup() {
    // Routes registered here are captured by createTestPluginContext().routes.
    this.context?.addRoute('get', '/hello', (_req, res) => {
      res.end();
    });
  }

  // A stand-in for a streaming handler: yields SSE-style event objects.
  async *greet(name: string) {
    yield { type: 'greeting_start', name };
    yield { type: 'greeting_end', message: `Hello, ${name}!` };
  }
}

describe('testing kit example', () => {
  test('attaches a real PluginContext and records registered routes', async () => {
    const mock = createTestPluginContext();
    const plugin = new GreeterPlugin({});

    await mock.attach(plugin);
    await plugin.setup();

    expect(mock.routes).toContainEqual(expect.objectContaining({ method: 'get', path: '/hello' }));
  });

  test('asserts the ordered events a stream emits', async () => {
    const plugin = new GreeterPlugin({});

    await expectStream(plugin.greet('world')).toEmit('greeting_start', 'greeting_end');
  });
});
