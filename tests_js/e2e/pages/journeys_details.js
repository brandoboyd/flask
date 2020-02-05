'use strict';

var JourneysDetails = function () {

  var detailsList = element.all(by.repeater('journeys.table_data'));

  this.verifySubTabTitle = function(title) {
    expect(element(by.tagName('h1')).getText()).toEqual(title);
  };

  this.verifyNumberOfItemsList = function(expectedSize) {
    expect(detailsList.count()).toEqual(expectedSize);
  };
};

module.exports = JourneysDetails;
