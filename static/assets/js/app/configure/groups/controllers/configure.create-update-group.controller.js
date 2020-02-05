(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('CreateUpdateGroupCtrl', CreateUpdateGroupCtrl);

  /** @ngInject */
  function CreateUpdateGroupCtrl($scope,
                                 $location,
                                 $routeParams,
                                 $q,
                                 ChannelsService,
                                 UserRolesRest,
                                 UserService,
                                 SmartTags,
                                 GroupsRest,
                                 JourneyTagsRest,
                                 JourneyTypesRest,
                                 JourneyFunnelsRest,
                                 PredictorsRest) {
    var JourneyFunnels = new JourneyFunnelsRest(),
        JourneyTags = new JourneyTagsRest(),
        JourneyTypes = new JourneyTypesRest(),
        Predictors = new PredictorsRest(),
        Groups = new GroupsRest(),
        UserRoles = new UserRolesRest();
    $scope.group_id = $routeParams.group_id;
    $scope.chosen = {
      groupChannel: [],
      groupSmartTag: [],
      groupJourneyTypes: [],
      groupJourneyTags: [],
      groupFunnels: [],
      groupPredictors: [],
      groupRoles: [],
      groupUsers: []
    };

    $scope.initData = function (is_edit) {
      // Do all the required data initialization which we need.
      // Load full channel list for channel access
      ChannelsService.load(['inbound', 'dispatch'], false, true);
      /** ROLES */
      UserRoles.list().success(function (res) {
        $scope.fullGroupRoles = res.list;

        if (is_edit) { // edited user
          // data contains only roles accessible by current user
          // so all roles in group.roles might not be there in data
          // so filter out undefined values
          var arr = _.filter(_.map($scope.group.roles, function (roleId) {
            return _.find($scope.fullGroupRoles, {id: roleId});
          }));
          $scope.chosen.groupRoles = _.uniq(arr);
        } else {
          $scope.chosen.groupRoles = $scope.fullGroupRoles;
          $scope.group.roles = [];
        }
      });
      /** USERS */
      UserService.listAvailableUsers(function (data) {
        $scope.fullUserList = data['list'];
        var users = [];
        for (var i = 0, len = $scope.fullUserList.length; i < len; i++) {
          var current = $scope.fullUserList[i];
          if (current.email.indexOf("+") > 0) {
            users[i] = $scope.fullUserList[i];
          }
        }
        $scope.fullUserList = _.difference($scope.fullUserList, users);

        if (is_edit) {
          var arr = _.filter(_.map($scope.group.members, function (memberId) {
            return _.find($scope.fullUserList, {id: memberId});
          }));
          $scope.chosen.groupUsers = _.uniq(arr);
        } else {
          $scope.chosen.groupUsers = [];
          $scope.group.members = [];
        }
      });
      /** FUNNELS */
      JourneyFunnels.list().success(function (res) {
        $scope.fullFunnelsList = _.uniq(res.data);

        if (is_edit) {
          groupDeferred.promise.then(function () {
            var arr = _.map($scope.group.funnels, function (funnelId) {
              return _.find($scope.fullFunnelsList, {id: funnelId});
            });
            $scope.chosen.groupFunnels = _.uniq(arr);
          });
        } else {
          $scope.chosen.groupFunnels = [];
          $scope.group.funnels = [];
        }
      });
      /** JOURNEY TAGS & TYPES */
      JourneyTags.list().success(function (jTags) {
        $scope.fullJourneyTagsList = _.uniq(jTags.data);

        JourneyTypes.list().success(function (jTypes) {
          $scope.fullJourneyTypesList = _.uniq(jTypes.data);

          _.each(jTags.data, function (jTag) {
            var jType = _.find($scope.fullJourneyTypesList, {id: jTag.journey_type_id});
            jTag.journey_tag_full_name = jType.display_name + ' : ' + jTag.display_name;
          });

          if (is_edit) {
            groupDeferred.promise.then(function () {
              var arr = _.map($scope.group.journey_types, function (id) {
                return _.find($scope.fullJourneyTypesList, {id: id});
              });
              $scope.chosen.groupJourneyTypes = _.uniq(arr);

              arr = _.map($scope.group.journey_tags, function (id) {
                return _.find($scope.fullJourneyTagsList, {id: id});
              });
              $scope.chosen.groupJourneyTags = _.uniq(arr);
              updateAvailableJourneyTags();
            });
          } else {
            $scope.chosen.groupJourneyTypes = [];
            $scope.chosen.groupJourneyTags = [];
            $scope.group.journey_types = [];
            $scope.group.journey_tags = [];
          }
        });
      });

      /** PREDICTORS */
      Predictors.list().success(function (res) {
        $scope.fullPredictorsList = _.uniq(res.list);

        if (is_edit) {
          groupDeferred.promise.then(function () {
            var arr = _.map($scope.group.predictors, function (id) {
              return _.findWhere($scope.fullPredictorsList, {id: id});
            });
            $scope.chosen.groupPredictors = _.uniq(arr);
          });
        } else {
          $scope.chosen.groupPredictors = [];
          $scope.group.predictors = [];
        }
      });
    };

    if ($scope.group_id) {
      $scope.mode = 'edit';
      Groups.getOne($scope.group_id).success(function (res) {
        groupDeferred.resolve();
        $scope.group = res.group;
        if ($scope.group.perm == 'r' && $scope.mode == 'edit') {
          $scope.title = 'View Group';
        }
        $scope.initData(true);
      });
    } else {
      $scope.mode = 'create';
      $scope.group = {};
      $scope.initData(false);
    }

    $scope.objectIds = [$scope.group_id];
    var groupDeferred = $q.defer();

    $scope.title = {
      'create': 'New',
      'edit': 'Update'
    }[$scope.mode];

    $scope.$on(ChannelsService.ON_CHANNELS_LOADED, function () {
      $scope.fullChannelList = ChannelsService.getList();
      if ($scope.mode === 'edit') {
        var arr = _.map($scope.group.channels, function (roleId) {
          return _.find($scope.fullChannelList, {id: roleId});
        });
        $scope.chosen.groupChannel = _.uniq(arr);
      } else {
        $scope.chosen.groupChannel = $scope.fullChannelList;
        $scope.group.channels = [];
      }
      $scope.loadSmartTags();
    });

    $scope.addSelectTag = function (item, array) {
      array.indexOf(item) < 0 && array.push(item);
    };

    $scope.removeSelectTag = function (item, array) {
      _.remove(array, {id: item.id});
    };

    $scope.addJourneyType = function () {
      updateAvailableJourneyTags();
    };

    $scope.removeJourneyType = function (journeyType) {
      updateAvailableJourneyTags();
      _.remove($scope.chosen.groupJourneyTags, {journey_type_id: journeyType.id});
    };

    $scope.addChannelGroup = function (channel) {
      updateAvailableSmartTags();
    };
    $scope.removeChannelGroup = function (channel) {
      updateAvailableSmartTags();
      _.remove($scope.chosen.groupSmartTag, {channel: channel.id});
    };

    $scope.selectedJourneyTypeTags = [];

    function updateAvailableJourneyTags() {
      $scope.selectedJourneyTypeTags.length = 0;
      _.each($scope.chosen.groupJourneyTypes, function (journeyType) {
        Array.prototype.push.apply($scope.selectedJourneyTypeTags, _.filter($scope.fullJourneyTagsList, {journey_type_id: journeyType.id}));
      });
    }

    $scope.selectedChannelSmartTags = [];

    function updateAvailableSmartTags() {
      $scope.selectedChannelSmartTags.length = 0;
      _.each($scope.chosen.groupChannel, function (channel) {
        Array.prototype.push.apply($scope.selectedChannelSmartTags, _.filter($scope.fullSmartTags, {channel: channel.id}));
      });
    }

    /** SMART TAGS */
    $scope.loadSmartTags = function () {
      $scope.fullSmartTags = [];
      var loadedChannelCounter = 0;

      _.each($scope.fullChannelList, function (channel) {
        var params = {channel: channel.id};
        SmartTags.listAll(params).then(function (res) {
          Array.prototype.push.apply($scope.fullSmartTags, res.list);
          loadedChannelCounter += 1;

          if (loadedChannelCounter === $scope.fullChannelList.length) {
            updateAvailableSmartTags();

            if ($scope.mode === 'edit') {
              groupDeferred.promise.then(function () {
                var arr = _.map($scope.group.smart_tags, function (smartTagId) {
                  return _.findWhere($scope.selectedChannelSmartTags, {id: smartTagId});
                });
                $scope.chosen.groupSmartTag = _.uniq(arr);
              });
            } else { // new
              $scope.chosen.groupSmartTag = [];
              $scope.group.smart_tags = [];
            }
          }
        });
      });
    };

    $scope.saveButtonDisabled = function () {
      if (!$scope.group) {
        return true;
      }
      if (!$scope.group.name) {
        return true;
      }
      if (!$scope.chosen.groupChannel.length) {
        // Test that user roles are set for this user
        return true;
      }
      return false;
    };

    $scope.save = function () {
      $scope.group.channels = _.uniq(_.pluck($scope.chosen.groupChannel, 'id'));
      $scope.group.smart_tags = _.uniq(_.pluck($scope.chosen.groupSmartTag, 'id'));
      $scope.group.members = _.uniq(_.pluck($scope.chosen.groupUsers, 'id'));
      $scope.group.roles = _.uniq(_.pluck($scope.chosen.groupRoles, 'id'));
      $scope.group.journey_types = _.uniq(_.pluck($scope.chosen.groupJourneyTypes, 'id'));
      $scope.group.journey_tags = _.uniq(_.pluck($scope.chosen.groupJourneyTags, 'id'));
      $scope.group.funnels = _.uniq(_.pluck($scope.chosen.groupFunnels, 'id'));
      $scope.group.predictors = _.uniq(_.pluck($scope.chosen.groupPredictors, 'id'));
      Groups.save($scope.group).then(function () {
        $location.path('/groups/');
      });
    };
  }
})();