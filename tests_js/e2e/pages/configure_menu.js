'use strict';

var ConfigureMenu = function() {
  this.getItemsList = function() {
    var menuItems = element(by.css('.nav-side-tabs')).all(by.xpath('//li[@ng-class]/a'));
    return menuItems.getText().then(function (text) {
      var optionsString = text.join(',').replace(/ +(?= )/g, '');
      return optionsString.split(',').filter(function (n) {
        return n != ''
      });
    });
  };
  this.switchByLink = function(link) {
    element(by.css('.nav-side-tabs')).element(by.css('a[href*="' + link + '"]')).click();
  }
};

module.exports = ConfigureMenu;