(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('toTitleCase', toTitleCaseFilter);

  /**
   * 'customer gender' | toTitleCase -> Customer gender
   * @param Utils
   * @returns {Function}
   */
  /** @ngInject */
  function toTitleCaseFilter(Utils) {
    return function (str) {
      if (str) {
        return Utils.toTitleCase(str.replace(/[_-]/g, ' ')).replace('Id', '');
      }
    }
  }
})();