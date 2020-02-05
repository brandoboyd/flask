(function () {
  'use strict';

  var dependencies = [
      'ngSanitize',
      'ngRoute',
      'ui.router',
      'ngResource',
      'ng-drag-scroll',
    
      'slr.components'
  ];
  angular
    .module('omni', dependencies)

    .filter("unwrapAsHtml", function () {
        return function (items) {
            var html = "";
            _(_.unique(items)).each(function (item) {
                html += "- " + item + "<br>";
            });
            return html;
        };
    })

    .filter("countUniqueIndustries", function () {
        return function (industries) {
            return _.unique(industries).length;
        };
    })

    .filter("countUniqueAgents", function () {
        return function (journeys) {
            return _.union.apply(_, _.pluck(journeys, 'agents')).length;
        };
    })

    .filter("countUniqueCustomers", function () {
        return function (journeys) {
            return _.unique(_.pluck(journeys, 'customer_id')).length;
        };
    })

    .value('uiJqConfig', {
        tooltip: {
            animation: false,
            placement: 'bottom',
            container: 'body'
        }
    })

    .controller('InteractionCtrl', function ($scope, $modalInstance, events) {
        $scope.events = events.list;

        $scope.close = function () {
            $modalInstance.dismiss('close');
        };
    })
})();
