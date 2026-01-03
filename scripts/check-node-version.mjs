#!/usr/bin/env node
/**
 * Simple guard script: ensures running Node major matches .nvmrc expected major.
 * Fails with a clear message if mismatch to reduce CI/dev confusion.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, '..');

function readNvmrc() {
    try {
        const raw = readFileSync(resolve(root, '.nvmrc'), 'utf8').trim();
        return raw.replace(/^v/, '').trim();
    } catch {
        return null;
    }
}

const expected = readNvmrc();
if (!expected) process.exit(0); // nothing to enforce

const expectedMajor = expected.split('.')[0];
const actualMajor = process.versions.node.split('.')[0];

if (expectedMajor !== actualMajor) {
    console.error(`\n[Node Version Mismatch] Expected major ${expectedMajor} (from .nvmrc) but running ${process.versions.node}.\n` +
        `Run: nvm use || nvm install ${expected}\n`);
    process.exit(1);
}
