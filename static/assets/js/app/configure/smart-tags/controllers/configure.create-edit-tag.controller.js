(function() {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateEditTagCtrl', CreateEditTagCtrl);

  /** @ngInject */
  function CreateEditTagCtrl($scope, $location, $routeParams, $http, $q,
                                             SmartTag, SmartTags, SmartTagForm, GroupsRest, SharedState) {
    var Groups = new GroupsRest();
    $scope._is_modal = false;
    $scope.groupUsers = [];
    $scope.allGroupsUsers = [];
    $scope.usersEmails = [];
    $scope.alertCandidateEmails = [];
    $scope.selected_users = [];

    $http.get('/alert_user_candidates', {}).
      success(function (data) {
        $scope.alertCandidateEmails = data.list;
      });

    //A flag to know when we've just restored an existing smart tag and we don't need to query for group users, since we already have them
    //This should be needed only on the first time the tag is restored, it is meant to avoid the tagItem.groups watcher to empty the users form field
    $scope.smart_tag_restored = false;

    $scope.selectOptions = {
      intentions: SmartTagForm.getIntentions(),
      postCreationStatuses: SmartTagForm.getPostStatuses()
    };

    SmartTagForm.getChannels().then(function (data) {
      $scope.selectOptions.channels = data;
    });
    SmartTagForm.getContactLabels().then(function (data) {
      $scope.selectOptions.labels = data;
    });

    $scope.tagItem_id = $routeParams.tag_id;

    //Add a watcher for the fullGroups, need to search for the groups users every time there is a change
    $scope.chosenSTGroups = [];
    $scope.$watch('chosenSTGroups', function (nVal, oVal) {
      if (!_.isEqual(nVal, oVal)) {
        //Removed all groups?
        if (nVal.length == 0) {
          //Delete all users too
          $scope.tagItem.users = [];
          $scope.groupUsers = [];
          $scope.allGroupsUsers = [];
          $scope.usersEmails = [];
          $scope.selected_users = [];
        }
        else {
          $scope.groupUsers = [];
          if (!$scope.smart_tag_restored) {
            $scope.usersEmails = [];
          }
          for (var i = 0; i < $scope.chosenSTGroups.length; i++) {
            var group_id;
            if ($scope.mode == 'create') {
              group_id = $scope.chosenSTGroups[i];
            }
            else {
              if (typeof $scope.chosenSTGroups[i].id === "undefined") {
                group_id = $scope.chosenSTGroups[i];
              }
              else {
                group_id = $scope.chosenSTGroups[i].id;
              }
            }
            //Query the users for each group in the group list
            Groups.action('get_users', {id: group_id}).success(function (res) {
              //Check if the user does not exist already in users array
              for (var j = 0; j < res.users.length; j++) {
                var userEmail = res.users[j].email;
                var userID = res.users[j].id;
                var user = res.users[j];
                var userFound = false;
                if ($scope.allGroupsUsers.length == 0)
                  $scope.allGroupsUsers.push(user);
                //Check if the user has been inserted in the whole group users array, to avoid duplicates
                for (var i = 0; i < $scope.allGroupsUsers.length; i++) {
                  if ($scope.allGroupsUsers[i].id == userID) {
                    userFound = true;
                    break;
                  }
                }
                if (!userFound) {
                  $scope.allGroupsUsers.push(user);
                }
                //Check if the current user email is in the drop down list userEmeials
                var foundElement = _.find($scope.usersEmails, function (val) {
                  return _.isEqual(userEmail, val);
                });
                //If undefined, could not find a matching element
                if (typeof foundElement === "undefined") {
                  $scope.groupUsers.push(user);
                  if (!$scope.smart_tag_restored) {
                    $scope.usersEmails.push(userEmail);
                  }
                }
              }
            });
          }
        }
      }
      else {
        //Check if we are restoring an existing smart tag
        if ($scope.smart_tag_restored) {
          $scope.smart_tag_restored = false;
          //Check what users are in the selected groups list and the drop down list
          for (var i = 0; i < $scope.groupUsers.length; i++) {
            var userEmail = $scope.groupUsers[i].email;
            var foundElement = _.find($scope.usersEmails, function (val) {
              return _.isEqual(userEmail, val);
            });
            //If undefined, could not find a matching element
            if (typeof foundElement === "undefined") {
              $scope.usersEmails.push(userEmail);
            }
          }
          //Need to update the selected user too here
        }
      }
    });

    function getFullGroups() {
      var deferred = $q.defer();

      Groups.list().success(function (res) {
        $scope.fullGroups = _.map(res.data, function (item) {
          item.is_selected = false;
          return item;
        });
        deferred.resolve($scope.fullGroups);
      });

      return deferred.promise;
    }

    $scope.directions = [{ type: "inbound" }, { type: "outbound" }, { type: "any" }];

    //Add a watcher for the users, need to remove the user ID whenever a user is added/removed
    $scope.$watch('tagItem_id', function (nVal, oVal) {
      if (nVal) {
        $scope.mode = 'edit';
        SmartTags.getById($scope.tagItem_id).then(function (res) {
          //Don't need the groups with number:permissions
          var aux = res;
          var auxGroups = [];
          for (var i = 0; i < aux.groups.length; i++) {
            var currentGroupID = aux.groups[i];
            //If found
            if (currentGroupID.indexOf(":") == -1) {
              auxGroups.push(currentGroupID);
            }
          }
          aux.groups = auxGroups;
          $scope.tagItem = aux;

          /** INTENTIONS */
          var intentions = [];
          _.each($scope.tagItem.intentions, function (intentionLabel) {
            intentions.push(_.findWhere($scope.selectOptions.intentions, {label: intentionLabel}));
          });
          $scope.chosenSTIntenions = _.uniq(intentions);
          $scope.changingSTIntentionLabels = _.pluck($scope.chosenSTIntenions, 'label');

          /** GROUPS */
          getFullGroups().then(function (fullGroups) {
            var groups = [];
            _.each($scope.tagItem.groups, function (groupId) {
              groups.push(_.findWhere(fullGroups, {id: groupId}));
            });
            $scope.chosenSTGroups = _.uniq(groups);
            $scope.changingSTGroupsIds = _.pluck($scope.chosenSTGroups, 'id');
          });

          //Need to restore the userIDs for the restored emails too
          $scope.selected_users_IDs = $scope.tagItem.alert.users;
          $scope.usersEmails = $scope.tagItem.alert.emails;
          $scope.smart_tag_restored = true;
          $scope.tagItemDefaults = SmartTagForm.getSmartTagDefaults();
        });
      } else {
        $scope.mode = 'create';
        $scope.tagItem = new SmartTag();
        $scope.tagItem.title = '';
        $scope.tagItem.direction = 'any';
        $scope.tagItem.description = '';
        $scope.tagItem = angular.extend($scope.tagItem, SmartTagForm.getSmartTagDefaults(), {channel: SharedState.filters.channel});
        $scope.chosenSTIntenions = [];
        $scope.changingSTIntentionLabels = [];
        $scope.changingSTGroupsIds = [];
        getFullGroups().then(function (fullGroups) {
          $scope.chosenSTGroups = fullGroups;
          $scope.changingSTGroupsIds = _.pluck($scope.chosenSTGroups, 'id');
        });
      }
      $scope.title = SmartTagForm.getFormTitle($scope.mode);
    });

    $scope.addSTIntenion = function (intention) {
      $scope.changingSTIntentionLabels.push(intention.label);
    };
    $scope.removeSTIntenion = function (intention) {
      $scope.changingSTIntentionLabels.splice($scope.changingSTIntentionLabels.indexOf(intention.label), 1);
    };
    $scope.addSTGroup = function (group) {
      $scope.changingSTGroupsIds.push(group.id);
    };
    $scope.removeSTGroup = function (group) {
      $scope.changingSTGroupsIds.splice($scope.changingSTGroupsIds.indexOf(group.id), 1);
    };

    $scope.newTag = function () {
      $location.path('/tags/edit/');
    };

    $scope.formState = {
      isSaved: false,
      isError: false
    };

    $scope.save = function () {
      $scope.formState.isSaved = false;
      //Get the array of userIDs from the selected users Array
      var usersIDs = [];
      for (var i = 0; i < $scope.selected_users.length; i++) {
        usersIDs.push($scope.selected_users[i].id);
      }
      $scope.tagItem.alert.users = usersIDs;
      //Don't need the groups with number:permissions
      var groups = _.uniq($scope.changingSTGroupsIds);
      var auxGroups = [];
      for (var i = 0; i < groups.length; i++) {
        var currentGroupID = groups[i];
        //If found
        if (currentGroupID.indexOf(":") == -1) {
          auxGroups.push(currentGroupID);
        }
      }
      $scope.tagItem.groups = auxGroups;
      $scope.tagItem.intentions = _.uniq($scope.changingSTIntentionLabels);
      SmartTag.update($scope.tagItem, function (res) {
        //Need to set this to edit, since after creating a tag we move to "edit" mode
        $scope.mode = 'edit';
        $scope.formState.isSaved = true;
      });
    };


    $scope.isAdvancedState = false;

    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    };
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-chevron-down";
      }
      else {
        return "icon-chevron-right";
      }
    };

    $scope.evaluate = function () {
      return $scope.isAdvancedState;
    };
    $scope.evaluateIcon = function () {
      if ($scope.isAdvancedState) {
        return "icon-expand-down";
      }
      else {
        return "icon-expand-right";
      }
    };
    $scope.changeStatus = function () {
      $scope.isAdvancedState = !$scope.isAdvancedState;
    }
  }
})();