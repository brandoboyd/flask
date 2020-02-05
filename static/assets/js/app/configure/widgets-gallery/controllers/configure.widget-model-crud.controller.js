(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('WidgetModelCRUDCtrl', WidgetModelCRUDCtrl);

  /** @ngInject */
  function WidgetModelCRUDCtrl($scope, $http, $location, $routeParams) {

    var id = $routeParams.id;
    $scope.title = id ? 'Update' : 'Create';
    $scope.gallery_id = $routeParams.gallery_id;
    $scope.model = {};
    $scope.formState = {};
    var url = '/gallery/' + $scope.gallery_id + '/widget_models';

    if (id) {
      $http.get(url + '/' + id)
        .then(function (resp) {
          $scope.model = resp.data.data;
          $scope.model.settings = JSON.stringify($scope.model.settings, null, 4);
        })
    } else {
      $scope.model = {
        title: "",
        description: "",
        settings: ""
      };
    }

    $scope.save = function () {
      function modelSaved(resp) {
        $scope.model = resp.data;
        $scope.model.settings = JSON.stringify($scope.model.settings, null, 4);
        $scope.formState.isSaved = true;
        $scope.formState.hasError = false;
        $scope.title = 'Update';
        if (!id) {
          $location.path('/gallery/' + $scope.gallery_id);  
        }
      }

      function modelNotSaved() {
        $scope.formState.hasError = true;
        $scope.model.settings = JSON.stringify($scope.model.settings, null, 4);
      }

      $scope.formState.isSaved = false;

      try {
        $scope.model.settings = JSON.parse($scope.model.settings);
        if (id) {
          $http.put(url + '/' + id, $scope.model)
            .success(modelSaved)
            .error(modelNotSaved);
        } else {
          $http.post(url, $scope.model)
            .success(modelSaved)
            .error(modelNotSaved);
        }
      } catch (e) {
        $scope.formState.hasError = true;
        console.log('Invalid JSON');
      }
    };
  }
})();