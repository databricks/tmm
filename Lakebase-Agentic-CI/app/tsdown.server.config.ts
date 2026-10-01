import { appkitServerConfig } from '@databricks/appkit/tsdown';

// AppKit's server build preset. When you keep code agents in `server/agents/`,
// it auto-includes them as build entries so discovery works in a bundled build.
// Customize with overrides — `appkitServerConfig({ external, define, ... })` —
// or a function form for full control: `appkitServerConfig((base) => ({ ...base }))`.
export default appkitServerConfig();
