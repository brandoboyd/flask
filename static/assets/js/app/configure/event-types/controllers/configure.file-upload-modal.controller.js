(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('FileUploadCtrl', FileUploadCtrl);

  /** @ngInject */
  function FileUploadCtrl($scope, $modalInstance, _entityName, _uploadFunc, MetadataService, SystemAlert) {

    angular.extend($scope, {
      progress: 0,
      form: {
        separator: null,
        selectedFile: null,
      },
      uploadingFile: false,

      onImportFile: onImportFile,
      onUploadFile: onUploadFile,
      onCloseDialog: onCloseDialog,
      separtors: MetadataService.getCSVSeparators()
    });

    function onImportFile(files) {
      if(!files.length) return;
      $scope.form.selectedFile = files[0];
    }

    function onUploadFile() {
      $scope.uploadingFile = true;
      var params = {
        sep: $scope.form.separator,
        file: $scope.form.selectedFile,
        name: _entityName,
      };

      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _uploadFunc(params)
        .success(function(res) {
          SystemAlert.info('Uploaded file successfully!');
        })
        .catch(function(err) {
          SystemAlert.error('Failed to upload file!');
        })
        .finally(function() {
          $scope.uploadingFile = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    }

    function onCloseDialog() {
      $modalInstance.dismiss('cancel');
    };
  }
})();