(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ConfigureAccountCtrl', ConfigureAccountCtrl);

  /** @ngInject */
  function ConfigureAccountCtrl($scope, $resource, $routeParams,
                                AccountsService, ACLService,
                                ConfigureAccount,
                                DialogService,
                                SystemAlert) {
    $scope.users = [];
    $scope.selectedAccount = '';
    $scope.accountsList = []; // All accounts available to this user.
    $scope.editableAccountsList = []; // The accounts that this user has edit rights to.

    $scope.editPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}, {id: 'd', name: 'Delete'}];
    $scope.permsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}];
    $scope.newUserPermission = 'r';
    $scope.state = 'normal';
    $scope.accountId = $routeParams.acct_id;
    $scope.NOAccount = null;

    $scope.fetchUsers = function () {
      $scope.users = [];
      angular.forEach($scope.accountsList, function (acc) {
        if ($scope.NOAccount == null || acc.id != $scope.NOAccount.id) {
          $scope.fetchUsersForAccount(acc);
        }
      });
      if ($scope.NOAccount != null) {
        $scope.fetchOrphanedUsers();
      }
    };

    $scope.fetchUsersForAccount = function (account) {
      ConfigureAccount.getUsers({account: account.id}, function (result) {
        $scope.errorMessages = [];
        angular.forEach(result.users, function (u) {
          u.origPerm = u.perm;
          u.action = 'change';
          if (account.is_admin) {
            // This user will be editable, so make sure he can only be moved to account with permission
            u.currentAccount = _.find($scope.editableAccountsList, function (item) {
              return item.id == u.currentAccount.id;
            });
          } else {
            // This user will only be viewable, pick account from entire account list
            u.currentAccount = _.find($scope.accountsList, function (item) {
              return item.id == u.currentAccount.id;
            });
          }
          $scope.users.push(u);
        });
      }, function onError() {
        // no permission or other error
        $scope.accountsList = _.filter($scope.accountsList, function (acc) {
          return acc.id != account.id;
        });
      });
    };

    $scope.fetchOrphanedUsers = function () {
      $resource("/configure/users/json", {}).get({orphaned: true}, function (res) {
        angular.forEach(res.result, function (orphan) {
          orphan.origPerm = -1;
          orphan.perm = -1;
          orphan.action = 'change';
          var NO_ACCOUNT = orphan.accounts[0];
          orphan.currentAccount = _.find($scope.accountsList, function (item) {
            return item.id == NO_ACCOUNT.id;
          });
          $scope.users.push(orphan);
        });
      });
    };

    $scope.loadAccountsList = function () {
      AccountsService.get({}, function (res) {
        $scope.accountsList = res.data;
        $scope.editableAccountsList = _.filter($scope.accountsList, function (item) {
          return item.is_admin;
        });
      }).$promise.finally(function () {
        AccountsService.noAccount({}, function (res) {
          $scope.accountsList.push(res.account);
          $scope.editableAccountsList.push(res.account);
          $scope.NOAccount = res.account;
        }).$promise.finally(function () {
          $scope.selectedAccount = _.find($scope.accountsList, function (item) {
            return item.name == $scope.accountName;
          });
          $scope.fetchUsers();
        });
      });
    };

    $scope.EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$/; //Same regex that angular uses

    $scope.addUsers = function (emails) {
      if (!$scope.newUsers) return;
      if (!$scope.selectedAccount) return;
      var emails = _.uniq($scope.newUsers.split(/[,;:\s\n\t]+/));
      var existEmails = _.pluck($scope.users, 'email');
      var usersInfo = [];
      _.each(emails, function (email) {
        if ($scope.EMAIL_REGEXP.test(email)) {
          if (email && $scope.newUserPermission && !_.include(existEmails, email)) {  // if email is valid and permission set
            usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'add');
          } else if (_.include(existEmails, email)) {
            angular.forEach($scope.users, function (u) {
              if (u.email == email) {
                if (u.action == 'change') {
                  $scope.setUserAccount(u, $scope.selectedAccount);
                  usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'change');
                } else {
                  // u.currentAccount = $scope.selectedAccount;
                  usersInfo.push(email + ':' + $scope.newUserPermission + ':' + 'add');
                }
              }
            });
          }
        } else {
          SystemAlert.info("Invalid email " + email + " will be ignored.");
        }

      });
      ACLService.shareAndSave({
        up: usersInfo,
        id: [$scope.selectedAccount.id],
        ot: 'account'
      }, function (result) {
        $scope.fetchUsers();
      });
      $scope.newUsers = "";
    };

    $scope.filterAccount = function (user) {
      var ret = (user.currentAccount != undefined && $scope.selectedAccount.id == user.currentAccount.id);
      //console.log(ret);
      return ret;
    };

    $scope.saveButtonDisabled = function () {
      var changedUsersList = _.filter($scope.users, function (u) {
        return u.perm != u.origPerm
      });
      return !(changedUsersList && changedUsersList.length);
    };

    $scope.isEditDisabled = function (isCurrentSuper, currentUserEmail, targetUser) {
      if (targetUser.perm == 's' && currentUserEmail != targetUser.email) {
        // One super user should not be able to reset the password of another
        return true;
      }
      if (!isCurrentSuper && targetUser.perm == 's') {
        // A regular user should not be able to reset password of superuser
        return true;
      }
      return false;
    };

    $scope.resetPassword = function (email) {
      DialogService.openDialog({dialog: 'password_change', email: email});
    };

    /*
     * Do a sync in database, setting the currently selected user account as users current account.
     * Called on any change in the 'Account select' entry from the collections table.
     */
    $scope.setCurrentAccount = function (user) {
      $scope.setUserAccount(user, user.currentAccount);
    };

    /*
     * Change the permissions for this given user, on his current account.
     */
    $scope.changePermissions = function (user) {
      var userInfo = user.email + ':' + user.perm + ':' + user.action;
      ACLService.shareAndSave({
        up: [userInfo],
        id: [user.currentAccount.id],
        ot: 'account'
      }, function (result) {
        $scope.fetchUsers();
      });
    };

    /*
     * For a give user, set account as the current one.
     */
    $scope.setUserAccount = function (user, account) {
      if (!(account.is_admin || account.is_super)) {
        SystemAlert.info("You only have view permissions in account " + account.name + "!");
      }
      if (user.action == 'change') {
        if ($scope.NOAccount == null || account.id != $scope.NOAccount.id) {
          // Switch from one account to another. Either keep the permissions
          // or in case we brough a user from NO_ACCOUNT'land give him the
          // permissions that are currently set for new users.
          var perm = user.perm;
          if (user.perm == -1) perm = $scope.newUserPermission; // Switched from NO_ACCOUNT land
          ConfigureAccount.save({
            account_id: account.id,
            email: user.email,
            perms: perm
          }, function (res) {
            user.origPerm = $scope.newUserPermission;
            user.perm = $scope.newUserPermission;
            user.currentAccount = globals.account;
          });
        } else {
          // We just switched a user to NO_ACCOUNT land. Remove his current account.
          $resource("/configure/accounts/remove", {}).save({email: user.email},
            function (res) {
              user.perm = -1;
              user.origPerm = -1;
            });
        }
      }
    };

    $scope.editUser = function (user) {
      DialogService.openDialog({target: 'user_edit', email: user.email});
    };

    $scope.$on(DialogService.CLOSE, function (event, data) {
      if (data.target == 'user_edit') {
        $scope.fetchUsers();
      }
    });

    $scope.loadAccountsList();
  }
})();