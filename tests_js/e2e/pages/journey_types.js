'use strict';

var UiSelect = require("./ui-select2");

var JourneyType = function() {

  var addJourneyTypeBtn = element(by.xpath("//*[@ng-click='create()']"));
  var journeyTypeNameFld = element(by.id("id_name"));
  var createJourneyTypeBtn = element(by.partialButtonText('Create'));
  var addNewAttributeBtn = element(by.partialButtonText('Add New Attribute'));
  var updateJourneyTypeBtn = element(by.partialButtonText('Update'));
  var addNewStageBtn = element(by.partialButtonText('Add New Stage'));
  var backBtnAllJourneyTypes = element(by.xpath("//button[@tooltip='All Journey Types']"));
  var JOURNEY_ROW = "//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]//ancestor::tr[1]";
  var JOURNEYS_NUMBER_CELL = JOURNEY_ROW + "//td[4]";
  var JOURNEY_CHECKBOX = JOURNEY_ROW + "//td[1]/*/input[@ng-click='select(item)']";

  this.navigateToJourneyTypesPage = function() {
    element(by.css('.nav-side-tabs')).element(by.linkText('Journey Types')).click();
  };

  this.waitJourneyTypeCreatedSuccessfully = function(journeyTypeName) {
    var e = element(by.xpath("//*[contains(@class,'table')]//tbody//a[contains(text(),'%s')]".replace('%s', journeyTypeName)));
    browser.wait(EC.presenceOf(e), 100000);
    expect(e.isPresent()).toBeTruthy();
  };

  this.verifyJourneysNumber = function(journeyTypeName, numberOfJourneys) {
    var numberActual = element(by.xpath(JOURNEYS_NUMBER_CELL.replace('%s', journeyTypeName))).getText();
    expect(numberActual).toEqual(numberOfJourneys);
  }

  this.verifyJourneyTypesPageOpen = function() {
    expect(element(by.tagName('h1')).getText()).toEqual('Journey Types');
  };

  this.clickAddJourneyTypeBtn = function() {
    addJourneyTypeBtn.click();
  };

  this.verifyNewJourneyTypePageOpen = function() {
    expect(element(by.tagName('h3')).getText()).toEqual('New Journey Type');
  };

  this.addJourneyTypeName = function(label) {
    journeyTypeNameFld.sendKeys(label);
};

  this.clickCreateJourneyTypeBtn = function() {
    createJourneyTypeBtn.click();
    browser.wait(EC.presenceOf(addNewAttributeBtn), 1000);
    browser.wait(EC.presenceOf(addNewStageBtn), 1000);
  };

  this.clickAddAttributeBtn = function() {
    addNewAttributeBtn.click();
  };

  this.addAttribute = function(rowNum, label, type, expression) {
    var e = element(by.repeater("feature in item['journey_attributes_schema'] track by $index").row(rowNum));
    e.element(by.model('feature.label')).sendKeys(label);
    e.element(by.cssContainingText('option', type)).click();
    e.element(by.model('feature.field_expr')).sendKeys(expression);
  };

  this.clickAddStageBtn = function() {
      addNewStageBtn.click();
      var e = element(by.repeater("st in stage.items track by $index"));
      expect(e.isPresent()).toBeTruthy();
  };

  this.addStage = function(rowNum, name, status, expression, eventTypeName) {
    var e = element(by.repeater("st in stage.items track by $index").row(rowNum));
    e.element(by.model('st.display_name')).sendKeys(name);
    e.element(by.cssContainingText('option', status)).click();
    e.element(by.model('st.match_expression')).sendKeys(expression);
    //e.element(by.model('$select.search')).click();
    //e.element(by.css('.ui-select-search')).sendKeys(eventTypeName, protractor.Key.ENTER);
    var input = new UiSelect( e.element(by.model('st.event_types')) );
    input.sendKeys(eventTypeName);
    input.pickChoice(0);
  };

  this.saveJourneyType = function() {
    updateJourneyTypeBtn.click();
  };

  this.navigateToAllJourneyTypes = function() {
    backBtnAllJourneyTypes.click();
  };
};

module.exports = JourneyType;
