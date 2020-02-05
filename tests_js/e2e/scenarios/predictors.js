'use strict';

var LoginPage     = require("../pages/login_page");
var AppSwitcher   = require("../pages/app_switcher");
var Predictor     = require("../pages/predictor");

describe("PRR App - ", function() {

  var loginPage   = new LoginPage();
  var appCtxt     = new AppSwitcher();
  var predictor   = new Predictor();
  var simplePredictorName = 'SimpleTestPredictor#' + Date.now();

  beforeAll(function(){
    loginPage.login('/login');
    appCtxt.switch('QA');
    appCtxt.switch('Predictive Matching', true);
  });


  describe('Settings Page', function() {
    it(" should have correct title", function() {
      predictor.navigateToPredictorsList();
      var title = element(by.tagName('h1'));
      expect(title.getText()).toEqual('Predictors');
    });

    it(" should display new form after clicking the button ", function() {
      predictor.clickAddNewPredictorBtn();
      var title = element(by.tagName('h3'));
      expect(title.getText()).toEqual('New Predictor');
    });

    describe("Configure predictor with numeric metric ", function() {

      it("When User types name for predictor, User should see name in the Name field", function() {
        predictor.addPredictorName(simplePredictorName);
        predictor.getPredictorNameValue().then(function (val) {
          expect(val).toEqual(simplePredictorName)
        });
      });

      it("When User selects dataset from Dataset dropdown, User should see dataset daterange displayed", function() {
        predictor.addDataset();
        expect(element(by.css('[ng-show="selectedDataset"]')).isPresent()).toBeTruthy();
      });

      it("When User selects CSAT (numeric value) from Metric dropdown, User should see dropdown closes and CSAT displayed", function() {
        predictor.addMetric('CSAT');
        predictor.getModelValue('predictor.metric').then(function (val) {
          expect(val).toContain('CSAT');
        });
      });

      it("When User selects native_id from Action ID dropdown, User should see dropdown closes and native_id displayed", function() {
        predictor.addActionId('native_id');
        predictor.getModelValue('predictor.action_id_expression').then(function (val) {
          expect(val).toContain('native_id');
        });
      });

      it("When User selects 'Dataset generated' from Action Type dropdown, User should see dropdown closes and 'Dataset generated' displayed", function() {
        predictor.addActionType('Dataset generated');
        predictor.getActionTypeValue().then(function(val) {
          expect(val).toEqual('Dataset generated');
        })
      });

      it("When User adds new Action feature 'Closing_Account', 'Closing_Account' is displayed in Label field", function() {
        predictor.addActionFeature(0, 'Closing_Account');
        predictor.getFeatureLabelValue(0).then(function(val) {
          expect(val).toEqual('Closing_Account')
        });
        /*
        predictor.getFeatureTypeValue(0).then(function(val) {
          expect(val).toEqual('Label')
        })
        */

      });

      it("When User adds new new Context feature 'customer_status', Create button should be enabled", function() {
        predictor.addContextFeature(1, 'customer_status');
        expect(
          element(by.buttonText('Create')).isEnabled()
        ).toBe(true);
      });

      it("When User clicks Create button, Then User should see Models button displayed", function() {
        element(by.buttonText('Create')).click();
        //first scroll to the top so that Models button is visible
        browser.executeScript('window.scrollTo(0,0);');
        //click Models
        var modelsBtn = element(by.linkText('Models'));
        expect(modelsBtn.isPresent()).toBe(true);

      });

      it("When User clicks Models button, Then User should see predictor name and RMSE column", function() {
        //first scroll to the top so that Models button is visible
        browser.executeScript('window.scrollTo(0,0);');
        element(by.linkText('Models')).click();
        var RMSE_column = element(by.css('[data-title="RMSE"]'));
        var title   = element(by.tagName('h3'));
        expect(title.getText()).toContain(simplePredictorName);
        expect(RMSE_column.isPresent()).toBe(true);
      });

    });

    describe("Generate/Purge data for predictor ", function() {
      it("When User clicks on Generate data, User should see message 'Started generation of predictor data'", function() {
        predictor.navigateToPredictorsList();
        //predictor.generateData();

      });
      it("When User waits 1 min, User should see message 'Finished inserting…'", function() {

      });
      it("When User clicks on Purge button, User should see 'Removed … total items'", function() {

      });
      it("When User checks 'Generate' and 'Purge' button, User should see 'Generate' button is active and 'Purge' button is disabled", function() {

      });
    });

/*
    xdescribe("Delete previously created simple predictor ", function() {
      var simplePredictor = element(by.linkText(simplePredictorName));
      var deleteButton    = element(by.css('button[tooltip="Delete"]'));
      var yesButton       = element(by.buttonText('Yes'));
      var opt = simplePredictor.element(by.xpath('..')).element(by.xpath('preceding-sibling::td')).element(by.css('.checkbox'));

      it("should enable delete button first once selected", function() {
        opt.click();
        expect(deleteButton.isEnabled()).toBe(true);
      });

      it("should remove the deleted predictor from the table", function() {
        deleteButton.click();
        yesButton.click();
        expect(simplePredictor.isPresent()).toBe(false);
      });
    });
*/

  });

});
