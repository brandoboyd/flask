(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateUserCtrl', CreateUpdateUserCtrl);

  /** @ngInject */
  function CreateUpdateUserCtrl($scope, $location, $modal, $routeParams, UserRolesRest, GroupsService, UserEditService, $http, SystemAlert) {
    $scope.accountId = $routeParams.acct_id;
    $scope.userEmail = $routeParams.user_email;
    $scope.EMAIL_REGEXP = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$/; //Same regex that angular uses
    $scope.changingRolesIds = [];
    var changingGroupsIds = [];
    var initial_role_ids = [];
    var initial_group_ids = [];
    
    var UserRoles = new UserRolesRest();

    var toResource = function (user) {
      var u = new UserEditService();
      for (var i in user) {
        u[i] = user[i];
      }
      return u;
    };

    $scope.initData = function (is_edit) {
      // Load possible user roles and populate field with all of them as default
      UserRoles.list().success(function (data) {
        $scope.fullRoles = data.list;

        if (is_edit) { // edited user
          var arr = [];
          _.each($scope.user.roles, function (roleId) {
            var found = _.findWhere(data.list, {id: roleId});
            if (found) {
              arr.push(found);
            } else {
              initial_role_ids.push(roleId);
            }
          });
          $scope.chosenRoles = _.uniq(arr);
        } else {
          $scope.chosenRoles = data.list;
        }
        $scope.changingRolesIds = initArray($scope.chosenRoles);
      });
      GroupsService.query({}, function (res) {
        $scope.fullGroups = _.map(res.data, function (item) {
          item.is_selected = false;
          return item;
        });

        if (is_edit) { // edited group
          var arr = [];
          _.each($scope.user.groups, function (groupId) {
            var found = _.findWhere($scope.fullGroups, {id: groupId});
            if (found) {
              arr.push(found);
            } else {
              initial_group_ids.push(found);
            }
          });
          $scope.chosenGroup = _.uniq(arr);
        } else {
          $scope.chosenGroup = $scope.fullGroups;
        }
        changingGroupsIds = initArray($scope.chosenGroup);
      });
      $scope.user.email = $scope.userEmail;
    };

    function initArray(array) {
      return array.length ? _.pluck(array, 'id') : [];
    }

    $scope.addRole = function (item) {
      $scope.changingRolesIds.push(item.id);
    };
    $scope.removeRole = function (item) {
      $scope.changingRolesIds.splice($scope.changingRolesIds.indexOf(item.id), 1);
    };
    $scope.addGroup = function (item) {
      changingGroupsIds.push(item.id);
    };
    $scope.removeGroup = function (item) {
      changingGroupsIds.splice(changingGroupsIds.indexOf(item.id), 1);
    };

    if ($scope.userEmail) {
      $scope.mode = 'edit';
      UserEditService.get({email: $scope.userEmail}, function (res) {
        $scope.user = toResource(res.user);
        $scope.initData(true);
      });
    } else {
      $scope.mode = 'create';
      $scope.user = new UserEditService();
      $scope.initData(false);
    }

    $scope.title = {
      'create': 'Create',
      'edit': 'Update'
    }[$scope.mode];

    $scope.isCreationMode = function () {
      return ($scope.mode == 'create');
    };

    $scope.save = function () {
      // Backup in case of error
      if (initial_group_ids.length) {
        changingGroupsIds = changingGroupsIds.concat(initial_group_ids);
      }
      if (initial_role_ids.length) {
        $scope.changingRolesIds = $scope.changingRolesIds.concat(initial_role_ids);
      }
      $scope.user.roles = _.uniq($scope.changingRolesIds);
      $scope.user.groups = _.uniq(changingGroupsIds);
      var usr = toResource($scope.user);
      var onSuccess = function () {
        $location.path('/users/' + $scope.accountId);
        SystemAlert.success("Congratulations, user was created successfully!", 4000);
      };

      if ($scope.mode == 'create') {
        $http({
          method: 'POST',
          url: '/users/check_user_archived/json',
          data: {user: $scope.user}
        }).success(onSuccess).error(function () {
          // if not archived
          $scope.user.$save(onSuccess).finally(function () {
            $scope.user = usr;
          });
        })
      } else {
        $scope.user.$save(function () {
          $location.path('/users/' + $scope.accountId)
        }).finally(function () {
          $scope.user = usr;
        });
      }
    };


    $scope.saveButtonDisabled = function () {
      if (!$scope.user) return false;
      if (!$scope.user.first_name || !$scope.user.last_name) {
        // Firstname + Lastname should be required
        return true;
      }
      if (!$scope.user.email || !$scope.EMAIL_REGEXP.test($scope.user.email)) {
        // Test that email is present and that it's valid
        return true;
      }
      if ($scope.changingRolesIds.length === 0) {
        // Test that user roles are set for this user
        return true;
      }
      return false;
    };

    $scope.deleteButtonDisabled = function () {
      if ($scope.mode == 'edit') {
        return true;
      }
      else {
        return false;
      }
    };

    $scope.deleteUser = function () {
      var postData = {id: $scope.user.id};
      $http({
        method: 'POST',
        url: '/users/delete/json',
        data: postData
      }).success(function () {
        $location.path('/users/' + $scope.accountId)
      })
    };

    $scope.list = function () {
      $location.path('/users/' + $scope.accountId);
    };

    $scope.add = function () {
      $location.path('/users/add/' + $scope.accountId);
    };

    $scope.openDialog = function (rootScope, http) {
      var d = $modal.open({
        backdrop: true,
        keyboard: true,
        backdropClick: true,
        templateUrl: '/partials/users/confirmDialog',
        controller: function ($scope) {
          $scope.user = rootScope.user;
          $scope.accountId = rootScope.accountId;
          $scope.modal_title = 'Warning'
          //$rootScope.$broadcast(SmartTags.ON_POST_TAGS_REMOVED, response_id, post_id, tag_removed, true);
          $scope.close = function (result) {
            $http({
              method: 'POST',
              url: '/users/reactivate_user/json',
              data: {user: $scope.user}
            }).success(function () {
              $location.path('/users/' + $scope.accountId);
            }).finally(function () {
              $scope.$close(result);
            });
          };
          $scope.dismiss = function (reason) {
            rootScope.user.email = '';
            $scope.$dismiss(reason);
          }

        }
      });
    };

  }
})();