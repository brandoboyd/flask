'use strict';

var LoginPage     = require("../pages/login_page");
var AppSwitcher   = require("../pages/app_switcher");
var Account       = require("../pages/account");
var ConfigureMenu = require("../pages/configure_menu");
var Select2Widget = require("../pages/select2");

/*
Feature: Adding Predictive Matching app to account, it's activation and menu verification

Scenario 1: Add Predictive Matching app to account - priority High
 Given User with Staff role is configured
 And Account is created
 And Update Account form is displayed
 When User clicks on Configurable Apps field
 Then User should see Predictive Matching in dropdown
 When User clicks on Predictive Matching option in the drop down
 Then User should see that Predictive Matching is added to the field
 When User clicks on Update button
 Then User should see Update Account form closes
 When User opens cog-wheel drop down
 Then User should see Predictive Matching under the Selected app section

Scenario 2: Remove Predictive Matching app from account - priority High
 Given User with Staff role is configured
 And Account is created
 And Update Account form is displayed
 And Predictive Matching app id added to the account
 When User clicks on x icon in Configurable Apps field to remove Predictive Matching
 Then User should see Predictive Matching in removed
 When User clicks on Update button
 Then User should see Update Account form closes
 When User opens cog-wheel drop down
 Then User should NOT see Predictive Matching under the Selected app section

Scenario 3: Admin User should see certain menu items when Predictive Matching app is active - priority High
 Given User with Admin role is configured
 And Account is created
 And Predictive Matching app is added to account
 And User with Admin role is logged in
 When User opens cog-wheel drop down
 Then User should see Predictive Matching under the Selected app section
 When User clicks on Predictive Matching
 Then User should see the following top menu options: Predictive Matching as app name, Dashboard and Predictors And User should see the following options in the left menu: Datasets under SHEMA section, Channels, Accounts, Groups, Smart Tags and Predictors under SETTINGS section
*/


describe("PRR App - ", function() {

  var loginPage     = new LoginPage();
  var appCtxt       = new AppSwitcher();
  var account       = new Account();
  var configureMenu = new ConfigureMenu();
  var select2       = new Select2Widget();

  var accountName = 'Acc#' + Date.now();



  beforeAll(function(){
    loginPage.login('/login');
    appCtxt.switch('GSE', true);
  });

  beforeEach(function() {
    configureMenu.switchByLink('/configure#/accounts');
  });

  describe('Adding Predictive Matching app to account -- ', function() {

    it('after account is created user should be redirected to the accounts\' list page', function() {
      account.create(accountName);
      expect(browser.getCurrentUrl()).toContain('/configure#/accounts');
    });

    describe('The following actions should be allowed with the new account:', function() {
      var accountLink = account.locateAccountLinkByName(accountName);

      it('just created account should be located in the accounts list', function() {
        accountLink.first().getText().then(function (label) {
          expect(label).toEqual(accountName);
        });
      });

      it('user should be navigated to the account edit page after clicking on the account link', function() {
        accountLink.first().click();
        element(by.tagName('h3')).getText().then(function(title) {
          expect(title).toContain(accountName);
        });
      });

      describe('\'Predictive Matching\' app should ', function() {
        it('appear in Configurable Apps field when User selects it form the list of available apps', function() {
          //click the just created account
          accountLink.first().click();
          //add PRR app to the account
          select2.addTag('s2id_configurable_apps', 'Predictive Matching');
          var tags = select2.getTagsList('s2id_configurable_apps');
          expect(tags).toContain('Predictive Matching');
          //save the form
          element(by.buttonText('Update')).click();
        });
        it('appear under the Selected app section when User opens cog-wheel drop down', function() {
          //make the new account active
          appCtxt.switch(accountName);
          //check if the PRR app is in the list of the available apps
          var predictiveApp = element(by.css('a[href*="/account_app/switch/Predictive Matching"]'));
          expect(predictiveApp.isPresent()).toBe(true);
        });
      });

      it('after switching to \'Predictive Matching\' app user should see the following menu options', function() {
        //make the new account active
        appCtxt.switch(accountName);
        //switch to PRR
        appCtxt.switch('Predictive Matching', true);

        var expectedOptions = ['Agent Profile', 'Datasets', 'Channels', 'Accounts', 'Groups', 'Smart Tags', 'Predictors', 'Default Channels', 'Password', 'User Details', 'Default Channels', 'User Management' ];
        configureMenu.getItemsList().then(function (actualOptions) {
          expect(expectedOptions).toEqual(actualOptions)
        })
      })
    });
  });

  describe('Removing Predictive Matching app from account -- ', function() {
    var accountLink = account.locateAccountLinkByName(accountName);
    it('User should NOT see Predictive Matching under the Selected app section', function() {
      //navigate to the just created account form
      accountLink.first().click();
      //remove PRR app from the account
      select2.removeTag('s2id_configurable_apps', 'Predictive Matching');
      //update the Form
      element(by.buttonText('Update')).click();
      //make the just created account active
      appCtxt.switch(accountName);
      var predictiveApp = element(by.css('a[href*="/account_app/switch/Predictive Matching"]'));
      expect(predictiveApp.isPresent()).toBe(false);
    });
  })

});
