(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('array', Array);

  /**
   * ng-repeat="item in items | _:'pluck':'title' | array:'join':', '" -> Title1, Title2, Title3
   * @returns {Function}
   * @constructor
   */
  function Array() {
    return function (array, method) {
      return Array.prototype[method].apply(array, Array.prototype.slice.call(arguments, 2));
    };
  }
})();