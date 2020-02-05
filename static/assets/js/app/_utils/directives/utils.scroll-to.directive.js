(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('scrollTo', scrollTo);

  // TODO: this directive could be flexible, if you pass Selector. Currently it always scrolls to ng-repeat  
  /** @ngInject */
  function scrollTo() {
    return {
      scope: {
        scrollTo: '=',
        highlightClass: '@'
      },
      link: function (scope, el, attrs) {
        function scrollToIndex(idx) {
          var $scrollToEl = angular.element(el).find('div[ng-repeat]').eq(idx);
          var $scrollView = angular.element(el);
          $scrollView.scrollTo($scrollToEl.offset().top - $scrollView.offset().top);
          if (attrs.highlightClass) {
            $scrollToEl.addClass(attrs.highlightClass);
          }
        }

        scope.$watch('scrollTo', function (val) {
          if (angular.isNumber(val) && val > -1) {
            scrollToIndex(val);
          }
        });
      }
    };
  }
})();