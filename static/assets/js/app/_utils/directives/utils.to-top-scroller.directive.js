(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('toTopScroller', toTopScroller);

  /** @ngInject */
  function toTopScroller($location, $anchorScroll) {
    return {
      restrict: 'A',
      link: function (scope, elem) {
        angular.element(document).scroll(function () {
          var y = angular.element(this).scrollTop();
          var navWrap = $('#top').offset().top;
          if (y - 200 > navWrap) {
            angular.element('.to-top-scroller').show()
          } else {
            angular.element('.to-top-scroller').hide()
          }
        });

        elem.on('click', function () {
          $location.hash('top');
          $anchorScroll();
        });
      }
    }
  }
})();