const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
const webpack = require('webpack');
const Dotenv = require('dotenv-webpack');

// Load env vars for the webpack config itself (e.g. proxy target)
require('dotenv').config();

/**
 * Multi-Portal Webpack Configuration
 * 
 * Build specific portal:
 *   PORTAL=b2b npm run build   (default)
 *   PORTAL=b2c npm run build
 *   PORTAL=platform npm run build
 * 
 * Development:
 *   PORTAL=b2c npm start
 */
const PORTAL = process.env.PORTAL || 'b2b';

const entryPoints = {
    b2b: './src/index.js',
    b2c: './src/b2c.js',
    platform: './src/platform.js',
};

const titles = {
    b2b: 'Enterprise SSO - B2B',
    b2c: 'Personal Workspace',
    platform: 'Platform Admin Console',
};

module.exports = {
    cache: {
        type: 'filesystem',
    },
    entry: entryPoints[PORTAL] || entryPoints.b2b,
    output: {
        path: path.resolve(__dirname, `dist/${PORTAL}`),
        filename: 'bundle.[contenthash].js',
        publicPath: '/',
        clean: true
    },
    module: {
        rules: [
            {
                test: /\.(js|jsx)$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: [
                            '@babel/preset-env',
                            ['@babel/preset-react', { runtime: 'automatic' }]
                        ]
                    }
                }
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader']
            }
        ]
    },
    plugins: [
        new HtmlWebpackPlugin({
            template: './public/index.html',
            favicon: false,
            title: titles[PORTAL] || 'Enterprise SSO'
        }),
        new Dotenv({
            path: './.env',
            safe: false,
            systemvars: true,
            defaults: false
        }),
        new webpack.DefinePlugin({
            'process.env.PORTAL': JSON.stringify(PORTAL),
            // Explicitly define API URL to ensure system/docker env vars take precedence over .env file
            'process.env.REACT_APP_API_URL': JSON.stringify(process.env.REACT_APP_API_URL)
        })
    ],
    devServer: {
        host: '0.0.0.0',  // Bind to all interfaces (allows Docker access)
        port: PORTAL === 'b2c' ? 3001 : PORTAL === 'platform' ? 3002 : 3000,
        hot: true,
        historyApiFallback: true,
        open: true,
        allowedHosts: process.env.NODE_ENV === 'production' ? undefined : 'all',  // Allow Docker in dev only
        proxy: {
            '/api': {
                target: process.env.REACT_APP_API_URL || (PORTAL === 'b2c'
                    ? 'http://localhost:8002'  // B2C API
                    : PORTAL === 'platform'
                        ? 'http://localhost:8080'  // Platform API
                        : 'http://localhost:8000'), // B2B API
                changeOrigin: true,
                secure: false
            }
        }
    },
    resolve: {
        extensions: ['.js', '.jsx']
    }
};

