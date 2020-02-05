(function () {
  'use strict';

  angular
    .module('slr.utils')
    .directive('sorter', sorter);

  function sorter() {
    var template = "<a style=\"width: 100%;display: block;\" " +
      "ng-click=\"onClick()\">" +
      "<span class=\"pull-left\">" +
      "{{ title }}" +
      "&nbsp;<span ng-if='questionTooltip' class='icon-iw-active-circle-question' tooltip='{{questionTooltip}}' tooltip-placement='top'>&nbsp;" +
      "</span>" +
      "<span class=\"pull-right\">" +
      "<i class=\"icon-search-previous\" ng-show=\"!isArrShown\"></i>" +
      "<i class=\"icon-search-next\" ng-show=\"isArrShown\"></i>" +
      "</span></a>";

    return {
      template: template,
      scope: {
        title: '@title',
        questionTooltip: '@questionTooltip',
        predicate: '@predicate',
        sorter: '='
      },
      link: function (scope, el, attrs) {
        el.addClass("nowrap");

        var pred = scope.predicate,
          tableState = scope.sorter || scope.$parent.table.sort;
        scope.isArrShown = false;

        angular.extend(scope, {
          onClick: function () {
            tableState.predicate = pred;
            tableState.reverse = !tableState.reverse;
            scope.isArrShown = !scope.isArrShown;
          }
        });
      }
    }
  }
})();