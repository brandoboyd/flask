(function () {
  'use strict';

  angular
    .module('slr.ng-confirm')
    .directive('ngConfirm', ngConfirm);

  /** @ngInject */
  function ngConfirm(PopupService) {
    return {
      restrict: 'EA',
      link: function postLink(scope, element, attrs) {
        // Could have custom or boostrap modal options here
        var popupOptions = {closeAfterAction: true};
        element.bind("click", function () {
          var showFn = function () {
              return scope.$eval(attrs["showIf"])
            },
            actionFn = function () {
              return scope.$eval(attrs["actionFunction"])
            },
            show = showFn();
          if (show === true || show === undefined) {
            PopupService.confirm(attrs["title"], attrs["actionText"],
              attrs["actionButtonText"], attrs["actionFunction"],
              attrs["cancelButtonText"], attrs["cancelFunction"],
              scope, popupOptions);
          } else {
            angular.isFunction(actionFn) && actionFn();
          }
        });
      }
    };
  }
})();