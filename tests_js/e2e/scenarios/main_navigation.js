'use strict';

/* https://github.com/angular/protractor/blob/master/docs/toc.md */

var LoginPage   = require("../pages/login_page");
var MainMenu    = require("../pages/main_menu");
var AppSwitcher = require("../pages/app_switcher");

describe('Main Navigation - ', function() {

  var mainMenuItems = new MainMenu();
  var loginPage = new LoginPage();
  var settings  = new AppSwitcher();

  beforeAll(function(){
    loginPage.login('/login');
    settings.switch('QA', true);
  });

  describe("after login", function() {
    xit('user should be redirected to the channels\' settings page', function() {
      expect(browser.getLocationAbsUrl()).toMatch("/configure#/channels");
    });
  });

  describe("When User switches to ", function() {
    it('GSA app, it has the predefined set of main sections in exact order', function() {
      settings.switch('GSA', true);
      var expectedOptions =  [ 'Dashboard', 'Reports', 'Inbox', 'Test', 'Jobs' ];
      mainMenuItems.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions);
      })
    });
    it('GSE app has the predefined set of main sections in exact order', function() {
      //var expectedOptions = ['Dashboard', 'Reports', 'Interactions', 'Test'];
      settings.switch('GSE', true);
      var expectedOptions = ['Test', 'Jobs'];
      mainMenuItems.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions);
      })
    });

    it('JA app has the predefined set of main sections in exact order', function() {
      settings.switch('Journey Analytics', true);
      var expectedOptions = [ 'Dashboard', 'Customers', 'Agents', 'Journeys', 'Test', 'Jobs' ];
      mainMenuItems.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions);
      })
    });


    xit('NPS app has the predefined set of main sections in exact order', function() {
      var expectedOptions = ['Dashboard', 'NPS', 'Test'];
      element(by.linkText('NPS')).click();
      actualOptions.getItemsList().then(function(options) {
        expect(options).toEqual(expectedOptions);
      })
    });


    it('PRR app has the predefined set of main sections in exact order', function() {
      settings.switch('Predictive Matching', true);
      var expectedOptions = [ 'Dashboard', 'Predictors', 'Agents', 'Test', 'Jobs' ];
      mainMenuItems.getItemsList().then(function(actualOptions) {
        expect(expectedOptions).toEqual(actualOptions);
      })
    });

  });


});


