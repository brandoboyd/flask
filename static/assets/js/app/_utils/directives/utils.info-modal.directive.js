(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('slrInfoModal', slrInfoModal);

  /**
   * ARK UI bootstrap $modal to display the static content
   */
  /** @ngInject */
  function slrInfoModal($modal) {
    return {
      restrict: 'EA',
      scope: {
        template: '@slrInfoModal'
      },
      link: function (scope) {
        var settings = {
          scope: scope
        };

        if (scope.template.slice(-4) === 'html') {
          _.extend(settings, {templateUrl: scope.template});
        } else {
          _.extend(settings, {template: scope.template});
        }

        $modal.open(settings);
      }
    }
  }
})();