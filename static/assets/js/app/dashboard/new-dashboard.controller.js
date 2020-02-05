(function() {
  'use strict';
  angular.module('dashboard')
    .controller('NewDashboardCtrl', function($scope, $modalInstance, $http, $timeout) {

      var init = function() {
        $scope.dashboardTitle = '';
        $scope.flags = {
          isGallery: false,
          isShared: false,
          isFetched: false
        };
      };

      /** From shared dashboards */
      $scope.fromShared = function() {
        $scope.flags.isShared = true;
        $scope.sharedFilters = {
          title: ''
        };
        $http.get('/dashboards/shared_to_me')
          .success(function(res) {
            $scope.flags.isFetched = true;
            $scope.sharedDashboards = _.map(res.data, function(d) {
              return _.extend(d, {selected: false});
            });
          });
      };

      $scope.selectShared = function(shared) {
          $scope.chosenShared = shared;
      };

      $scope.buildFromShared = function(title) {
        var parent_dashboard_id = $scope.chosenShared.id;
        $http.post('/dashboards/' + parent_dashboard_id + '/copy', {
          title: title
        }).success(function (res) {
          $scope.$emit("pipeDash", res.data);
          $modalInstance.close();
        });

      };

      /** From Gallery */
      $scope.fromGallery = function() {
        $scope.flags.isGallery = true;
        $scope.galleryFilters = {
          display_name: ''
        };

        $http.get('/dashboards/type')
          .success(function (res) {
            var blankType = _.filter(res.data, { type: 'blank' });

            $scope.flags.isFetched = true;
            $scope.dashboardTypes = _.map(blankType, function(d) {
              return _.extend(d, {selected: false});
            });
          });
      };

      $scope.selectType = function (selectedType) {
        _.each($scope.dashboardTypes, function (type) {
          type.selected = false;
          if (type.id === selectedType.id) {
            type.selected = true;
            $scope.selectedType = selectedType;
          }
        });
      };

      $scope.buildFromGallery = function(title) {
        build($scope.selectedType.id, title);
      };

      $scope.back = function() {
        init();
      };

      function build(typeId, title) {
        $http.post('/dashboards', {
          type_id: typeId,
          title: title,
          widgets: [],
          filters: {
            'facets': {},
            'period': {
              'alias': 'today'
            }
          }
        }).success(function (res) {
          $scope.$emit("pipeDash", res.data);
          $modalInstance.close();
        });
      }

      $scope.keyPressed = function (e) {
        if (e.which === 13) {
          $modalInstance.close();
        }
      };

      init();
    });
}());
