(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('UsersListCtrl', UsersListCtrl);

  /** @ngInject */
  function UsersListCtrl($scope, $location, $http, $resource, $routeParams, $timeout, $window,
                         AccountsService, ACLService, ConfigureAccount, DialogService, SystemAlert, UserRolesRest) {

    var _UserRoles = new UserRolesRest();

    $scope.pagination = {
      offset: 0,
      limit: 20,
      currentPage: 1,
      totalItems: 0,
      pages: 0,
      maxSize: 10,
      setPage: setPage
    };

    $scope.filters = {
      searchQuery: ''
    };

    var debouncedFetchUsers = _.debounce(function () {
      $scope.fetchUsers();
    }, 500);

    $scope.$watch('filters.searchQuery', function (n, o) {
      if (!n && !o) {
        return;
      }
      debouncedFetchUsers();
    });

    function setPage() {
      $scope.pagination.offset = parseInt($scope.pagination.limit) * ($scope.pagination.currentPage - 1);
      $scope.fetchUsers();
    }

    $scope.users = [];
    $scope.selectedAccount = '';
    $scope.accountsList = []; // All accounts available to this user.
    $scope.editableAccountsList = []; // The accounts that this user has edit rights to.

    $scope.editPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}, {id: 'd', name: 'Delete'}];
    $scope.permsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}];
    $scope.newUserPermission = 'r';

    $scope.accountId = $routeParams.acct_id;
    $scope.NOAccount = null;

    $scope.fetchUsers = function() {
        _UserRoles.list().then(function(data) {
            $scope.fullRoles = data.data.list;
        });

        $scope.users = [];
//        angular.forEach($scope.accountsList, function(acc) {
//            if ($scope.NOAccount == null || acc.id != $scope.NOAccount.id) {
//                $scope.fetchUsersForAccount(acc);
//            }
//        });
        console.log('fetch users for account', $scope.currentAccount.name);
        $scope.usersResolved = false;
        $scope.fetchUsersForAccount($scope.currentAccount).$promise.then(function () {
            $scope.usersResolved = true;
        });
//        if ($scope.NOAccount !== null) {
//        	$scope.fetchOrphanedUsers();
//        }
    };
    //$scope.fetchUsers = function () {
    //  $scope.users = [];
    //  $scope.usersResolved = false;
    //  $scope.fetchUsersForAccount($scope.currentAccount).$promise.then(function () {
    //    $scope.usersResolved = true;
    //  });
    //};

    $scope.fetchAccounts = function () {
      return AccountsService.query({}, applyAccounts).$promise;
    };
    function applyAccounts() {
      $scope.accounts = AccountsService.getList();
      $scope.currentAccount = AccountsService.getCurrent();
      if ($scope.currentAccount && $scope.accountId !== $scope.currentAccount.id) {
        AccountsService.switchAccountId($scope.accountId);
      }
    }

    $scope.switchCurrentAccount = function () {
      AccountsService.switchAccount($scope.currentAccount, function () {
        //$scope.currentAccount = $scope.selectedAccount;
        //reload configure page since the current account was changed
        $window.location.href = '/configure#/users/' + $scope.currentAccount.id;
//            $scope.fetchUsers();
      });
    };

    $scope.fetchUsersForAccount = function (account) {
      var params = {
        offset: $scope.pagination.offset,
        limit: $scope.pagination.limit,
        account: account.id
      };

      if ($scope.filters.searchQuery) {
        params.searchQuery = $scope.filters.searchQuery;
      }

      return ConfigureAccount.getUsers(params, function (result) {
        $scope.pagination.totalItems = result.total_items;
        $scope.pagination.pages = result.pages;

        $scope.errorMessages = [];
        angular.forEach(result.users, function (u) {
          //console.log("User " + u.name);
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
      $scope.fetchAccounts().then(function (res) {
        $scope.accountsList = angular.copy(res.data);
        $scope.editableAccountsList = _.filter($scope.accountsList, function (item) {
          return item.is_admin;
        });
      }).finally(function () {
        $scope.selectedAccount = _.find($scope.accountsList, function (item) {
          return item.id == $scope.accountId;
        });
        $scope.fetchUsers();

//            AccountsService.noAccount({}, function(res) {
//                $scope.accountsList.push(res.account);
//                $scope.editableAccountsList.push(res.account);
//                $scope.NOAccount = res.account;
//            }).$promise.finally(function(){
//	            $scope.selectedAccount = _.find($scope.accountsList, function(item){return item.id == $scope.accountId;});
//	        	$scope.fetchUsers();
//	        });
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

    /* deprecated
    $scope.filterAccount = function (user) {
      return (user.currentAccount != undefined && $scope.selectedAccount.id == user.currentAccount.id);
    };
    */

    /*$scope.removeUser = function(user) {
     //alert("Should be removing user " + user);
     var postData = {id: user.id,
     account_id: user.currentAccount.id};
     $http({
     method : 'POST',
     url    : '/users/remove/json',
     data: { user_id : user.id,
     account_id: user.currentAccount.id }

     }).success(function(res) {
     $scope.fetchUsers();
     })
     }*/

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

    $scope.close = function (result) {
      $scope.$close(result);
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
        SystemAlert.error("You only have view permissions in account " + account.name + "!");
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
          }, function () {
            user.origPerm = $scope.newUserPermission;
            user.perm = $scope.newUserPermission;
            user.currentAccount = account;
          });
        } else {
          // We just switched a user to NO_ACCOUNT land. Remove his current account.
          ConfigureAccount.removeUser({email: user.email},
            function () {
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

    $scope.edit = function (email) {
      $location.path('/users/edit/' + $scope.accountId + '/' + email);
    };

    $scope.loadAccountsList();

  }
})();
