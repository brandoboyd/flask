(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventViewCtrl', EventViewCtrl);

  /** @ngInject */
  function EventViewCtrl($scope, $routeParams, EventsList) {
    $scope.event_id = $routeParams.event_id;
    EventsList.getById($scope.event_id).then(function (res) {
      $scope.item = res;
    });

  }
})();