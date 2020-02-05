(function () {
  'use strict';

  angular
    .module('slr.utils')
    .filter('_', Underscore);

  /**
   * ng-repeat="item in items | _:'unique'"
   * ng-repeat="item in items | _:'pluck':'title'"
   * @returns {Function}
   * @constructor
   */
  function Underscore() {
    return function (obj, method) {
      var args = Array.prototype.slice.call(arguments, 2);
      args.unshift(obj);
      return _[method].apply(_, args);
    };
  }
})();