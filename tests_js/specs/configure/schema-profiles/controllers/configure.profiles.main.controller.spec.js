describe('slr.configure.SchemaProfileCtrl', function () {
  var $scope;
  var $rootScope;
  var createController;
  var SchemaProfilesRest;
  var $q;
  var deferred;
  var $httpBackend;
  var MetadataService;

  beforeEach(angular.mock.module('slr.configure'));

  beforeEach(angular.mock.inject(function (_$q_, $controller, _$rootScope_, _$httpBackend_, _SchemaProfilesRest_, _MetadataService_) {
    $q = _$q_;
    deferred = _$q_.defer();
    $scope = _$rootScope_.$new();
    $rootScope = _$rootScope_;
    $httpBackend = _$httpBackend_;

    SchemaProfilesRest = _SchemaProfilesRest_;
    $scope.ProfileAccess = new _SchemaProfilesRest_();

    MetadataService = _MetadataService_;

    $httpBackend.whenGET(/.*_profile\/get.*/).respond(200, '');

    createController = function(entityType) {
      return $controller('SchemaProfileCtrl', {
        $scope: $scope,
        entityType : entityType,
        SchemaProfilesRest: _SchemaProfilesRest_,
        MetadataService : _MetadataService_
      });
    };

    spyOn(_SchemaProfilesRest_.prototype, 'getOne').and.returnValue(deferred.promise);
    spyOn(_MetadataService_, 'getBeautifiedStatus');
    spyOn($scope, '$on').and.callThrough();
    spyOn($scope, '$broadcast').and.callThrough();

  }));


  it('entityType==agent should init controller to agent related profile', function () {
    createController('agent');
    expect($scope.entityType).toEqual('agent');
    expect($scope.pageTitle).toEqual('Agent Profile');
  });

  it('entityType==customer should init controller to customer related profile', function () {
    createController('customer');
    expect($scope.entityType).toEqual('customer');
    expect($scope.pageTitle).toEqual('Customer Profile');
  });

  it('loadProfile success', function() {
    var schema_response = {
      data: {
        cardinalities : {'field1' : {count: 1}, 'field2' : {count: 2}},
        discovered_schema: [{name: 'field1'},{name: 'field2'}]
      }
    };
    createController('customer');
    deferred.resolve(schema_response);
    $scope.$apply();

    expect($scope.ProfileAccess.getOne).toHaveBeenCalled();
    expect(MetadataService.getBeautifiedStatus).toHaveBeenCalledWith($scope.profile);
    expect($scope.$broadcast).toHaveBeenCalledWith('LOAD_PROFILE_SUCESS');

    expect($scope.isFetching).toBeTruthy();

  });

  it('loadProfile error', function() {

    createController('customer');
    deferred.reject();
    $scope.$apply();

    expect($scope.ProfileAccess.getOne).toHaveBeenCalled();
    expect($scope.isFetching).toBeFalsy();

  });

  it('deleteProfile for customer', function() {

    createController('customer');
    spyOn($scope, 'onSelectTab');

    $scope.deleteProfile();

    $httpBackend
      .when('POST', '/customer_profile/delete')
      .respond(200, { ok: true });

    $httpBackend.flush();

    expect($scope.entityType).toEqual('customer');
    expect($scope.isFetching).toBeTruthy();
    expect($scope.currentTab).toEqual($scope.profileTabs[0]);
    expect($scope.currentTab.active).toBeTruthy();

  });

  it('deleteProfile for agent', function() {
    createController('agent');
    spyOn($scope, 'onSelectTab');

    $scope.deleteProfile();

    $httpBackend
      .when('POST', '/agent_profile/delete')
      .respond(200, { ok: true });

    $httpBackend.flush();

    expect($scope.entityType).toEqual('agent');
    expect($scope.isFetching).toBeTruthy();
    expect($scope.currentTab).toEqual($scope.profileTabs[0]);
    expect($scope.currentTab.active).toBeTruthy();

  });

  it('onStartRefresh', function() {
    ctrl = createController('agent');
    var sub_scope = $scope.$new();
    sub_scope.$emit('START_REFRESH');
    expect(ctrl.pageRefresher).toBeDefined();
    expect($scope.ProfileAccess.getOne.calls.count()).toEqual(2)
  });

  it('onStartRefresh with existing pageRefresher should do nothing', function() {
    ctrl = createController('agent');
    ctrl.pageRefresher = true;
    var sub_scope = $scope.$new();
    sub_scope.$emit('START_REFRESH');
    expect($scope.ProfileAccess.getOne.calls.count()).toEqual(1)
  });


  it('onStopRefresh', function() {
    ctrl = createController('agent');
    ctrl.pageRefresher = true;
    var sub_scope = $scope.$new();
    sub_scope.$emit('STOP_REFRESH');
    expect(ctrl.pageRefresher).not.toBeDefined();
    expect($scope.ProfileAccess.getOne.calls.count()).toEqual(1)
  });

  it('onRequestProfile', function() {
    ctrl = createController('agent');
    var sub_scope = $scope.$new();
    sub_scope.$emit('REQUEST_PROFILE');
    expect($scope.$broadcast).toHaveBeenCalledWith('LOAD_PROFILE_SUCESS');

  })


});



