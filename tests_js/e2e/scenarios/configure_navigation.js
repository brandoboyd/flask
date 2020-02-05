'use strict';

var LoginPage     = require("../pages/login_page");
var AppSwitcher   = require("../pages/app_switcher");
var ConfigureMenu = require("../pages/configure_menu");

describe("After switching to", function() {

    var loginPage   = new LoginPage();
    var settings    = new AppSwitcher();
    var configMenu  = new ConfigureMenu();



    beforeAll(function(){
      loginPage.login('/login');
    });

    it('JOP app - the configure section should have the following list of options in proper order', function() {
      settings.switch('Journey Analytics', true);
      var expectedOptions =  [ 'Agent Profile', 'Customer Profile', 'Channel Types', 'Event Types', 'Journey Types', 'Channels', 'Accounts', 'Groups', 'Widgets Gallery', 'Smart Tags', 'Journey Tags', 'Funnels', 'Default Channels', 'Password', 'User Details', 'Default Channels', 'User Management' ];
      configMenu.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions)
      })
    });
    it('GSA app - the configure section should have the following list of options in proper order', function() {
      settings.switch('GSA', true);
      var expectedOptions = [ 'Channels', 'Accounts', 'Groups', 'Messages', 'Smart Tags', 'Trials', 'Contact Labels', 'Event Logs', 'Default Channels', 'Password', 'User Details', 'Default Channels', 'User Management' ];
      configMenu.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions)
      })
    });

    it('GSE app - the configure section should have the following list of options in proper order', function() {
      settings.switch('GSE', true);
      var expectedOptions = [ 'Channels', 'Accounts', 'Groups', 'Trials', 'Default Channels', 'Password', 'User Details', 'Default Channels', 'User Management' ];
      configMenu.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions)
      })
    });


    it('PRR app - the configure section should have the following list of options in proper order', function() {
      settings.switch('Predictive Matching', true);
      var expectedOptions = ['Agent Profile', 'Datasets', 'Channels', 'Accounts', 'Groups', 'Smart Tags', 'Predictors', 'Default Channels', 'Password', 'User Details', 'Default Channels', 'User Management' ];
      configMenu.getItemsList().then(function (actualOptions) {
        expect(expectedOptions).toEqual(actualOptions)
      })
    });
});


