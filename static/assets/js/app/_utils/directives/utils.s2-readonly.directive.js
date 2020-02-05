(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('s2Readonly', s2Readonly);

  /** @ngInject */
  function s2Readonly($timeout) {
    return {
      restrict: "A",
      link: function (scope, iElement, iAttrs) {
        iAttrs.$observe('s2Readonly', function (value) {
          if (value == 'true') {
            $timeout(function () {
              iElement.select2(iAttrs.s2Readonly ? 'disable' : 'enable');
            }, 600, false)
          }
        });
      }
    }
  }
})();