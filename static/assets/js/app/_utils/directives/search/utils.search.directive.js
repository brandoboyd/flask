(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('search', search);

  /** @ngInject */
  function search() {
    return {
      restrict: 'E',
      scope: {
        filter: '=',
        placeholderText: '@',
        control: '=?'
      },
      templateUrl: '/static/assets/js/app/_utils/directives/search/utils.search.directive.html',
      link: function (scope) {
        scope.isReloadShown = angular.isDefined(scope.control);
        scope.reload = function () {
          if (angular.isDefined(scope.control)) {
            scope.control();
          }
        }
      }
    }
  }
})();