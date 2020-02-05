(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaPredictorsCtrl', SchemaPredictorsCtrl);

  /** @ngInject */
  function SchemaPredictorsCtrl($scope, $http, toaster, AccountsService, Utils, $modal) {

    var init = function () {
      $scope.account = AccountsService.getCurrent();

      $http.get("/account/predictor-configuration/" + $scope.account.id)
        .success(function (response) {
          $scope.schemaList = response.data;
        })
        .error(function (data) {
          toaster.pop('error', data);
        });
    };

    $scope.showPredictorConfiguration = function (name, schema) {
      if (!$scope.schemaList) return;
      var dialogScope = $scope.$new();
      dialogScope.account = $scope.account;

      dialogScope.predictorObj = {
        data: schema,
        options: {
          name: name,
          mode: 'tree',
          // sort objects alphabetically because python dictionary doesn't preserve the order
          // for some reason, this is causing problem, and showing empty Object
          //sortObjectKeys: true
        }
      };

      var oldConfiguration = angular.copy(dialogScope.predictorObj.data);
      dialogScope.predictorConfigurationError = false;

      var modalInstance = $modal.open({
        scope: dialogScope,
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/schema-predictors/predictor-configuration'
      });

      // detect invalid json and disable 'save' button
      dialogScope.editorLoaded = function (jsonEditor) {
        // onChange and onError couldn't be configured in predictorObj.options configuration
        // so define them here
        // but it's overriding some default behavior, thereby not working at all
        //jsonEditor.options.onChange = function () {
        //  $timeout(function () {
        //    $scope.predictorConfigurationError = false;  // reset flag
        //    console.log('onChange');
        //  }, 10);
        //};
        //jsonEditor.options.onError = function (err) {
        //  $timeout(function () {
        //    $scope.predictorConfigurationError = true;
        //    console.log('onError', err);
        //  }, 20);
        //};
      };

      dialogScope.canPredictorConfigurationBeSaved = function () {
        if (angular.equals(oldConfiguration, dialogScope.predictorObj.data)) {
          return false;
        }
        return !dialogScope.predictorConfigurationError;
      };

      dialogScope.savePredictorConfiguration = function () {
        oldConfiguration = angular.copy(dialogScope.predictorObj.data);

        $scope.schemaList[name] = oldConfiguration;

        $http.post("/account/predictor-configuration/" + dialogScope.account.id, $scope.schemaList)
          .success(function () {
            toaster.pop('success', "Default predictor configuration for this account saved.");
            modalInstance.close();
          });
      };

    };

    init();
  }
})();