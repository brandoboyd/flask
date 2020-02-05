describe('Contact Label create-edit controller', function () {
  var CreateEditLabelCtrl;
  var $scope;
  var $routeParams;
  var ContactLabel;
  var TwitterHandle;
  var $httpBackend;
  var $q;

  var URLs = {
    check: '/twitter/users?twitter_handle='
  };

  beforeEach(angular.mock.module('slr.configure'));

  beforeEach(angular.mock.inject(function (_$q_, _$controller_, _$rootScope_, _$routeParams_, _ContactLabel_, _TwitterHandle_, _$httpBackend_) {
    $scope = _$rootScope_;
    $q = _$q_;
    $routeParams = _$routeParams_;
    ContactLabel = _ContactLabel_;
    TwitterHandle = _TwitterHandle_;
    $httpBackend = _$httpBackend_;

    CreateEditLabelCtrl = _$controller_('CreateEditLabelCtrl', {$scope: $scope});

    $scope.item = {
      title: 'Contact Label',
      users: ['@valid_user', 'invalid_user@gmail.com', 'valid_user']
    };
  }));

  it('should validate users in contact label creating', function (done) {
    _.each($scope.item.users, function (user) {
      if (user.charAt(0) === '@' || !/@/g.test(user)) {
        TwitterHandle.check({'twitter_handle': user}, function (res) {
          expect(res.ok).toBeTruthy();
        });
        $httpBackend.when('GET', URLs.check + user).respond({ok: true});
      } else {
        TwitterHandle.check({'twitter_handle': user}, function () {
          fail('Invalid user should not return 200 ok response');
        }, function (err) {
          expect(err.data.ok).toBeFalsy();
        });
        $httpBackend.when('GET', URLs.check + user).respond({ok: false});
      }
    });
    $httpBackend.flush();
    done();
  });

});