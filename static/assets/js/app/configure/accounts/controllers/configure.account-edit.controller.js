(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AccountEditCtrl', AccountEditCtrl);

  /** @ngInject */
  function AccountEditCtrl($scope, $http, $routeParams, $window, $modal, $filter, $timeout,
                           FilterService,
                           StaffUsersService,
                           AccountHelper,
                           AccountsService,
                           ChannelsRest,
                           DialogService,
                           SystemAlert,
                           PackageDetailsMixin) {
    var _ChannelsRest = new ChannelsRest();

    angular.extend($scope, AccountHelper);
    angular.extend($scope, angular.copy(PackageDetailsMixin));

    $scope.alertCandidateEmails = [];
    $http.get('/alert_user_candidates', {}).success(function (data) {
      $scope.alertCandidateEmails = data.list;
    });

    $scope.account = null;
    $scope.channels = [];
    $scope.staff_users = {};
    $scope.account_id = $routeParams.account_id;

    FilterService.setDateRangeByAlias('this_month');
    $scope.dateRange = FilterService.getDateRange();

    $scope.$watch('account.package', $scope.onPackageChange.bind($scope));

    $scope.$watch('account.account_type', function (nVal) {
      // ng-options accountTypeOptions is not observing ng-model account.account_type
      // See https://github.com/angular/angular.js/issues/8651
      // Workaround to trigger change in accountTypeOptions
      var _poped = $scope.accountTypeOptions.pop();
      $timeout(function () {
        $scope.accountTypeOptions.push(_poped);
      });
    });

    $scope.getCurrentAccount = function () {
      return AccountsService.get({account_id: $scope.account_id, stats: true}, function (res) {
        var account = res.account || (res.data && res.data[0]);
        if (account) {
          $scope.setCurrentAccount(account);
          return account;
        }
      })
    };

    $scope.executeAccountStatus = function () {
      $scope.account.is_locked ? lock() : unlock();
    };

    $scope.channelsTable = {
      sort: {
        predicate: 'title',
        reverse: false
      }
    };


    function lock() {
      $http.post("/account/lock", {id: $scope.account_id})
        .success(function (data, status, headers, config) {
          $scope.getCurrentAccount();
        })
        .error(function (data, status, headers, config) {
          console.log(data);
        });
    }

    function unlock() {
      $http.post("/account/unlock", {id: $scope.account_id})
        .success(function (data, status, headers, config) {
          $scope.getCurrentAccount();
        })
        .error(function (data, status, headers, config) {
          console.log(data);
        });
    }

    var openAuditModal = function (data, accountId) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/audit/auditModal',
        controller: function ($scope) {
          $scope.audit = {loading: false};
          $scope.data = data.data;
          $scope.cursor = data.cursor;
          $scope.close = $scope.$close;
          $scope.loadMoreAccountEvents = function () {
            if ($scope.audit.loading) return;
            $scope.audit.loading = true;
            return $http.post("/account/events", {id: accountId, cursor: $scope.cursor}).success(function (data) {
              $scope.data.push.apply($scope.data, data.data);
              $scope.cursor = data.cursor;
              $scope.audit.loading = false;
            });
          }
        }
      });
      //return d.result;
    };

    $scope.showAuditTrail = function () {
      $http.post("/account/events", {id: $scope.account_id}).success(function (data, status, headers, config) {
        openAuditModal(data, $scope.account_id);
      }).error(function (data, status, headers, config) {
        console.log(data);
      });
    };


    $scope.setCurrentAccount = function (account) {

      if ((account != null) && (account != $scope.account)) {
        account.end_date = account.end_date ? new Date(account.end_date).format('mm/dd/yyyy') : '';  // merger: prefer this
        $scope.account = account;
        $scope.fetchChannels();
        $scope.fetchStaffUsers();
        AccountsService.accountUpdate(account);
      }
    };

    $scope.getCurrentAccount();

    $scope.fetchChannels = function () {
      //console.log("Fetching channels");
      var postData = {
        widget: false,
        stats: true,
        from: $scope.dateRange.from,
        to: $scope.dateRange.to,
        account: $scope.account_id
      };
      _ChannelsRest.fetchChannels(postData).success(function (res) {
        $scope.channels = res.list;
      });
    };

    $scope.fetchStaffUsers = function () {
      return StaffUsersService.query(function (res) {
        $scope.staff_users = res.users;
      });
    };

    $scope.update = function (reload) {
      return AccountsService.update($scope.account).$promise.then(function () {
        //SystemAlert.success("The Account '{name}' has been updated".replace('{name}', $scope.account.name), 5000);
        $window.location.href = '/configure#/accounts/';
        if (reload) {
          $window.location.reload(true);
        }
      });
    };

    $scope.isChannelsEmpty = function () {
      return angular.equals([], $scope.channels);
    };

    $scope.createAccount = function () {
      $window.location.href = '/configure#/new_account';
    };

    $scope.createChannel = function () {
      $window.location.href = '/configure#/new_channel';
    };

    $scope.$on(DialogService.CLOSE_DIALOG_EVENT, function (evt, data) {
      if (data.dialog == 'account') {
        AccountsService.accountUpdate(data.account);
        if (data.fromPage != '/configure#/accounts/') {
          setTimeout(function () {
            // let the popup close
            $window.location.href = "/configure#/accounts/";
          }, 0);
        }
      }
    });
  }
})();
