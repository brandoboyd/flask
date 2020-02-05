(function () {
  'use strict';

  angular
    .module('slr.smart-tags-modal')
    .directive('slrSmartTagsModal', slrSmartTagsModal);

  /** @ngInject */
  function slrSmartTagsModal($modal, $http, SmartTag, SmartTags, SmartTagForm, GroupUserService) {
    return {
      restrict: 'E',
      template: "<button ng-show= 'smartTag'"
      + "ng-click='openDialog()' "
      + "class='btn btn-md btn-link' "
      + "data-original-title='Click to see tag settings' "
      + "data-placement='bottom'"
      + "ui-jq='tooltip'>Edit</button>",
      scope: {
        smartTag: '='
      },
      link: function (scope, elm, attrs, ctrl) {
        scope.openDialog = function () {
          $modal.open({
            backdrop: true,
            keyboard: true,
            backdropClick: true,
            templateUrl: '/partials/tags/tagModal',
            resolve: {
              tag: function () {
                return angular.copy(scope.smartTag)
              }
            },
            controller: function ($scope, tag) {
              $scope.tagItem = tag;
              $scope.tagItemDefaults = SmartTagForm.getSmartTagDefaults();
              $scope.usersEmails = [];
              $scope.alertCandidateEmails = [];
              $scope.changingSTIntentionLabels = [];
              $scope.chosenSTIntenions = [];
              $scope.selected_users_emails = {
                users: $scope.tagItem.alert.emails
              };
              $scope.allUsersLoaded = false;
              $scope.groupCounter = 0;


              $http.get('/alert_user_candidates', {}).success(function (data) {
                $scope.alertCandidateEmails = data.list;
              });

              //Get all the available users for
              var goodGroups = _.filter($scope.tagItem.groups, function (group) {
                return group.indexOf(":") == -1
              });
              var tempUsers = [];
              for (var i = 0; i < goodGroups.length; i++) {
                var group_id = goodGroups[i];
                //Query the users for each group in the group list
                GroupUserService.fetchUsers({id: group_id}, function (res) {
                  $scope.groupCounter++;
                  if ($scope.groupCounter == goodGroups.length) {
                    $scope.allUsersLoaded = true;
                  }
                  _.each(res.users, function (user) {
                    tempUsers.push(user);
                  })
                });
              }

              $scope.$watch('allUsersLoaded', function (nVal, oVal) {
                if (nVal == true) {
                  $scope.usersEmails = _.map(_.groupBy(tempUsers, function (doc) {
                    return doc.id;
                  }), function (grouped) {
                    return grouped[0];
                  });
                }
              });

              $scope.smart_tag_restored = true;
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

              /** INTENTIONS */
              $scope.chosenSTIntenions = SmartTags.getIntentionsByLabel($scope.tagItem.intentions, $scope.selectOptions.intentions);
              $scope.changingSTIntentionLabels = _.pluck($scope.chosenSTIntenions, 'label');
              $scope.addSTIntenion = function (intention) {
                $scope.changingSTIntentionLabels.push(intention.label);
              };
              $scope.removeSTIntenion = function (intention) {
                $scope.changingSTIntentionLabels.splice($scope.changingSTIntentionLabels.indexOf(intention.label), 1);
              };
              /** END */

              $scope.formState = {
                isSaved: false,
                isError: false
              };
              $scope.mode = "edit";
              $scope.is_modal = true;


              $scope.isAdvancedState = false;
              //Advanced options
              $scope.evaluate = function () {
                return $scope.isAdvancedState;
              }
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
              };
              $scope.save = function () {
                $scope.formState.isSaved = false;

                $scope.tagItem.intentions = _.uniq($scope.changingSTIntentionLabels);

                var selectedUsers = [];
                _.each($scope.selected_users_emails.users, function (email) {
                  selectedUsers.push(
                    _.find($scope.usersEmails, function (u) {
                      return u.email == email
                    })
                  )
                });
                //$scope.tagItem.alert.users  = _.pluck(selectedUsers, 'id');
                //$scope.tagItem.alert.emails = $scope.selected_users_emails.users;
                SmartTag.update($scope.tagItem, function (res) {
                  $scope.$parent.$broadcast(SmartTag.ON_SMARTTAG_UPDATE);
                  $scope.formState.isSaved = true;
                });
              };
              $scope.usersRequired = function () {
                if (typeof $scope.tagItem != 'undefined' && typeof $scope.tagItem.alert.is_active != 'undefined' && $scope.selected_users_emails.users != 'undefined') {
                  if ($scope.tagItem.alert.is_active == true && $scope.selected_users_emails.users.length > 0)
                    return false;
                  else
                    return true;
                }
                else
                  return false;
              };
              $scope.formValid = function () {
                if (typeof $scope.tagItem != 'undefined' && typeof $scope.tagItem.title != 'undefined' && typeof $scope.tagItem.description != 'undefined') {
                  if ($scope.tagItem.title.length > 0 && $scope.tagItem.description.length > 0) {
                    if ($scope.tagItem.alert.is_active) {
                      if ($scope.selected_users_emails.users.length > 0)
                        return false;
                      else
                        return true;
                    }
                    else
                      return false;
                  }
                  else
                    return true;
                }
                else
                  return true;
              };
              $scope.close = function (result) {
                $scope.$close(result);
              };

            }
          });
        }
      }
    };
  }
})();