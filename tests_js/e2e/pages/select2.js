'use strict';

var Select2Widget = function() {
  this.addTag = function(selectId, tagName) {
    var configurableApps = element(by.css('div#' + selectId));
    configurableApps.click();
    var lis = element.all(by.css('li.select2-results-dept-0'));
    var app_option = lis.filter(function(li) {
      return li.getText().then(function(optionName) {
        return optionName == tagName
      })
    });
    app_option.click();
  };

  this.removeTag = function(selectId, tagName) {
    var configuredApp = element(by.css('div#' + selectId))
      .all(by.css('.select2-search-choice'))
      .filter(function(app) {
        return app.element(by.tagName('div')).getText().then(function(_name) {
          return _name == tagName;
        })
      });
    configuredApp.first().element(by.tagName('a')).click();
  };

  this.getTagsList = function(selectId) {
    var menuItems = element(by.css('div#' + selectId)).all(by.css('.select2-search-choice'));
    return menuItems.getText().then(function (text) {
      var optionsString = text.join(',').replace(/ +(?= )/g, '');
      return optionsString.split(',').filter(function (n) {
        return n != ''
      });
    });
  };

};

module.exports = Select2Widget;
