const { getDefaultConfig } = require('expo/metro-config');
const path = require('path');

/**
 * Shared Metro config for Pi-PM monorepo apps.
 * @param {string} projectRoot - absolute path to the app directory
 */
function createMetroConfig(projectRoot) {
  const workspaceRoot = path.resolve(projectRoot, '../..');
  const config = getDefaultConfig(projectRoot);

  config.watchFolders = [workspaceRoot];
  config.resolver.nodeModulesPaths = [
    path.resolve(projectRoot, 'node_modules'),
    path.resolve(workspaceRoot, 'node_modules'),
  ];
  config.resolver.disableHierarchicalLookup = true;

  return config;
}

module.exports = { createMetroConfig };
