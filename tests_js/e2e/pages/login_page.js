'use strict';

var LoginPage = function() {
  this.login = function(url) {
    browser.get(url);
    element(by.id('email')).sendKeys('super_user@solariat.com');
    element(by.id('password')).sendKeys('password');
    element(by.buttonText('Log In')).click();
    /*
     with 'password' password we display a warning dialog which will prevent
     any click events to come through it;
     we need to make sure it's dismissed before other tests
     */
    element(by.buttonText('Dismiss')).click();
    browser.sleep(500);
  };
};

module.exports = LoginPage;