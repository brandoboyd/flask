(function () {
  'use strict';

  angular
    .module('slr.configure')
    .controller('SchemaProfileCtrl', SchemaProfileCtrl);

  /** @ngInject */
  function SchemaProfileCtrl($scope, $interval, $http, entityType, SchemaProfilesRest, MetadataService) {

    var self = this;

    self.pageRefresher = undefined;

    angular.extend($scope, {
      entityType: entityType,
      pageTitle: (entityType === 'agent')? 'Agent Profile': 'Customer Profile',
      profileTabs: [
        { name: 'Discovered Fields',  active: false,  templateUrl: 'partials/schema-profiles/schema_discovery' },
        { name: 'Schema',             active: false,  templateUrl: 'partials/schema-profiles/schema_edit' }
      ],

      profile: null, // global scope variable
      ProfileAccess: new SchemaProfilesRest(),

      onSelectTab: onSelectTab,
      deleteProfile : deleteProfile

    });

    $scope.$on('REQUEST_PROFILE', onRequestProfile);
    $scope.$on('LOAD_PROFILE', onLoadProfile);
    $scope.$on('START_REFRESH', onStartRefresh);
    $scope.$on('STOP_REFRESH', onStopRefresh);

    activateController();

    function activateController() {
      $scope.ProfileAccess.setType(entityType);
      onLoadProfile();

      onSelectTab($scope.profileTabs[0]);
    }

    function onLoadProfile() {
      $scope.isFetching = true;
      $scope.ProfileAccess.getOne()
        .then(loadProfileSuccess)
        .catch(function(err) {
          $scope.isFetching = false;
        });
    }

    function onRequestProfile() {
      $scope.$broadcast('LOAD_PROFILE_SUCESS');
    }

    function loadProfileSuccess(res) {
      $scope.profile = res.data;
      $scope.profile.discovered_schema.forEach(function (field) {
        field.cardinality = $scope.profile.cardinalities[field.name].count;
      });

      $scope.schemaFields = _.map($scope.profile.schema, function (field) {
        return field.name;
      });

      if ($scope.profile) {
        $scope.profile.status_display = MetadataService.getBeautifiedStatus($scope.profile);
      }
      $scope.$broadcast('LOAD_PROFILE_SUCESS');
    }

    function onStartRefresh() {
      if ( angular.isDefined(self.pageRefresher) ) {
        return;
      }
      onLoadProfile();
      self.pageRefresher = $interval(onLoadProfile, 2000);
    }

    function onStopRefresh() {
      if ( angular.isDefined(self.pageRefresher) ) {
        $interval.cancel(self.pageRefresher);
        self.pageRefresher = undefined;
      }
    }

    function onSelectTab(tab) {
      if ($scope.currentTab) {
        $scope.currentTab.active = false;
      }
      $scope.currentTab = tab;
      $scope.currentTab.active = true;
    }

    function deleteProfile() {
      var profile = $scope.entityType == 'agent'  ? '/agent_profile/' : '/customer_profile/';
      $http.post(profile + "delete", {}).then(function(res) {
        onLoadProfile();
        onSelectTab($scope.profileTabs[0]);
      })
    }

  }
})();
