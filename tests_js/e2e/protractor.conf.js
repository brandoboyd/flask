exports.config = {
  allScriptsTimeout: 60000,


  suites : {
     login      : 'scenarios/login.js',
     main_nav   : 'scenarios/main_navigation.js',
     config_nav : 'scenarios/configure_navigation.js',
     sub_tabs   :  [
       'scenarios/customers_sub_tabs.js',
       'scenarios/agents_sub_tabs.js',
       'scenarios/journey_sub_tabs.js'
     ],
    predictors : [
        'scenarios/predictors.js'
    ],
    datasets : [
        'scenarios/datasets.js'
    ],
    accounts : [
        'scenarios/accounts.js'
    ],
    events_sync : [
        'scenarios/events_sync.js'
    ]
  },


  specs: [
    'scenarios/*.js'
  ],


  capabilities: {
    'browserName': 'chrome',
    'chromeOptions': {
      'args': ['incognito', 'disable-extensions', 'start-maximized']
    }
  },

  baseUrl: 'http://127.0.0.1:5000',
  framework: 'jasmine2',

  jasmineNodeOpts: {
      defaultTimeoutInterval: 100000
  },

  onPrepare: function() {
    var AllureReporter = require('jasmine-allure-reporter');
    global.EC = protractor.ExpectedConditions;
    jasmine.getEnv().addReporter(new AllureReporter({
      resultDir: 'allure-results'
    }));
     jasmine.getEnv().afterEach(function(done){
      browser.takeScreenshot().then(function (png) {
        allure.createAttachment('Screenshot', function () {
          return new Buffer(png, 'base64')
        }, 'image/png')();
        done();
      })
    });
    browser.manage().window().setSize(1600, 1200);
  }
};
