(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UserEditCtrl', UserEditCtrl);

  /** @ngInject */
  function UserEditCtrl($scope, $resource, $route, DialogService, toaster) {
    var User = $resource('/user/json');

    var init = function () {
      $scope.user = null;
      $scope.flags = {
        isChanged: false
      };
    };

    $scope.close = function () {
      DialogService.closeDialog({target: 'user_edit'});
      $scope.userEditModalShown = false;
    };

    $scope.load = function (email) {
      User.get({email: email}, function (res) {
        $scope.user = res.user;
        $scope.userEditModalShown = true;
      });
    };

    $scope.save = function () {
      User.save($scope.user, function () {
          $scope.close();
          toaster.pop('success', 'User details have been changed');
          $scope.flags.isChanged = false;
        },
        function onError(res) {
          $scope.errorMessage = res.error;
        });
    };

    $scope.$on(DialogService.OPEN_DIALOG_EVENT, function (event, data) {
      //console.log(event, data);
      if (data.target == 'user_edit') {
        $scope.errorMessage = '';
        $scope.load(data.email);
      }
    });

    $scope.$watch('user', function (nVal) {
       if (nVal) {
         $scope.flags.isChanged = true;
       }
    }, true);

    if ($route.current.params.email) {
      $scope.load($route.current.params.email);
    }

    init();
  }
})();