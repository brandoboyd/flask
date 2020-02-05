(function () {
  'use strict';

  angular
    .module('slr.widget-dialog')
    .directive('widgetDialog', widgetDialog);

  /** @ngInject */
  function widgetDialog($modal, $timeout, SystemAlert, WidgetService, DashboardService) {
    return {
      scope: {
        sourceWidget: '=widget',
        settings: '&'
      },
      link: function (scope, elm, attrs) {
        elm.on('click', function () {
          scope.openDialog();
        });

        var dashboards = {
          'types': [],
          'list': {}
        }
        DashboardService.loadSimple()
          .then(function (data) {
            dashboards = data;
          });

        scope.openDialog = function () {
          var source_widget = scope.sourceWidget,
            settings = scope.settings();

          $modal.open({
            backdrop: true,
            keyboard: true,
            backdropClick: true,
            templateUrl: '/static/assets/js/app/_components/widget-dialog/components.widget-dialog.directive.html',
            resolve: {
              'dashboards': function () {
                return dashboards;
              }
            },

            controller: function ($scope, dashboards) {
              $scope.dashboards = dashboards;
              $scope.dashboardTypeId = _.result(_.find($scope.dashboards.types, {'display_name': 'Blank dashboard type'}), 'id');
              $scope.dashboardList = $scope.dashboards.list[$scope.dashboardTypeId];

              $scope.dashboardTypeSelect = function () {
                $scope.dashboardList = $scope.dashboards.list[$scope.dashboardTypeId];
              };

              $scope.widget = {
                id: source_widget ? source_widget.id : null,
                title: source_widget ? source_widget.title : '',
                description: source_widget ? source_widget.description : '',
                style: source_widget ? source_widget.style : {width: '33%'},
                settings: settings.settings,
                extra_settings: settings.extra_settings,
                dashboard_id: null
              };
              $scope.save = function () {
                if ($scope.widget.title.length > 0) {
                  var isNew = !source_widget,
                    save = isNew ? WidgetService.create : WidgetService.update;
                  save.bind(WidgetService)($scope.widget).then(function (res) {
                    if (isNew) {
                      SystemAlert.success("Widget '" + res.data.item.title + "' has been added to dashboard", 5000);
                    }
                    $scope.$close();
                  });
                }
              };
              $scope.close = $scope.$close;

              $scope.init = function () {
                $timeout(function () {
                  angular.element('#widgetTitle').focus();
                });
              };
              $scope.init();
            }
          });
        }
      }
    }
  }
})();