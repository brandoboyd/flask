(function() {
  'use strict';
  angular.module('dashboard')
    .controller('NewWidgetCtrl', function($scope, $http, $q, $modalInstance, $timeout, $window, selectedDashboard, WidgetService, SystemAlert, jsonValidator, jsonSchemaCache) {

      $scope.isLoading = true;
      var url = '/gallery/' + selectedDashboard.galleryId + '/widget_models';
      var init = function() {
        $scope.dashboard = selectedDashboard;
        if ($scope.dashboard.isTypeDefault) {

        } else {
          $http.get(url)
            .success(function(res) {
              $scope.isLoading = false;
              $scope.widgetModels = res.data;
            });
        }

        $scope.widget = {
          title: '',
          description: '',
          model: {},
          dashboard_id: selectedDashboard.id,
          settings: {},
          extra_settings: {},
          style: {}
        };

        $scope.jsonEditorObject = {
          data: {},
          options: {}
        };

        //$scope.visualizations = [{
        //  name: 'bar',
        //  src: '/static/dist/images/tpl-barchart.png',
        //  descr: 'A bar graph is a chart that uses vertical bars to show comparisons among categories.',
        //  selected: false
        //}, {
        //  name: 'pie',
        //  src: '/static/dist/images/tpl-piechart.png',
        //  descr: 'A pie chart is a circular statistical graphic, which is divided into slices to illustrate numerical proportion.',
        //  selected: false
        //}, {
        //  name: 'row',
        //  src: '/static/dist/images/tpl-rowchart.png',
        //  descr: 'A bar graph is a chart that uses horizontal bars to show comparisons among categories.',
        //  selected: false
        //}, {
        //  name: 'line',
        //  src: '/static/dist/images/tpl-trends.png',
        //  descr: 'A line chart is a type of chart which displays information as a series of data points connected by straight line segments',
        //  selected: false
        //}, {
        //  name: 'flow',
        //  src: '/static/dist/images/tpl-flow.png',
        //  descr: 'A chart that indicates the process at specific Journey\'s type or stage.',
        //  selected: false
        //}, {
        //  name: 'table',
        //  src: '/static/dist/images/tpl-table.png',
        //  descr: 'A general view of listed, sorted data.',
        //  selected: false
        //}];

      };

      $scope.isLastStep = false;
      $scope.hasJSONError = false;

      $scope.selectModel = function(model) {
        $scope.jsonEditorObject = {
          data: {},
        };

        $scope.widget.model = model;
        // Set schema for json-editor
        $scope.jsonEditorObject.options = {
          mode: 'tree',
          schema: model.settings,
        };
        jsonSchemaCache.put('schema.json', model.settings);
        // Set default values for json-editor
        _.each(model.settings.properties, function (item, key) {
          $scope.jsonEditorObject.data[key] = item.default || null;
        });

        $scope.isLastStep = true;
      };

      $scope.create = function() {
        $scope.hasJSONError = false;

        jsonValidator.validateJson($scope.jsonEditorObject.data, 'schema.json')
          .then(function(object) {

            $scope.hasJSONError = false;
            $scope.widget.style = angular.extend($scope.widget.style, _.pick(object, ['sizeX', 'sizeY']));
            $scope.widget.settings = _.omit(object, ['sizeX', 'sizeY']);
            WidgetService.create($scope.widget).then(function(resp) {
              $scope.$emit('WIDGET_ADDED', $scope.dashboard.id);
              SystemAlert.success('Widget has been created.');
              $scope.$close();
            });

          })
          .catch(function(err) {
            $scope.hasJSONError = true;
          });
      };

      $scope.selectVisualization = function(v) { };

      init();
    });
}());