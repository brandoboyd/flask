(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('EventsImportModalCtrl', EventsImportModalCtrl);

  /** @ngInject */
  function EventsImportModalCtrl($scope, $modalInstance, _channelId, _eventTypes, _uploadFunc, MetadataService, SystemAlert) {

    angular.extend($scope, {
      progress: 0,
      form: {
        separator: null,
        selectedFile: null,
        eventTypeName: null,
      },
      uploadingFile: false,
      fileType: null,

      onImportFile: onImportFile,
      onUploadFile: onUploadFile,
      onCloseDialog: onCloseDialog,
      canSubmit: canSubmit,

      eventTypes: _eventTypes,
      separtors: MetadataService.getCSVSeparators(),
      fileTypes: MetadataService.getDataFileTypes(),
    });

    function onImportFile(files) {
      if(!files.length) return;
      $scope.form.selectedFile = files[0];

      if (_.indexOf(['text/csv',  'application/vnd.ms-excel'], files[0].type) !== -1) {
        $scope.fileType = 'CSV';
      } else if (files[0].type === 'application/json') {
        $scope.fileType = 'JSON';
      }
    }

    function onUploadFile() {
      $scope.uploadingFile = true;
      var params = {
        channel_id: _channelId,
        name: $scope.form.eventTypeName,
        sep: $scope.form.separator,
        file: $scope.form.selectedFile,
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

    function canSubmit() {

      console.log("fileType" + $scope.fileType);

      if ($scope.fileType === 'JSON') {
        return true;
      } else if ($scope.fileType === 'CSV') {
        return (!!$scope.form.separator && $scope.form.selectedFile
          && !!$scope.form.eventTypeName);
      }
      return false;
    }

    function onCloseDialog() {
      $modalInstance.dismiss('cancel');
    };
  }
})();