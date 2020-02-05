(function () {
  'use strict';

  angular.module('signup')
    .controller('selfSignUpCtrl', selfSignUpCtrl);

  function selfSignUpCtrl($scope, $http, $location, $window) {
    $scope.showErr = false;
    $scope.passwordChanging = false;

    $(function () {
        $('[data-toggle="tooltip"]').tooltip()
    })

    if (typeof User === 'undefined') {
      $scope.account = {
        first_name: '',
        last_name: '',
        email: '',
        company_name: ''
      };
    } else {
      $scope.account = _.extend(User, {password: '', password_confirm: ''});
      $scope.passwordChanging = true;
    }

    //$scope.$watch('account.identification_number', function (newVal, oldVal) {
    //  if (newVal !== oldVal) {
    //    $http.get('/gse/signup/validate_customer?identification_number=' + $scope.account.identification_number)
    //      .success(function (res) {
    //        $scope.idStatus = res.ok;
    //        $scope.idErrMsg = res.error ? res.error : null;
    //      });
    //  }
    //});

    $scope.$watch('account.email', function (newVal, oldVal) {
      if (newVal !== oldVal) {
        if ((/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$/).test(newVal)) {
          $scope.emailErr = null;
        } else {
          $scope.emailErr = 'Email is not valid';
        }
      }
    });

    $scope.$watch('account.password_confirm', function (newVal, oldVal) {
      if (newVal !== oldVal) {
        if ($scope.account.password !== '') {
          $scope.pwdNotEqual = $scope.account.password !== newVal;
        }
      }
    });

    $scope.$watch('account', function (newVal, oldVal) {
      if (newVal !== oldVal) {
        $scope.showErr = false;
        $scope.signupErr = '';
      }
    }, true);

    $scope.submitForm = function () {
      for (var property in $scope.account) {
        if ($scope.account.hasOwnProperty(property)) {
          if ($scope.account[property] === '') {
            $scope.showErr = true;
            break;
          } else {
            $scope.showErr = false;
          }
        }
      }

      if ($scope.passwordChanging) {
        if (!$scope.showErr && $scope.account.password === $scope.account.password_confirm) {
          $http.post($location.url(), $scope.account)
            .success(function (res) {
              $window.location.href = "http://" + $window.location.host + res.redirect_url;
            });
        }
      } else {
        if (!$scope.showErr && !$scope.emailErr && $scope.account.company_name.length <= 30) {
          $http.post('/gse/signup', $scope.account)
            .success(function (res) {
              if (res.ok) {
                $scope.showVerificationMsg = res.ok;
              } else {
                $scope.signupErr = res.error;
              }
            });
        }
      }

    }
  }
})();
