(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UpdateAccountCtrl', UpdateAccountCtrl);

  /** @ngInject */
  function UpdateAccountCtrl($log,
                             $scope,
                             $routeParams,
                             $location,
                             $http,
                             ConfigureAccount,
                             AccountHelper,
                             SystemAlert) {

    angular.extend($scope, AccountHelper);
    $scope.account = null;
    $scope.account_id = $routeParams.account_id;
    $scope.package = "Internal";
    $scope.span_bronze = false;
    $scope.span_silver = false;
    $scope.span_gold = false;
    $scope.span_platinum = false;


    $scope.$watch('package', function () {
      if ($scope.package == "Bronze") {
        $scope.span_bronze = true;
        $scope.span_silver = false;
        $scope.span_gold = false;
        $scope.span_platinum = false;
      }
      else if ($scope.package == "Silver") {
        $scope.span_bronze = false;
        $scope.span_silver = true;
        $scope.span_gold = false;
        $scope.span_platinum = false;
      }
      else if ($scope.package == "Gold") {
        $scope.span_bronze = false;
        $scope.span_silver = false;
        $scope.span_gold = true;
        $scope.span_platinum = false;
      }
      else if ($scope.package == "Platinum") {
        $scope.span_bronze = false;
        $scope.span_silver = false;
        $scope.span_gold = false;
        $scope.span_platinum = true;
      }
      else {
        $scope.span_bronze = false;
        $scope.span_silver = false;
        $scope.span_gold = false;
        $scope.span_platinum = false;
      }
    });

    $scope.load = function () {
      return ConfigureAccount.fetch({accountId: $scope.account_id}, function (res) {
        var data = res.data;
        $scope.account_id = data.accountId;
        $scope.account_name = data.accountName;
        $scope.account_type = data.accountType;
        $scope.package = data.pricingPackage;
        $scope.oauth = data.hasoAuth;
      }, function onError(res) {
        if (!res.error) {
          SystemAlert.error("No channel found!");
        }
      });
    };
    $scope.load();

    $scope.update = function () {
      return ConfigureAccount.update(
        {
          accountId: $scope.account_id,
          accountName: $scope.account_name,
          accountType: $scope.account_type,
          pricingPackage: $scope.package
        },
        function () {
          $location.path('/accounts/');
        });
    };

    $scope.setupSalesforce = function () {
      var url = "/accounts/salesforce/" + $scope.account_id;
      var windowName = "Salesforce";
      var windowSize = "width=700,height=500,scrollbars=yes";
      $scope.salesforcePopup = window.open(url, windowName, windowSize);
      var watchClose = setInterval(function () {
        try {
          if ($scope.salesforcePopup.closed) {
            clearTimeout(watchClose);
            $scope.load();
            $scope.salesforcePopup = null;
          }
        } catch (e) {
          $log.error(e);
        }
      }, 1000);
    };

    $scope.disableSalesforce = function () {
      var url = "/accounts/salesforcerevoke/" + $scope.account_id;
      $http({
        method: 'POST',
        url: url
      }).error(function (data) {
        SystemAlert.error(data.message);
      }).finally(function () {
        $scope.load();
      });
    };
  };
})();