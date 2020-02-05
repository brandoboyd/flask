'use strict';

var LoginPage     = require("../pages/login_page");
var AppSwitcher   = require("../pages/app_switcher");
var MainMenu      = require("../pages/main_menu");

var AgentTestParams = [
  {
    uiSref: 'agents.distribution', tab: 'Distribution', facets: [
    'All Age Groups'
  ]
  },
  {
    uiSref: 'agents.details', tab: 'Details', facets: [
    'All Age Groups'
    ]
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
    mainMenu.switch('Agents');
  });


  describe('Agents should have the following subtabs present ', function() {
    AgentTestParams.map(function(obj, i) {
      it(obj.tab + " tab should have proper ui-sref and title", function() {
        var tab = element(by.css('.nav-tabs')).element(by.xpath('//a[@ui-sref="' + obj.uiSref + '"]'));
        tab.getText().then(function(attr) {
          expect(attr.trim()).toEqual(AgentTestParams[i]['tab']);
        });
      })
    })
  });

/*
  describe('each Agents subtab should have proper set of facets ', function() {
    AgentTestParams.map(function(obj, i) {
      it(obj.tab + " tab should have the set of facets in certain order", function() {
        var tab    = element(by.css('.nav-tabs')).element(by.xpath('//a[@ui-sref="' + obj.uiSref + '"]'));
        var facets = element.all(by.tagName('facet-panel'));
        tab.click();
        facets.getText().then(function(f) {
          var optionsString = f.join(',').replace(/ +(?= )/g,'');
          var cleanFacets   = optionsString.split(',').filter(function(n) {return n != ''});
          expect(cleanFacets).toEqual(AgentTestParams[i]['facets']);
        });
      })
    })
  });
*/
});


