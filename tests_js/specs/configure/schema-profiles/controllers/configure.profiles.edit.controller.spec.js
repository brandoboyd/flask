describe('slr.configure.SchemaProfileCtrl', function () {
  var $scope;
  var $rootScope;
  var createController;
  var SchemaProfilesRest;
  var $q;
  var deferred;
  var $httpBackend;
  var MetadataService;
  var toaster;
  var $modalMock;
  var $modal;

  beforeEach(angular.mock.module('slr.configure'));

  beforeEach(angular.mock.inject(function (_$q_, $controller, _$rootScope_, _$httpBackend_, _$modal_, _toaster_, _SchemaProfilesRest_, _MetadataService_) {
    $q = _$q_;
    deferred = _$q_.defer();
    $scope = _$rootScope_.$new();
    $rootScope = _$rootScope_;
    $httpBackend = _$httpBackend_;
    toaster = _toaster_;

    SchemaProfilesRest = _SchemaProfilesRest_;
    $scope.ProfileAccess = new _SchemaProfilesRest_();

    MetadataService = _MetadataService_;
    //$modalMock = { open: function() {}, close : function() {}, dismiss: function(){} };
    $modal = _$modal_;

    $httpBackend.whenPOST('/sync/cancel').respond(200, '');

    createController = function(entityType) {
      return $controller('SchemaProfileEditCtrl', {
        $scope: $scope,
        //$modal :$modal,
        toaster : toaster,
        SchemaProfilesRest: _SchemaProfilesRest_,
        MetadataService : _MetadataService_

      });
    };

    spyOn(_SchemaProfilesRest_.prototype, 'updateSchema').and.returnValue(deferred.promise);
    spyOn(_SchemaProfilesRest_.prototype, 'applySchema').and.returnValue(deferred.promise);
    spyOn(_SchemaProfilesRest_.prototype, 'acceptSchema').and.returnValue(deferred.promise);
    spyOn(_SchemaProfilesRest_.prototype, 'cancelSchema').and.returnValue(deferred.promise);
    spyOn(_MetadataService_, 'getBeautifiedStatus');
    spyOn(toaster, 'pop');
    spyOn($scope, '$emit').and.callThrough();
    spyOn($scope, '$broadcast').and.callThrough();
    spyOn(_$modal_, 'open');
  }));

  it("onSaveSchema", function() {
    createController();
    $scope.profile = { schema: []};
    $scope.onSaveSchema();
    deferred.resolve();
    $scope.$apply();

    expect($scope.ProfileAccess.updateSchema).toHaveBeenCalled();
    expect(toaster.pop).toHaveBeenCalledWith('info', 'Updated schema successfully.');
  });

  it("onAddField", inject(function($timeout) {

    spyOn(angular, 'element').and.callThrough();
    createController();

    $scope.profile = { schema: [{name:'field1'}]};

    var event = jasmine.createSpyObj('event', [ 'preventDefault' ]);

    $scope.onAddField(event);
    expect(event.preventDefault).toHaveBeenCalled();

    // flush timeout(s) for all code under test.
    $timeout.flush();
    // this will throw an exception if there are any pending timeouts.
    $timeout.verifyNoPendingTasks();

    expect(angular.element).toHaveBeenCalled();
    console.log(angular.element.calls.allArgs());
    expect(angular.element.calls.argsFor(0)).toEqual(['.field-1 a']);

  }));

  it("onRemoveField", function() {
    createController();
    $scope.wrapper = { id_field : 'field1'};
    $scope.profile = { schema: [{name: 'field1'}]};

    var event = jasmine.createSpyObj('event', [ 'preventDefault' ]);

    $scope.onRemoveField(event, 0);
    expect(event.preventDefault).toHaveBeenCalled();
    expect($scope.wrapper.id_field).toBe(null);
  });

  it("onFieldNameInput - mark the filed as expression if no matching type found", function() {
    createController();
    $scope.profile = { schema: [{name: 'field1'}]};
    $scope.onFieldNameInput(0);
    expect($scope.profile.schema[0].is_expression).toBeTruthy();
  });

  it("onFieldNameInput - assign proper type to a schema field from discovered schema", function() {
    createController();
    $scope.availableFields = ['field1'];
    $scope.profile = { schema: [{name: 'field1'}]};
    $scope.profile.discovered_schema = [{name: 'field1', type: 'type1'}];
    $scope.onFieldNameInput(0);
    expect($scope.profile.schema[0].is_expression).toBeFalsy();
    expect($scope.profile.schema[0].type).toEqual('type1');
  });


  it("onFieldNameInput - reset field type to null if no corresponding field found in discovery schema", function() {
    createController();
    $scope.availableFields = ['field1'];
    $scope.profile = { schema: [{name: 'field1'}]};
    $scope.profile.discovered_schema = [{name: 'field3', type: 'type3'}];
    $scope.onFieldNameInput(0);
    expect($scope.profile.schema[0].is_expression).toEqual(undefined);
    expect($scope.profile.schema[0].type).toEqual(null);
  });

  it("onApplySchema", inject(function($timeout) {
    createController();
    $scope.profile = { sync_status : null};
    $scope.onApplySchema();

    expect($scope.ProfileAccess.applySchema).toHaveBeenCalled();
    expect($scope.profile.sync_status).toEqual('SYNCING');
    expect(toaster.pop).toHaveBeenCalledWith('info', 'Synchronization started.');


    $timeout.flush();
    $timeout.verifyNoPendingTasks();

    expect($scope.$emit).toHaveBeenCalledWith('START_REFRESH');

  }));


  it("onAcceptSchema", function() {
    createController();
    $scope.onAcceptSchema();

    deferred.resolve();
    $scope.$apply();

    expect($scope.ProfileAccess.acceptSchema).toHaveBeenCalled();
    expect(toaster.pop).toHaveBeenCalledWith('info', 'Accepted schema successfully.');
    expect($scope.$emit).toHaveBeenCalledWith('LOAD_PROFILE');

  });

  it("onCancelSchema", function() {
    createController();
    $scope.onCancelSchema();

    deferred.resolve();
    $scope.$apply();

    expect($scope.ProfileAccess.cancelSchema).toHaveBeenCalled();
    expect(toaster.pop).toHaveBeenCalledWith('info', 'Cancelled schema successfully.');
    expect($scope.$emit).toHaveBeenCalledWith('LOAD_PROFILE');

  });


  it("searchExpressions - matching results", function() {
    createController();
    $scope.originalFields = ['field1'];
    $scope.searchExpressions('field1');

    expect($scope._availableFields).toEqual(['field1'])

  });

  it("searchExpressions - no matching results", function() {
    createController();
    $scope.originalFields = ['field1'];
    $scope.searchExpressions('field2');

    expect($scope._availableFields).toEqual([])

  });


  it("onShowErrors", inject(function($modal) {
    createController();
    $scope.profile = {sync_errors : 'error1'};

    $scope.onShowErrors();

    expect($modal.open).toHaveBeenCalled();

  }));

  it("loadProfileSuccess", function() {
    createController();
    $scope.profile =  {
      schema : [{name:'field1', expression:true},{name:'field2', is_id:true}],
      discovered_schema: [{name:'field1'},{name:'field2'}]
    };
    $scope.$emit('LOAD_PROFILE_SUCESS');

    expect($scope.isFetching).toEqual(false);
    expect($scope.originalFields).toEqual(['field1', 'field2']);
    expect($scope.profile.schema[0]['is_expression']).toBeDefined();
    expect($scope.wrapper.id_field).toEqual('field2');

  })

});



