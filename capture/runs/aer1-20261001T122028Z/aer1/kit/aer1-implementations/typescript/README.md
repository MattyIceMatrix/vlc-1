# AER-1 TypeScript

TypeScript implementation targeting native Node.js ESM. Runtime code uses only `node:crypto`, `node:fs`, and `node:path`.

## Run

```sh
npm install
npm run conformance
npm run emit
```

The conformance command compiles the source and reports `CONFORMANCE: 45/45`. `src/aer1.ts` exports `verify`, `profile`, `anchor`, `emit`, and `load`.

`typescript` and `@types/node` are development-only build dependencies; no runtime package is required.
