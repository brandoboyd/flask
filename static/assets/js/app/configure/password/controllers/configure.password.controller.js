(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('PasswordCtrl', PasswordCtrl);

  /** @ngInject */
  function PasswordCtrl($scope, $routeParams, $modal, DialogService, UserService, UserEditService, $timeout, toaster) {
    var off = [];
    var init = function () {
      $scope.errorMessages = [];
      $scope.messages = [];
      $scope.user = {};
      $scope.cached_user = {};
    };

    var destructor = function () {
      off.forEach(function (unbind) {
        unbind();
      });
      off = null;
    };

    var toResource = function (user) {
      var u = new UserEditService();
      for (var i in user) {
        u[i] = user[i];
      }
      u.password = "";
      u.passwordConfirm = "";
      return u;
    };

    if ($routeParams.hasOwnProperty('email')) {
      $scope.email = $routeParams.email;
    }

    if ($scope.email) {
      UserService.getUserByEmail($scope.email, function (res) {
        $scope.user = toResource(res.user);
        $scope.cached_user = $scope.user;
        $scope.user.password = "";
        $scope.userProfileForm.$setPristine();
      })
    }

    $scope.resetPassword = function () {
      //res is the promise object returned - code between 200 and 209 is considered a success...thus the callback function is called
      UserService.setPassword($scope.email, $scope.password, function (res) {
        $scope.messages = res.messages;
        //Close the dialog after 3 seconds
        $timeout(function () {
          DialogService.closeDialog({dialog: 'password_change', email: $scope.email});
          $scope.modalShown = false;
        });
      }, function onError(res) {
        $scope.errorMessages = res.messages;
      });
    };

    $scope.close = function () {
      DialogService.closeDialog({dialog: 'password_change', email: $scope.email});
      $scope.modalShown = false;
    };

    $scope.viewDetails = function () {
      var dialogueScope = $scope.$new();
      $modal.open({
        templateUrl: '/static/assets/js/app/configure/password/controllers/configure.password-policies.html',
        scope: dialogueScope
      });
    };

    $scope.saveProfile = function () {
      var usr = toResource($scope.user);
      $scope.user.$save(function () {
        $scope.user = usr;
        toaster.pop('success', 'Password has been changed');
      }, function () {
        $scope.user = usr;
      });
    };

    $scope.cancelEdition = function () {
      if (!$scope.userProfileForm.$pristine) {
        if ($scope.email) {
          UserService.getUserByEmail($scope.email, function (res) {
            $scope.user = toResource(res.user);
            $scope.cached_user = $scope.user;
            $scope.user.password = "";
          })
        }
        $scope.userProfileForm.$setPristine();
      }
    };

    off.push($scope.$on(DialogService.OPEN_DIALOG_EVENT, function (evt, data) {
      if (data.dialog == 'password_change') {
        //reset all fields
        $scope.errorMessages = [];
        $scope.messages = [];
        $scope.password = null;
        $scope.passwordConfirm = null;
        $scope.passwordResetForm.$setPristine();
        $scope.email = data.email;
        // modalShown is $watched by uiModal, only change of value would trigger showing of modal
        // if simply set to true here, when modal is dismissed by clicking on backdrop, modalShown's value would remain true
        // thereby not triggering any change in value
        // ++undefined === NaN ~ false
        $scope.modalShown = ++$scope.modalShown || true;
      }
    }));

    init();
    off.push($scope.$on('$destroy', destructor));
  }
})();
