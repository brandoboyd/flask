var _ = require('underscore');
var path = require('path');
var paths = require('../gulp/paths.json');
var files = [
  "static/assets/vendor/jquery/dist/jquery.min.js",
  'static/assets/vendor/angular/angular.min.js',
  'static/assets/vendor/angular-mocks/angular-mocks.js',
  paths.vendorjs,
  paths.angular
];

_.values(paths.angularFiles).forEach(function (eachNgFile) {
  files.push(eachNgFile);
});

files.push(
  'tests_js/specs/karma.utils.js',
  'tests_js/specs/tests.factory.js',
  'tests_js/specs/**/*.js'
);

module.exports = function (config) {
  config.set({
    basePath: '../',

    files: _.flatten(files),

    exclude: [
      'static/assets/js/libs/angular-ui-utils/modules/**/test/*.js'
    ],

    frameworks: ['jasmine'],

    browsers: ['Chrome'],

    singleRun: true,

    autoWatch: true,

    plugins: [
      'karma-chrome-launcher',
      'karma-jasmine',
      'karma-htmlfile-reporter',
      'karma-coverage',
      'karma-spec-reporter',
      'karma-threshold-reporter'
    ],

    reporters: ['dots', 'html', 'coverage', 'spec', 'threshold'],


    // the configure thresholds
    thresholdReporter: {
      statements: 15,
      branches: 5,
      functions: 10,
      lines: 10
    },

    specReporter: {
      maxLogLines: 5,         // limit number of lines logged per test
      suppressErrorSummary: true,  // do not print error summary
      suppressFailed: false,  // do not print information about failed tests
      suppressPassed: false,  // do not print information about passed tests
      suppressSkipped: false,  // do not print information about skipped tests
      showSpecTiming: false // print the time elapsed for each spec
    },

    htmlReporter: {
      outputFile: 'tests_js/specs/units.html'
    },

    preprocessors: {
      'static/assets/js/app/**/!(*.module).js': ['coverage']
    },

    coverageReporter: {
      type: 'html',
      dir: 'tests_js/specs/__coverage/'
    },

    client: {
      captureConsole: true
    }

  });
};
