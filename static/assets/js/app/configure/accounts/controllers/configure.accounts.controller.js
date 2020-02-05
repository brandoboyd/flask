(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('AccountsCtrl', AccountsCtrl);

  /** @ngInject */
  function AccountsCtrl($route, $scope, $timeout, $http, $modal, SystemAlert,
                        AccountHelper, AccountsService, AppState, DialogService, FilterService) {

    angular.extend($scope, AccountHelper);

    $scope.table = {
      sort: {
        predicate: 'name',
        reverse: false
      }
    };

    $scope.filters = {
      name: ''
    };

    var getSelectedItems = function () {
      return _.filter($scope.accounts, function (item) {
        return item['is_selected'];
      });
    };

    var findItems = function (param) {
      var update = [];
      if (param) {
        update = [param];
      } else {
        update = getSelectedItems();
      }
      return update;
    };

    $scope.dateRange = FilterService.getDateRange();

    $scope.showDeleteConfirmIf = function (account) {
      return account.channels_count == 0 && account.users_count > 0;
    };

    $scope.$on(DialogService.CLOSE_DIALOG_EVENT, function (evt, data) {
      if (data.dialog == 'account') {
        AccountsService.accountUpdate(data.account);
        applyAccounts();
      } else if (data.dialog == 'acl') {
        var acctId = data.id[0];
        if (acctId)
        // TODO: reload only account with acctId
          $scope.fetchAccounts();
      }
    });

    $scope.loadAccounts = function (dates) {
      $scope.dateRange = dates;
      $scope.fetchAccounts();
    };

    $scope.changeDate = function () {
      AppState.store('configureAccountsDateRange', $scope.dateRangeObj);
      FilterService.updateDateRange($scope.dateRangeObj);
      $scope.dateRange = FilterService.getDateRange();
      $scope.fetchAccounts();
    };

    $scope.fetchAccounts = function () {
      var postData = {
        stats: true,
        from: $scope.dateRange.from,
        to: $scope.dateRange.to
      };
      AccountsService.query(postData, applyAccounts);
    };

    $scope.createAccount = function () {
      //console.log("new account");
      var newAcct = {
        account_type: 'Native',
        "package": 'Internal'
      };
      DialogService.openDialog({action: 'create', target: 'account', account: newAcct});
    };

    $scope.deleteAccount = function (account) {
      AccountsService.delete({id: account.id}, function () {
        AccountsService.accountUpdate(account, 'delete');
        applyAccounts();
      });
    };

    $scope.switchAccount = function (account) {
      $scope.selectedAccount = account;
      // Switch the selected account to the current
      AccountsService.switchAccount(account, $route.reload);
    };

    $scope.manageUsers = function (account) {
      var update = findItems(account),
        ids = _.pluck(update, 'id');
      if (!ids.length) return;
      DialogService.openDialog({target: 'acl', objectType: 'account', objectIds: ids});
    };

    $scope.$on(AccountsService.ACCOUNTS_EVENT, applyAccounts);
    $scope.fetchAccounts();

    function applyAccounts() {
      $timeout(function () {
        $scope.selectedAccount = AccountsService.getCurrent();
        $scope.accounts = AccountsService.getList();
        _.each($scope.accounts, function (item) {
          item.is_selected = item.id === $scope.selectedAccount.id;
        });
      }, 0);
    }

    var openEmailModal = function (data) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        templateUrl: '/partials/accounts/send_email',
        controller: function ($scope) {
          $scope.data = data.data;
          $scope.close = $scope.$close;

          $scope.chosen = {
              accounts: [],
              roles: [],
              templateIdx: null,
              subject: '',
              body: ''
          };

          $scope.$watch('chosen.templateIdx', function (n) {
              if (n === null) {
                  return;
              }
              var _chosenTemplate = $scope.data.templates[n];
              $scope.chosen.subject = _chosenTemplate.subject;
              $scope.chosen.body = _chosenTemplate.body;
          });

          $scope.sendMail = function () {
              $http.post('/account/send-mail', {
                  accounts: $scope.chosen.accounts,
                  roles: $scope.chosen.roles,
                  subject: $scope.chosen.subject,
                  body: $scope.chosen.body
              })
              .success(function (data) {
                  SystemAlert.success("Email notification has been sent to {count} user."
                                       .replace('{count}', data.recipients.length),
                                       2000);
                  $timeout(function () {
                      $scope.close();
                  }, 2000);
              });
          };
        }
      });
    };

    $scope.showEmailForm = function () {
      $http.get("/account/email-data").
        success(function (data, status, headers, config) {
          openEmailModal(data);
        }).
        error(function (data, status, headers, config) {
          console.log(data);
        });
    };
  }
})();
