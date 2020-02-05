(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('toggleResponsiveMenu', toggleResponsiveMenu);

  /** @ngInject */
  function toggleResponsiveMenu($timeout) {
    return {
      restrict: 'A',
      scope: {
        toggleResponsiveMenu: '@'
      },
      link: function (scope, elem) {
        elem.bind('click', function () {
          $timeout(function () {
            angular.element(scope.toggleResponsiveMenu).toggle();
          }, 100);
        });
      }
    }
  }
})();