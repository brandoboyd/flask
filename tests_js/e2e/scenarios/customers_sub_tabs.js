'use strict';

var LoginPage     = require("../pages/login_page");
var AppSwitcher   = require("../pages/app_switcher");
var MainMenu      = require("../pages/main_menu");

var CustomersTestParams = [
  {
    uiSref: 'customers.distribution', tab: 'Distribution', facets: [
    'All Industries',
    'All Age Groups',
    'All Customer Statuses',
    'All Segments' ]
  },
  {
    uiSref: 'customers.details', tab: 'Details', facets: [
    'All Industries',
    'All Age Groups',
    'All Customer Statuses',
    'All Segments' ]
  }
];

describe("Journey Analytics App", function() {

  var loginPage   = new LoginPage();
  var appCtxt     = new AppSwitcher();
  var mainMenu    = new MainMenu();


  beforeAll(function(){
    loginPage.login('/login');
    appCtxt.switch('QA');
    appCtxt.switch('Journey Analytics', false);
    mainMenu.switch('Customers');
  });


  describe('Customers should have the following subtabs present ', function() {
    CustomersTestParams.map(function(obj, i) {
      it(obj.tab + " tab should have proper ui-sref and title", function() {
        var tab = element(by.css('.nav-tabs')).element(by.xpath('//a[@ui-sref="' + obj.uiSref + '"]'));
        tab.getText().then(function(attr) {
          expect(attr.trim()).toEqual(CustomersTestParams[i]['tab']);
        });
      })
    })
  });



  /*

  describe('each Customer\'s subtab should have proper set of facets ', function() {
    CustomersTestParams.map(function(obj, i) {
      it(obj.tab + " tab should have the set of facets in certain order", function() {
        var tab    = element(by.css('.nav-tabs')).element(by.xpath('//a[@ui-sref="' + obj.uiSref + '"]'));
        var facets = element.all(by.tagName('facet-panel'));
        tab.click();
        facets.getText().then(function(f) {
          var optionsString = f.join(',').replace(/ +(?= )/g,'');
          var cleanFacets   = optionsString.split(',').filter(function(n) {return n != ''});
          expect(cleanFacets).toEqual(CustomersTestParams[i]['facets']);
        });
      })
    })
  });

  */
});


