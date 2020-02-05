(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('pluralize', pluralize);

  /**
   * pluralize:{'sing':'post', 'pl':'posts'}
   * @returns {Function}
   */
  function pluralize() {
    return function (num, text) {
      if (num === 1) {
        return num + ' ' + text.sing;
      } else {
        return num + ' ' + text.pl;
      }
    };
  }
})();