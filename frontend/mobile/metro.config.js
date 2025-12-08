const path = require('path');
const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

/**
 * Metro configuration
 * https://reactnative.dev/docs/metro
 *
 * @type {import('@react-native/metro-config').MetroConfig}
 */
const config = {
    watchFolders: [
        // Watch the parent directory so we can import shared code
        path.resolve(__dirname, '..')
    ],
    resolver: {
        // Ensure shared files in parent dir can resolve modules from this mobile/node_modules
        nodeModulesPaths: [path.resolve(__dirname, 'node_modules')],
    },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
