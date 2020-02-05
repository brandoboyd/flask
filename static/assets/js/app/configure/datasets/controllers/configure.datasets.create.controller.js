(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateDatasetCtrl', CreateDatasetCtrl);

  /** @ngInject */

  /** @ngInject */
  function CreateDatasetCtrl($scope, $modalInstance, toaster, _saveFunc, MetadataService, datasetName, isAppending) {
    $scope.datasetName = datasetName || '';
    $scope.isAppending = isAppending;
    $scope.separator = null;
    $scope.selectedFile = null;
    $scope.uploading = false;
    $scope.progress = 0;

    $scope.separtors = MetadataService.getCSVSeparators();

    $scope.import = function (files) {
      if(!files.length) return;
      $scope.selectedFile = files[0];
    }

    $scope.createOrAppend = function () {
      var params = {
        'name': $scope.datasetName,
        'csv_file': $scope.selectedFile,
        'sep': $scope.separator,
        'type': isAppending? 'append': 'create',
      };

      $scope.uploading = true;
      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _saveFunc(params)
        .then(function() {
          if (isAppending) {
            toaster.pop('info', 'Appended data successfully.');
          } else {
            toaster.pop('info', 'Created successfully.');
          }
        })
        .catch(function(err) {
          console.log('Dataset create/append failed! ', err);
        })
        .finally(function() {
          $scope.uploading = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    };

    $scope.cancel = function () {
      $modalInstance.dismiss('cancel');
    };
  }
})();