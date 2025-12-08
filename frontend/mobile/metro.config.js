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
        require('path').resolve(__dirname, '..')
    ]
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
