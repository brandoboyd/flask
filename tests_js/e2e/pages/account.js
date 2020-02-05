'use strict';

var Account = function() {
  this.create = function(accountName) {
    var createAccountBtn = element(by.css('a[href*="#/new_account"]'));

    createAccountBtn.click();
    //Fill in the name
    element(by.model('account.name')).clear().sendKeys(accountName);
    element(by.buttonText('Create')).click();
  };

  this.activateAccount = function(accountName) {
    var settingsDropDown = element(by.css('.fonticon.icon-settings-gear')).element(by.xpath('..'));
    var accSwitcher      = settingsDropDown.element(by.xpath('..')).element(by.linkText(accountName));
    settingsDropDown.click();
    accSwitcher.click();
  }

  this.locateAccountLinkByName = function(accountName) {
    return element.all(by.repeater('account in accounts').column('account.name')).filter(function(item) {
      return item.getText().then(function(label) {
        return label === accountName;
      });
    });
  };


};

module.exports = Account;
