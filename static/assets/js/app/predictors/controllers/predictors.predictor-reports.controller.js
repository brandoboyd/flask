(function () {
  'use strict';

  angular
    .module('predictors')
    .controller('PredictorReportsCtrl', PredictorReportsCtrl);

  /** @ngInject */
  function PredictorReportsCtrl($scope, AnalysisService, $window, $rootScope, $stateParams, Utils, AnalysisReport, PredictorsRest) {
    var Predictors = new PredictorsRest();
    var reports = AnalysisService.getReports();

    var init = function () {
      $scope.reports = [];
      $scope.ready = false;
      $scope.layout = {
        slimscroll: {
          height: '850px', // TODO
          wheelStep: 25,
          width: '215px'
        }
      };
      $scope.flags = AnalysisReport.disableFlags();
      angular.element('#analysis').hide();

      $scope.reports = _.sortBy(reports, 'created_at').reverse();

      if (!AnalysisService.isBuilt()) {
        _.each($scope.reports, function (report, index) {
          AnalysisReport.buildReport(report, function (data) {
            $scope.reports[index] = data.report;
            $scope.reports[index].tabs = data.tabs;
            $scope.reports[index].metric_buckets = data.report.metric_values;
            $scope.reports[index].parsedFilters = getParsedPredictorFilters(data.report.parsedFilters);

            if (data.metricData) {
              $scope.reports[index].metricData = data.metricData;
            }
          });
        });
      }

      var reportIndex = _.findIndex($scope.reports, {id: $stateParams.id});
      if (reportIndex > -1) {
        $scope.viewReport($scope.reports[reportIndex]);
      } else {
        $scope.viewReport($scope.reports[0]);
      }
    };

    $scope.getScrollHeight = function () {
      return $window.innerHeight - 145;
    };

    $scope.viewReport = function (report) {
      if (!report) return;
      $scope.metricData = {};
      $scope.tabs = [{
        name: 'Overall',
        active: true
      }];

      $scope.report = report;
      $scope.tabs = $scope.tabs.concat(report.tabs);
      $scope.metric_buckets = report.metric_values;
      $scope.metricData = report.metricData;
      $scope.selectFeature($scope.tabs[0]);

      _.each($scope.reports, function (r) {
        r.selected = (r.id == report.id);
      });
    };

    $scope.selectFeature = function (feature) {
      $scope.selectedFeature = feature.name;
      $scope.charts = [];

      _.each($scope.tabs, function (t) {
        t.active = false;
        if (t.name === feature.name) {
          t.active = true;
          $scope.flags = AnalysisReport.disableFlags();

          AnalysisReport.selectFeature({
            report: $scope.report, metricData: $scope.metricData, flags: $scope.flags, feature: t.name
          }, function (rep) {
            $scope.flags = rep.flags;
            $scope.charts = rep.charts;
            $scope.table = rep.table;
            $scope.feature_order = rep.feature_order;
            $scope.feature_order_label = 'Feature Score';
          });
        }
      });
      $scope.ready = true;
    };

    $scope.removeReport = function (report) {
      AnalysisReport.deleteReport(report, function (res) {
        if (res) {
          $rootScope.$broadcast('DELETE_BUILT_REPORTS', report);
          _.remove($scope.reports, {id: report.id});
          if ($scope.reports.length) {
            $scope.viewReport($scope.reports[0]);
          }
        }
      });
    };

    $scope.exportTable = function () {
      AnalysisReport.exportTable($scope.report, $scope.selectedFeature);
    };

    $scope.switchChart = function () {
      $scope.flags.showBar = !$scope.flags.showBar;
      $scope.flags.showScatter = !$scope.flags.showScatter;

      _.each($scope.charts, function (each, index) {
        $scope.charts[index].settings.visible = !each.settings.visible;
      });
    };

    $scope.switchView = function () {
      $scope.flags.showTable = !$scope.flags.showTable;
      $scope.flags.showCharts = !$scope.flags.showCharts;
    };

    $scope.paginate = function (direction, chart) {
      $scope.charts = AnalysisReport.paginate(direction, $scope.charts, chart);
    };

    function initReports() {
      if (reports.length) {
        init();
      } else {
        var debounce = _.debounce(function () {
          reports = AnalysisService.getReports();
          initReports();
        }, 10);
        debounce();
      }
    }

    function getParsedPredictorFilters(filters) {
      var _filters = _.reject(filters, function (f) {
        return ['plot_type', 'request_url', 'plot_by', 'level'].indexOf(f.key) >= 0;
      });

      var vectors = [];

      _.each(_filters, function (filter) {
        if (filter.key == "predictor_id") {
          Predictors.getOne(filter.value)
            .success(function (res) {
              var predictor = res.predictor;
              filter.value = predictor.name;

              var found = _.findWhere(_filters, {key: 'models'});
              if (!found) return;

              var model_ids = found.value;
              var model_names = [];
              _.each(model_ids, function (m_id) {
                var found_model = _.findWhere(predictor.models_data, {model_id: m_id});
                if (found_model) {
                  model_names.push(found_model.display_name);
                }
              });

              if (model_names.length) {
                _filters[_filters.indexOf(found)].value = model_names.join(', ').toString();
              }
            });
        } else if (['action_vector', 'context_vector'].indexOf(filter.key) >= 0) {
          var vector = (filter.key == 'action_vector' ? 'agent' : 'customer');
          var filtered_value = _.omit(filter.value, function (v, i) {
            return !filter.value[i].length
          });
          var values = _.values(filtered_value);

          var keys = _.map(_.keys(filtered_value), function (k) {
            return vector + '_' + k;
          });

          vectors.push(_.object(keys, values));
        }
      });

      _filters = _.filter(_filters, function (f) {
        return ['action_vector', 'context_vector'].indexOf(f.key) < 0
      });

      _.each(vectors, function (v) {
        var parsed_v = Utils.objToArray(v);
        _.each(parsed_v, function (pv) {
          pv.value = pv.value.join(', ').toString();
          _filters.push(pv);
        });
      });

      return _filters;
    }

    initReports();
  }
})();