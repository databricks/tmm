import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import reactPlugin from 'eslint-plugin-react';
import reactHooksPlugin from 'eslint-plugin-react-hooks';
import reactRefreshPlugin from 'eslint-plugin-react-refresh';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  // Global ignores
  {
    ignores: [
      '**/dist/**',
      '**/build/**',
      '**/node_modules/**',
      '**/.next/**',
      '**/coverage/**',
      'client/dist/**',
      '**.databricks/**',
    ],
  },

  // Base JavaScript config
  js.configs.recommended,

  // TypeScript config for all TS files
  ...tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },

  // React config for client-side files
  {
    files: ['client/**/*.{ts,tsx}', '**/*.tsx'],
    plugins: {
      react: reactPlugin,
      'react-hooks': reactHooksPlugin,
      'react-refresh': reactRefreshPlugin,
    },
    settings: {
      react: {
        version: 'detect',
      },
    },
    rules: {
      ...reactPlugin.configs.recommended.rules,
      ...reactPlugin.configs['jsx-runtime'].rules,
      ...reactHooksPlugin.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      'react/prop-types': 'off', // Using TypeScript for prop validation
      'react/no-array-index-key': 'warn',
    },
  },

  // Node.js specific config for server files
  {
    files: ['server/**/*.ts', '*.config.{js,ts}'],
    rules: {
      '@typescript-eslint/no-var-requires': 'off',
    },
  },

  // Disable type-checking for JS/ESM/CJS scripts and standalone config files
  // (these live outside the TS project graph, e.g. scripts/*.mjs).
  {
    files: ['**/*.js', '**/*.mjs', '**/*.cjs', '*.config.ts', '**/*.config.ts'],
    ...tseslint.configs.disableTypeChecked,
  },

  // Node globals for standalone scripts run by node/tsx (not bundled), e.g.
  // scripts/fix-lockfile.mjs. TS files get these from @types/node instead.
  {
    files: ['**/*.mjs', '**/*.cjs'],
    languageOptions: {
      globals: { console: 'readonly', process: 'readonly' },
    },
  },

  // Test files often use async signatures for API conformance (overriding an
  // async base-class method, async generators) without awaiting.
  {
    files: ['**/*.test.ts'],
    rules: { '@typescript-eslint/require-await': 'off' },
  },

  // Prettier config (must be last to override other formatting rules)
  prettier,

  // Custom rules
  {
    rules: {
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  }
);
