describe('slr.configure.SchemaProfileDiscoveryCtrl', function () {
  var $scope;
  var $modal;
  var toaster;
  var SchemaProfilesRest;
  var createController;
  var $q;
  var deferred;
  var $httpBackend;

  beforeEach(angular.mock.module('slr.configure'));

  beforeEach(angular.mock.inject(function (_$q_, $controller, _$rootScope_, _$httpBackend_, _toaster_, _SchemaProfilesRest_) {
    $q = _$q_;
    $scope = _$rootScope_.$new();
    $httpBackend = _$httpBackend_;
    deferred = _$q_.defer();

    toaster = _toaster_;
    SchemaProfilesRest = new _SchemaProfilesRest_();

    $scope.ProfileAccess = SchemaProfilesRest;
    $modal = { open: function() {}, close : function() {}, dismiss: function(){} };


    $httpBackend.whenGET(/\/view\/.*/).respond(200, '');

    createController = function(isAppending) {
      return $controller('SchemaProfileDiscoveryCtrl', {
        $scope: $scope,
        toaster : toaster,
        SchemaProfilesRest: _SchemaProfilesRest_,
        isAppending: isAppending,
        $modal : $modal
      });
    };

    $httpBackend.whenGET(/view\/fieldName.*/).respond(200, '');

    spyOn($modal, 'open');
    spyOn(toaster, 'pop');
    spyOn(SchemaProfilesRest, 'save').and.returnValue(deferred.promise);
    spyOn(_SchemaProfilesRest_.prototype, 'fetchFieldData').and.returnValue(deferred.promise);


  }));


  it('$scope.showDetails should call $modal.open', function () {
    createController(true);
    $scope.showDetails();
    expect($modal.open).toHaveBeenCalledWith({
      scope: jasmine.anything(),
      size: 'lg',
      templateUrl: 'static/assets/js/app/configure/datasets/templates/configure.datasets.column-values.html'
    });
  });

  it('$scope.showData should call $modal.open', function () {
    createController(true);
    $scope.showData();

    deferred.resolve({data: {list:[], total_items:0}});
    $scope.$apply();

    expect($modal.open).toHaveBeenCalled();
    expect(SchemaProfilesRest.fetchFieldData).toHaveBeenCalled();
  });




  describe('$scope.onAppendData should call $scope.ProfileAccess.save', function() {
    beforeEach(function() {
      createController(true);
      $scope.form = {selectedFile: 'file1'};
      $scope.onAppendData();
      spyOn($scope, '$emit');
    });

    it(' when success callback triggered, the scope should emit and toaster should pop with "Append..." message ', function() {
      deferred.resolve();
      $scope.$apply();
      expect($scope.ProfileAccess.save).toHaveBeenCalled();
      expect(toaster.pop).toHaveBeenCalledWith('info', 'Appended data successfully.');
      expect($scope.$emit).toHaveBeenCalledWith('START_REFRESH');
    });

    it(' when error/catch callback triggered, and the scope should NOT emit and toaster should NOT pop', function() {
      deferred.reject();
      $scope.$apply();
      expect($scope.ProfileAccess.save).toHaveBeenCalled();
      expect(toaster.pop).not.toHaveBeenCalled();
      expect($scope.$emit).not.toHaveBeenCalled();
    })

  });

  it('onSelectRow called without argument should select/deselect all rows ', function() {
    createController(true);
    $scope.profile = { discovered_schema : [{name:'field1'}, {name:'field2'}]};
    $scope.flags = { selectedAll : true };
    $scope.onSelectRow();
    expect($scope.flags.selectedAll).toEqual(false);
    expect($scope.selectedRows.length).toEqual(0)

    $scope.flags = { selectedAll : false };
    $scope.onSelectRow();
    expect($scope.selectedRows.length).toEqual(2)
  });

  it('onSelectRow when passed a schema field name should add or remove the item to/from selectedRows depending if it was already in the list', function() {
    createController(true);

    $scope.profile = { discovered_schema : [{name:'field1'}, {name:'field2'}]};
    $scope.flags = { selectedAll : true };
    $scope.onSelectRow({name:'field1'});
    expect($scope.selectedRows.length).toEqual(1);
    $scope.onSelectRow({name:'field1'});
    expect($scope.selectedRows.length).toEqual(0);
  });

  it("loadProfileSuccess", function() {
    ctrl = createController(true);
    $scope.profile = {
      cardinalities : {field1 : 1, field2: 2},
      discovered_schema : [{name:'field1'}, {name:'field2'}, {name:'field3'}]
    };


    ctrl.isRefreshing = true;
    $scope.profile.status = 'LOADED';
    $scope.profile.sync_status = 'OUT_OF_SYNC';
    $scope.$apply();

    $scope.$emit('LOAD_PROFILE_SUCESS');



    expect($scope.isFetching).toEqual(false);
    expect(ctrl.isRefreshing).toEqual(false);


  })

});



