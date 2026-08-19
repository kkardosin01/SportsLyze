// Configuração do Metro para funcionar dentro do monorepo pnpm (Turborepo).
// Sem isso, o Metro não resolve pacotes symlinkados pelo pnpm (ex: @sportslyze/*
// e o próprio expo-router, que fica em node_modules/.pnpm/... no root do monorepo).
// https://docs.expo.dev/guides/monorepos/
const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const workspaceRoot = path.resolve(projectRoot, "../..");

const config = getDefaultConfig(projectRoot);

config.watchFolders = [workspaceRoot];
config.resolver.nodeModulesPaths = [
  path.resolve(projectRoot, "node_modules"),
  path.resolve(workspaceRoot, "node_modules"),
];
config.resolver.unstable_enableSymlinks = true;

module.exports = config;
