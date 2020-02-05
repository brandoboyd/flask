(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventsCtrl', EventsCtrl);

  /** @ngInject */
  function EventsCtrl($scope, FilterService, EventsList) {

    $scope.filters = {
      'title': '',
      'limit': 30,
      'offset': 0
    };

    $scope.events = [];
    $scope.noEventsAlert = false;
    $scope.filters.currentPage = 0;
    $scope.pages = 0;
    $scope.maxSize = 10;

    $scope.loadEvents = function (dates) {
      $scope.dateRange = dates || FilterService.getDateRange();
      var params = {
        offset: $scope.filters.offset,
        limit: $scope.filters.limit,
        filter: {'title': $scope.filters.title}
      };
      EventsList.list(params).then(
        function (res) {
          $scope.events = res.list;
          $scope.noEventsAlert = $scope.events.length == 0;
          $scope.filters.offset = res.offset;
          $scope.filters.limit = res.limit;
          $scope.size = res.size;
          var pages = res.size / res.limit;
          $scope.pages = Math.ceil(pages);
        },
        function (d) {
          $scope.noEventsAlert = true;
        }
      );
    }

    $scope.setPage = function () {
      $scope.filters.offset = (parseInt($scope.filters.limit) * ($scope.filters.currentPage - 1));
      $scope.loadEvents();
    }

    $scope.loadEvents();

  }
})();