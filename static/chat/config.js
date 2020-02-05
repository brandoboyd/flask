var util = require('util'),
    env = process && process.env.NODE_ENV || 'development',
    config;

config = {
    'common': {
    },

    'development': {
        'IP_ADDR': '127.0.0.1',                     // Listening IP of node.js app
        'PORT': 5005,                               // Listening port of node.js app
        'HOST_DOMAIN': '127.0.0.1:5000',            // For API requests to Python backend
        'SOCKET_DOMAIN': '127.0.0.1:5005',
        'ENV': 'development'
    },

    'staging': {
        'IP_ADDR': '45.56.126.73',
        'HOST_DOMAIN': 'dev.cxoptimizer.com',
        'SOCKET_DOMAIN': '45.56.126.73:5000',
        'PORT': 5000,
        'ENV': 'staging'
    },

    'production': {
        'IP_ADDR': '45.56.126.73',
        'HOST_DOMAIN': 'dev.cxoptimizer.com',
        'SOCKET_DOMAIN': '45.56.126.73:5000',
        'PORT': 5000,
        'ENV': 'production'
    }
};

module.exports = util._extend(config['common'], config[env]);