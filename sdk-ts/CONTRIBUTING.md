# Contributing to Mnemosyne TypeScript SDK

Thank you for your interest in contributing to the Mnemosyne TypeScript SDK.

## Development Setup

### Prerequisites

- Node.js 18.0.0 or higher
- npm 9+ or pnpm

### Getting Started

```bash
# Clone the repository
git clone https://github.com/raghavpatnecha/Mnemosyne.git
cd Mnemosyne/sdk-ts

# Install dependencies
npm install

# Build the SDK
npm run build

# Run tests
npm test
```

## Development Workflow

### Code Style

This project uses ESLint and Prettier for code formatting:

```bash
# Check linting
npm run lint

# Fix linting issues
npm run lint:fix

# Check formatting
npm run format:check

# Format code
npm run format
```

### Type Checking

```bash
# Run TypeScript type checker
npm run typecheck
```

### Testing

```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run tests with coverage
npm run test:coverage
```

### Building

```bash
# Build the SDK (TypeScript to JavaScript + type definitions)
npm run build

# Build in watch mode for development
npm run build:watch
```

## Project Structure

```
sdk-ts/
├── src/                   # Source code
│   ├── index.ts           # Main entry point and exports
│   ├── client.ts          # MnemosyneClient class
│   ├── base-client.ts     # Base HTTP client with retry logic
│   ├── exceptions.ts      # Custom error classes
│   ├── streaming.ts       # SSE streaming utilities
│   ├── version.ts         # SDK version
│   ├── resources/         # API resource classes
│   │   ├── auth.ts
│   │   ├── chat.ts
│   │   ├── collections.ts
│   │   ├── documents.ts
│   │   └── retrievals.ts
│   └── types/             # TypeScript type definitions
│       ├── index.ts
│       ├── auth.ts
│       ├── chat.ts
│       ├── collections.ts
│       ├── common.ts
│       ├── documents.ts
│       ├── retrievals.ts
│       └── shared.ts
├── tests/                 # Test files
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── setup.ts           # Test utilities
├── examples/              # Usage examples
├── dist/                  # Built output (generated)
└── package.json
```

## Making Changes

### Adding a New Feature

1. Create a feature branch from `main`
2. Implement your changes with tests
3. Ensure all tests pass: `npm test`
4. Ensure code is formatted: `npm run format`
5. Ensure no lint errors: `npm run lint`
6. Ensure types are correct: `npm run typecheck`
7. Create a changeset (see below)
8. Submit a pull request

### Writing Tests

Tests are written using Vitest. Place tests in the appropriate directory:

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Integration tests for API interactions

Example test structure:

```typescript
import { describe, it, expect, beforeEach } from 'vitest';

describe('MyComponent', () => {
  beforeEach(() => {
    // Setup
  });

  it('should do something', () => {
    expect(result).toBe(expected);
  });
});
```

### Creating a Changeset

This project uses [changesets](https://github.com/changesets/changesets) for version management:

```bash
# Create a new changeset
npm run changeset

# Follow the prompts to:
# 1. Select the package(s) affected
# 2. Choose the version bump type (patch/minor/major)
# 3. Write a summary of your changes
```

**Version Guidelines:**
- `patch` - Bug fixes, documentation updates
- `minor` - New features, backwards-compatible additions
- `major` - Breaking changes

## Type Definitions

When modifying types:

1. Update the type definition in `src/types/`
2. Export from `src/types/index.ts` if public
3. Export from `src/index.ts` if part of public API
4. Update any affected tests
5. Consider backwards compatibility

## Pull Request Guidelines

1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what changes you made and why
3. **Tests**: Include tests for new functionality
4. **Documentation**: Update README if adding features
5. **Changeset**: Include a changeset for versioning

## Code of Conduct

Please be respectful and inclusive in all interactions. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

## Questions?

- Open a [GitHub Issue](https://github.com/raghavpatnecha/Mnemosyne/issues)
- Join our [Discussions](https://github.com/raghavpatnecha/Mnemosyne/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
