(function () {
  'use strict';

  angular
    .module('slr.facet-panel')
    .directive('facetPanel', facetPanel);

  /** @ngInject */
  function facetPanel($timeout) {
    return {
      scope: {
        facetTitle: '@',
        facetTooltip: '@',
        facetOptions: '=',
        isAllChecked: '=facetIsAll',
        facetIsMulti: '=',
        facetSelected: '=',
        facetUpdateAction: '=',
        isOpen: '@',
        facetIsHidden: '='
      },
      restrict: 'E',
      templateUrl: '/static/assets/js/app/_components/facet-panel/components.facet-panel.html',
      link: function (scope, element, attrs, ngModel) {
        scope.facet = {
          selected: scope.facetSelected
        }
        scope.$watch('facet.selected', function (nVal, oVal) {
          if (nVal === oVal) return;
          scope.isAllChecked = !nVal;
          $timeout(function () {
            scope.facetSelected = nVal;
            scope.$apply();
            scope.facetUpdateAction();
          }, 0)
        }, true);

        scope.$watch('facetSelected', function (nVal, oVal) {
          if (nVal) {
            scope.facet.selected = nVal;
          }
        })

        scope.$watch('facetIsHidden', function (nVal, oVal) {
          if (nVal) {
            scope.isAllChecked = true;
          }
        })

        scope.$watch('facetOptions', function () {
          scope.updateFacet();
        }, true);

        scope.updateFacet = function () {
          if (scope.facetIsMulti) {
            var selected = _.filter(scope.facetOptions, function (item) {
              return item.enabled == true
            });
            selected.length > 0 ? scope.isAllChecked = false : scope.isAllChecked = true;
            scope.facetUpdateAction();

            if (scope.facetOptions && scope.facetOptions.length === selected.length && scope.facetOptions.length > 1) {
             scope.isAllChecked = true;
            }
          }

        };
        scope.$watch('isAllChecked', function (newVal) {
          if (newVal) {
            _.each(scope.facetOptions, function (item) {
              item.enabled = false;
            });

            if (!scope.facetIsMulti) {
              scope.facet.selected = null;
            } else {
              scope.facetUpdateAction();
            }

          } else {
            $timeout(function() {
              scope.isOpen = true
            }, 0);
          }
        })
      }
    };
  }
})();
