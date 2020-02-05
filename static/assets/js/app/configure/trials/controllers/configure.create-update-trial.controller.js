(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateTrialCtrl', CreateUpdateTrialCtrl);

  /** @ngInject */
  function CreateUpdateTrialCtrl($location, $log, $scope, SystemAlert, Trial) {
    var clear = function () {
      $scope.item = Trial.create();
    };
    clear();

    $scope.pattern = {
      EMAIL_REGEXP: /^[a-z0-9!#$%&'*+/=?^_`{|}~.-]+@[a-z0-9-]+(\.[a-z0-9-]+)+$/i,
      ACCOUNT_REGEXP: /^[a-zA-Z0-9-_()]+$/  // sync with db.account.ACCOUNT_NAME_RE
    };

    $scope.options = {
      start_date: {dateFormat: 'mm/dd/yy', minDate: new Date()},
      end_date: {dateFormat: 'mm/dd/yy', minDate: new Date(+new Date() + 24 * 60 * 60 * 1000)}
    };

    $scope["get"] = function (id) {
      return Trial.resource.get({id: id}).$promise.then(function (item) {
        $scope.item = Trial.create(item);
        return item;
      });
    };

    $scope.save = function () {
      Trial.resource.save($scope.item, function () {
        SystemAlert.success("Trial invitation was sent successfully!", 5000);
        clear();
        $scope.trialForm.$setPristine();
        $scope.redirectAll();
      });
    };


    $scope.redirectAll = function () {
      $location.path('/trials/');
    };
  }
})();