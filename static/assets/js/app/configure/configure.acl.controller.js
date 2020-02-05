(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('ACLCtrl', ACLCtrl);

  /** @ngInject */
  function ACLCtrl($scope, ACLService, DialogService, AccountsService, ConfigureAccount) {
    $scope.sharingTitle = function () {
      var n = " ", p = "";
      if ($scope.objectIds.length > 1) {
        n = " " + $scope.objectIds.length + " ";
        p = "s";
      }
      var title = {
        'bookmark': 'Sharing{n}Bookmark{p}',
        'channel': 'Sharing{n}Channel{p}',
        'SmartTag': 'Sharing{n}Smart Tag{p}',
        'ContactLabel': 'Sharing{n}Contact Label{p}',
        'account': 'Add Users to Account',
        'matchable': 'Sharing{n}Message{p}',
        'group': 'Sharing{n}Group{p}'
      }[$scope.shareDialogScope];
      if (title)
        return title.replace('{n}', n).replace('{p}', p);
      else
        return "";
    };

    $scope.usersAndPermsList = [];
    $scope.groupsAndPermsList = [];
    $scope.objectIds = [];

    $scope.addPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}];
    $scope.editPermsList = [{id: 'r', name: 'Can view'}, {id: 'rw', name: 'Can edit'}, {id: 'd', name: 'Delete'}];
    $scope.permission = 'r';
    $scope.newUsers = '';
    $scope.currentAccount = AccountsService.getCurrent();

    // fetch all users for account and populate newUsers with users with whom channel is not shared
    $scope.fetchUsersForAccount = function (account) {
      ConfigureAccount.getUsers({account: account.id}, function (result) {
        $scope.newUsers = [];
        $scope.errorMessages = [];
        angular.forEach(result.users, function (u) {
          // do not push if user is already in usersAndPermsList or is superuser
          if (u.perm != 's' && !_.find($scope.usersAndPermsList, function (u_shared) {
              return u_shared.email == u.email
            })) {
            $scope.newUsers.push(u.email);
          }
        });
        $scope.newUsers = $scope.newUsers.join(', ');
      });
    };

    $scope.addPeople = function () {
      if (!$scope.newUsers) return;
      var newPeopleList = $scope.newUsers.split(/[,;:\s\n\t]+/);
      newPeopleList = _.uniq(newPeopleList);
      var existEmails = _.pluck($scope.usersAndPermsList, 'email');

      _.each(newPeopleList, function (email) {
        if (email && $scope.addPermission) {  // if email is valid and permission set
          var userPerm = {
            email: email,
            perm: $scope.addPermission,
            isChanged: true,
            isNew: true
          };

          if (!_.include(existEmails, email))
            $scope.usersAndPermsList.push(userPerm);
        }
      });
    };

    var findChanged = function (lst) {
      var changed = _.filter(lst, function (item) {
        return item.isChanged
      });
      return _.map(changed, function (item) {
        var o = {
          perm: item.perm,
          is_new: item.isNew
        };
        if (item.hasOwnProperty('email')) { //user
          o.email = item.email;
        } else { //group
          o.id = item.id;
        }
        return o;
      })
    };

    $scope.shareAndSave = function () {
//        var changedUsersList = _.filter($scope.usersAndPermsList, function(u) { return u.isChanged });
//        changedUsersList = _.map(changedUsersList, function(u) {
//            return u.email + ':' + u.perm + ':' + (u.isNew ? 'add' : 'change');
//        });

      ACLService.shareAndSave({
        up: findChanged($scope.usersAndPermsList),
        gp: findChanged($scope.groupsAndPermsList),
        id: $scope.objectIds,
        ot: $scope.shareDialogScope
      }, function (result) {
        if (result)
          $scope.modalShown = false;
      });
    };

    var loaded = function (result) {
      if (!(result.users || result.groups)) {
        // no permission or other error
        $scope.modalShown = false;
        return;
      }
      $scope.usersAndPermsList = [];
      $scope.usersAndPermsList = _.map(result.users, function (item) {
        var u = item;
        u.isChanged = false;
        u.isNew = false;
        return u;
      });

      $scope.groupsAndPermsList = _.map(result.groups, function (g) {
        g.isChanged = false;
        g.isNew = false;
        return g;
      });

      $scope.fetchUsersForAccount($scope.currentAccount);
    };

    $scope.load = function () {
      ACLService.getUsersAndPerms({ot: $scope.shareDialogScope, id: $scope.objectIds}, loaded);
    };

    $scope.$on(DialogService.OPEN_DIALOG_EVENT, function (evt, data) {
      if (data.target == 'acl') {
        $scope.objectIds = data.objectIds;
        $scope.shareDialogScope = data.objectType;

        $scope.errorMessage = "";
        $scope.modalShown = true;
        $scope.load();
      }
    });

    $scope.$watch('modalShown', function (visible, old) {
      if (!visible) {
        DialogService.closeDialog({dialog: 'acl', ot: $scope.shareDialogScope, id: $scope.objectIds});
      }
    });

    //tabs
    $scope.tab = 'users';
    $scope.switchTab = function (tab) {
      $scope.tab = tab;
    };
    $scope.css_tab = function (tab) {
      if ($scope.tab == tab) return 'active';
      return '';
    };

  }

})();