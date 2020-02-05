describe('slr.configure.CreateProfileCtrl', function () {
  var $scope;
  var $modalInstance;
  var toaster;
  var _ProfileAccess;
  var createController;
  var $q;
  var deferred;


  beforeEach(angular.mock.module('slr.configure'));

  beforeEach(angular.mock.inject(function (_$q_, $controller, _$rootScope_, _toaster_, SchemaProfilesRest) {
    $q = _$q_;
    $scope = _$rootScope_.$new();
    deferred = _$q_.defer();

    toaster = _toaster_;
    _ProfileAccess = new SchemaProfilesRest();
    $modalInstance = { close : function() {}, dismiss: function(){} };

    createController = function(isAppending) {
      return $controller('CreateProfileCtrl', {
              $scope: $scope,
              $modalInstance: $modalInstance,
              toaster : toaster,
              _ProfileAccess: _ProfileAccess,
              isAppending: isAppending,
              MetadataService : { getCSVSeparators : function() {return ''}}
            });
    };

    spyOn(_ProfileAccess, 'save').and.returnValue(deferred.promise);
    spyOn($modalInstance, 'close');
    spyOn($modalInstance, 'dismiss');
    spyOn(toaster, 'pop');

  }));


  it('onImportFile called with empty files list should do nothing', function () {
    createController(true);
    $scope.onImportFile([]);
    expect($scope.form.selectedFile).toBeNull();
  });

  it('onImportFile called with non-empty list should set $scope.form.selectedFile to first element from the list', function () {
    createController(true);
    $scope.onImportFile(['file1', 'file2', 'file3']);
    expect($scope.form.selectedFile).not.toBeNull();
    expect($scope.form.selectedFile).toEqual('file1');
  });

  it('onUploadFile should set $scope.uploadingFile to true', function() {
    createController(true);
    $scope.onUploadFile();
    expect($scope.uploadingFile).toBeTruthy();
  });

  it('onCloseDialog should call $modalInstance.dismiss()', function() {
    createController(true);
    $scope.onCloseDialog();
    expect($modalInstance.dismiss).toHaveBeenCalledWith('cancel');
  });

  describe('onUploadFile should call _ProfileAccess.save', function() {
    it('with \'success\' callback triggered, and it should pop the "Append..." message', function() {
      createController(true);
      $scope.onUploadFile();
      deferred.resolve();
      $scope.$apply();
      expect(_ProfileAccess.save).toHaveBeenCalled();
      expect($scope.isAppending).toBeTruthy();
      expect(toaster.pop).toHaveBeenCalledWith('info', 'Appended data successfully.');
      expect($modalInstance.close).toHaveBeenCalled();
    });

    it('with \'success\' callback triggered, and it should pop the "Create..." message', function() {
      createController(false);
      $scope.onUploadFile();
      deferred.resolve();
      $scope.$apply();
      expect(_ProfileAccess.save).toHaveBeenCalled();
      expect(toaster.pop).toHaveBeenCalledWith('info', 'Created profile successfully.');
      expect($modalInstance.close).toHaveBeenCalled();
    });

    it('with \'catch\' callback triggered and it should pop the "Failed..." message', function() {
      createController(true);
      $scope.onUploadFile();
      deferred.reject();
      $scope.$apply();
      expect(_ProfileAccess.save).toHaveBeenCalled();
      //expect(isAppending).toBeTruthy();
      expect(toaster.pop).toHaveBeenCalledWith('error', 'Failed to create/append profile.');
      expect($modalInstance.close).toHaveBeenCalled();
    });
  })
});



