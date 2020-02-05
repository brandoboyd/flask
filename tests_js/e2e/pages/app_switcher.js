'use strict';

var AppSwitcher = function() {
  var settingsDropDown = element(by.css('.fonticon.icon-settings-gear')).element(by.xpath('..'));

  this.switch = function(app, redirectToSettings) {

    var appSwitcher      = settingsDropDown.element(by.xpath('..')).element(by.linkText(app));
    var settingsSwitcher = settingsDropDown.element(by.xpath('..')).element(by.linkText('Settings'));

    settingsDropDown.click();
    appSwitcher.click();

    if(redirectToSettings) {
      settingsDropDown.click();
      settingsSwitcher.click();
    }
  };

};

module.exports = AppSwitcher;