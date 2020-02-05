'use strict';

var MainMenu = function() {

  var top_nav = element(by.css('.navbar-fixed-top')).all(by.css('.nav.navbar-nav')).first();
  var analysisButton = element(by.css('.nav-tabs.fixed-nav')).element(by.partialButtonText('Analysis'));

  this.switch = function(name) {
    element(by.linkText(name)).click();
  };

  this.getItemsList = function() {
    return top_nav.getText().then(function(text) {
      return text.split("\n");
    });
  };

  this.clickAnalysisButton = function() {
    analysisButton.click();
    var e = element(by.partialButtonText('Run Analysis'));
    expect(e.isPresent()).toBeTruthy();
  };
};

module.exports = MainMenu;
