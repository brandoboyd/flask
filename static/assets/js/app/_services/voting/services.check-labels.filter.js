(function () {
  'use strict';

  angular
    .module('slr.services')
    .filter('check_label', check_label);

  /** @ngInject */
  function check_label(FilterService) {
    var labels = FilterService.getIntentions();
    return function (input) {
      if (!input) return input;
      return _.find(labels, function (el) {
        return el.label == input.toLowerCase()
      })['display']
    };
  }
})();