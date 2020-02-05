(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateDialogCtrl', CreateUpdateDialogCtrl);

  /** @ngInject */
  function CreateUpdateDialogCtrl($window, $scope, DialogService, AccountHelper, AccountsService, PackageDetailsMixin) {
    $scope.action = 'create';
    $scope.modalShown = false;

    angular.extend($scope, AccountHelper);
    angular.extend($scope, PackageDetailsMixin);
    $scope.$watch('account.package', $scope.onPackageChange.bind($scope));

    $scope.$on(DialogService.OPEN_DIALOG_EVENT, function (evt, data) {
      if (data.target == 'account') {
        //Clear form
        $scope.accountForm.$setPristine(true);
        $scope.action = data.action;
        $scope.account = data.account || {
            account_type: "Native",
            "package": "Internal"
          };
        $scope.errorMessage = "";
        $scope.modalShown = true;
      }
    });

    $scope.save = function () {
      var Request = AccountsService['save'];

      Request($scope.account, function (res) {

        $scope.accountForm.$setPristine(true);
        //SystemAlert.success("The Account '{name}' has been created"
        //    .replace('{name}', $scope.account.name), 5000);

        $window.location.href = '/configure#/accounts/';
      });
    };

    $scope.close = function () {
      $scope.modalShown = false;
    }
  }
})();