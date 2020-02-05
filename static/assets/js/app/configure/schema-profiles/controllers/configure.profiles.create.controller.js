(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateProfileCtrl', CreateProfileCtrl);

  /** @ngInject */

  /** @ngInject */
  function CreateProfileCtrl($scope, $modalInstance, toaster, _ProfileAccess, isAppending, MetadataService) {

    angular.extend($scope, {
      progress: 0,
      form: {
        separator: null,
        selectedFile: null,
      },
      uploadingFile: false,
      isAppending: isAppending,

      onImportFile: onImportFile,
      onUploadFile: onUploadFile,
      onCloseDialog: onCloseDialog,

      separtors: MetadataService.getCSVSeparators(),
    });

    function onImportFile(files) {
      if(!files.length) return;
      $scope.form.selectedFile = files[0];
    }

    function onUploadFile() {
      $scope.uploadingFile = true;
      var params = {
        'sep': $scope.form.separator,
        'csv_file': $scope.form.selectedFile,
        'type': isAppending? 'append': 'create'
      };

      var updateProgressBar = setInterval(function increase() {
        $scope.progress += 1;
        if ($scope.progress > 100) {
          $scope.progress = 0;
        }
        $scope.$digest();
      }, 30);

      _ProfileAccess.save(params)
        .then(function(res) {
          if (isAppending) {
            toaster.pop('info', 'Appended data successfully.');
          } else {
            toaster.pop('info', 'Created profile successfully.');
          }
        })
        .catch(function(err) {
          toaster.pop('error', 'Failed to create/append profile.');
        })
        .finally(function() {
          $scope.uploadingFile = false;
          clearInterval(updateProgressBar);
          $modalInstance.close();
        });
    }

    function onCloseDialog() {
      $modalInstance.dismiss('cancel');
    }
  }
})();