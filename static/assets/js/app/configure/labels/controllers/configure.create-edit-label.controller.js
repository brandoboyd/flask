(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditLabelCtrl', CreateEditLabelCtrl);

  /** @ngInject */
  function CreateEditLabelCtrl($scope, $routeParams, ContactLabel) {
    $scope.params = {};

    $scope.item_id = $routeParams.label_id;
    var contactLabelDefaults = {};
    if ($scope.item_id) {
      $scope.mode = 'edit';
      ContactLabel.get({id: $scope.item_id}, function (res) {
        $scope.item = res.item;
      });
    } else {
      $scope.mode = 'create';
      $scope.item = new ContactLabel();
      $scope.item = angular.extend($scope.item, contactLabelDefaults);
      //console.log('new smart tag', $scope.item);
    }

    $scope.title = {
      'create': 'Create',
      'edit': 'Update'
    }[$scope.mode];


    $scope.formState = {
      isSaved: false,
      isError: false
    };

    $scope.save = function () {
      $scope.formState.isSaved = false;

      ContactLabel.update($scope.item, function (res) {
        $scope.formState.isSaved = true;
        $scope.item = res.item;
        //$location.path('/tags/all/')
      });
    };

  }
})();