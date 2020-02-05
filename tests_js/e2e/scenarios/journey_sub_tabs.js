'use strict';

var LoginPage     = require("../pages/login_page");
var AppSwitcher   = require("../pages/app_switcher");
var MainMenu      = require("../pages/main_menu");

var JourneyFacetsParams = [
  {
    uiSref :'journeys.trends', tab : 'Trends', facets : [
    'All Journey Types',
    'All Channels',
    'All Journey Statuses',
    'All Segments',
    'All NPS'
    ]
  },
  {
    uiSref: 'journeys.distribution', tab: 'Distribution', facets: [
    'All Journey Types',
    'All Channels',
    'All Journey Statuses',
    'All Segments',
    'All NPS' ]
  },
  {
    uiSref: 'journeys.flow', tab: 'Flow', facets: [
    'All Journey Types',
    'All Channels',
    'All Segments',
    'All NPS'  ]
  },
  {
   uiSref: 'journeys.funnels', tab: 'Funnels', facets: [
    'All Channels',
    'All Journey Statuses',
    'All Segments',
    'All NPS' ]
  },
  {
  uiSref : 'journeys.details', tab: 'Details', facets: [
    'All Journey Types',
    'All Channels',
    'All Journey Statuses',
    'All Segments',
    'All NPS' ]
  },
  {
   uiSref : 'journeys.reports', tab: 'Reports', facets: []
  }
];

describe("Journey App", function() {

  var loginPage   = new LoginPage();
  var appCtxt     = new AppSwitcher();
  var mainMenu    = new MainMenu();


  beforeAll(function(){
    loginPage.login('/login');
    appCtxt.switch('QA');
    appCtxt.switch('Journey Analytics', false);
    mainMenu.switch('Journeys');
  });


  describe('subtabs should be present ', function() {
    JourneyFacetsParams.map(function(obj, i) {
      it(obj.tab + " tab should have proper ui-sref and title", function() {
         var tab = element(by.css('.nav-tabs')).element(by.xpath('//a[@ui-sref="' + obj.uiSref + '"]'));
         tab.getText().then(function(attr) {
           expect(attr.trim()).toEqual(JourneyFacetsParams[i]['tab']);
         });
      })
    })
  });



  /*

  describe('each subtab should have proper set of facets ', function() {
    JourneyFacetsParams.map(function(obj, i) {
      it(obj.tab + " tab should have the set of facets in certain order", function() {
        var tab    = element(by.css('.nav-tabs')).element(by.xpath('//a[@ui-sref="' + obj.uiSref + '"]'));
        var facets = element.all(by.tagName('facet-panel'));
        tab.click();
        facets.getText().then(function(f) {
          var optionsString = f.join(',').replace(/ +(?= )/g,'');
          var cleanFacets   = optionsString.split(',').filter(function(n) {return n != ''});
          expect(cleanFacets).toEqual(JourneyFacetsParams[i]['facets']);
        });
      })
    })
  });

  */

});


