(function () {
  'use strict';

  angular
    .module('slr.analysis')
    .directive('analysisPanel', analysisPanel);

  /** @ngInject */
  function analysisPanel(AnalysisRest, AnalysisReport, $state, $rootScope, SystemAlert, MetadataService, Utils, $timeout, AnalysisService, toaster) {
    return {
      restrict: 'EA',
      scope: {
        analysisFilters: '=',
        analysisExtraParams: '='
      },
      templateUrl: '/static/assets/js/app/_components/analysis/directives/components.analysis-panel.html',
      link: function (scope) {
        var Apps = MetadataService.getApps();
        var Analysis = new AnalysisRest();

        var extraParams;
        var filters;
        var reportId;

        var conversionLabels = [
          // ordering is important to match the colors/legend-ordering
          // between funnel view and generated report
          {name: 'converted', checked: true},
          {name: 'abandoned', checked: true},
          {name: 'stuck', checked: true}
        ];

        var ja_standard_metrics = [
          {
            name: 'Conversion',
            selected: false,
            metric: 'conversion',
            metric_values: conversionLabels,
            metric_type: 'Label'
          },
          {
            name: 'Stage Paths',
            selected: false,
            metric: 'stage-paths',
            metric_values: null,
            metric_type: 'Label'
          },
          {
            name: 'Paths',
            selected: false,
            metric: 'paths-comparison',
            metric_values: null,
            metric_type: 'Boolean'
          }
        ];

        var initParams = function (analysisFilters) {
          try {
            scope.flags = resetFlags();
            extraParams = scope.analysisExtraParams;
            filters = analysisFilters || scope.analysisFilters;
            init();
          } catch (e) {
            console.error(e);
            scope.analyzing = false;
          }
        };

        var init = function () {
          scope.funnelData = {};
          scope.selectedNodes = null;

          scope.analyzing = false;
          scope.results = {};
          scope.labels = [];
          scope.sliderValue = [];
          scope.resultMetric ='';

          resetAnalysisParams();

          scope.builtReports = AnalysisService.getReports();

          scope.showLimit = 3;

          scope.exclude(scope.selectedMetric);
        };

        function resetAnalysisParams() {
          scope.metrics = extraParams.metrics;

          if (extraParams.application === Apps.JA) {
            scope.metrics = scope.metrics.concat(ja_standard_metrics);
          }
          scope.selectedMetric = scope.metrics[0];
          scope.reportName = scope.selectedMetric.metric + '_Report';

          if (scope.selectedMetric.metric_type === 'Numeric') {
            scope.selectedMetric.step = getStep();
          }
          scope.updateBuckets(scope.selectedMetric.metric_values_range);
        }

        function getStep() {
          return Math.floor(scope.selectedMetric.metric_values_range[1] / 20) <= 1 ? 1 : 10;
        }

        function pushToReports(res) {
          scope.analyzing = false;
          var report = _.extend(res.item, {
            name: res.item.title,
            type: 'report',
            sref: extraParams.sref + '(' + JSON.stringify({id: res.item.id}) + ')'
          });

          AnalysisReport.buildReport(report, function (rep) {
            report = rep.report;
            report.tabs = rep.tabs;
            report.metric_buckets = rep.report.metric_values;

            if (rep.metricData) {
              report.metricData = rep.metricData;
            }

            AnalysisService.unshiftReport(report);  // to show reports in Analysis Reports
          });
        }

        function analyze(params) {
          new AnalysisRest().run(params)
            .success(function (res) {
              reportId = res.item.id;
              if (_.isEmpty(res.item.results)) {
                getReport(res.item.id);
              } else {
                pushToReports(res);
              }
            }).error(function (err) {
            scope.analyzing = false;
          })
        }

        function getReport(id) {
          if (!scope.analyzing) return;
          Analysis.getOne(id)
            .success(function (res) {
              if (_.isEmpty(res.item.results)) {
                if (res.item.status[0] === 'error') {
                  SystemAlert.error(res.item.status_message);
                  Analysis.remove(res.item.id).then(loadReports);
                  scope.analyzing = false;
                  return;
                }
                if (scope.analyzing) {
                  var debounce = _.debounce(function () {
                    getReport(id);
                  }, 2000); // each 2 secs
                  debounce();
                }
              } else {
                pushToReports(res);
              }
            });
        }

        function resetFlags() {
          return {
            showLabels: false,
            showSlider: false
          }
        }

        function showMessage(res) {
          var msg = res.message || (res.data && res.data.message) || (res.item && res.item.message);
          SystemAlert.success(msg);
          return res;
        }

        scope.stop = function () {
          Analysis.stop(reportId)
            .success(function (res) {
              scope.analyzing = false;
              Analysis.remove(reportId).then(showMessage).then(loadReports);
            })
        };

        scope.analyze = function () {
          scope.analyzing = true;

          if (angular.isDefined(scope.selectedMetric)) {
            scope.selectedMetric.metric_values = getMetricValues();

            if (!scope.selectedMetric.metric_values || !scope.selectedMetric.metric_values.length) {
              return;
            }

            var params = {
              filters: filters,
              analyzed_metric: scope.selectedMetric.metric,
              metric_type: scope.selectedMetric.metric_type,
              metric_values: scope.selectedMetric.metric_values,
              metric_values_range: scope.selectedMetric.metric_values_range,
              title: scope.reportName,
              application: extraParams.application,
              analysis_type: getAnalysisType()
            };

            var from = filters.from,
              to = filters.to;

            if (extraParams.application == Apps.JA) {
              from = moment(filters.from).format('YYYY-MM-DD HH:mm:ss');
              to = moment(filters.to).format('YYYY-MM-DD HH:mm:ss')
            } else {
              from = moment(filters.from).format('L');
              to = moment(filters.to).format('L')
            }

            _.extend(params.filters, {
              from: from,
              to: to,
              timerange: [moment(from).unix(), moment(to).unix()]
            });

            if (scope.selectedMetric.metric === 'stage-paths') {
              _.extend(params.filters, {
                labeling_strategy: extraParams.labelStrategy
              })
            }

            if (scope.selectedMetric.metric === 'conversion' && scope.funnelData) {
              params.filters['funnel_id'] = scope.funnelData.funnel_id;
              params.filters['stage_id'] = scope.funnelData.stage_id;
            }

            // params.filters['level'] = FilterService.getSelectedLevel();
            analyze(params);
          }
        };

        scope.openReportPage = function (reportId) {
          $state.go(extraParams.sref, {id: reportId});
        };

        scope.$on('DELETE_BUILT_REPORTS', function (e, report) {
          if (report) {
            _.remove(scope.builtReports, {id: report.id});
          }
        });

        scope.$on('FACETS_CHANGED', function () {
          initParams();
        });

        scope.$on("OnNodesSelected", function (data, obj) {
          scope.selectedNodes = obj;
          scope.selectedMetric = _.find(scope.metrics, {metric: 'stage-paths'});
          scope.exclude(scope.selectedMetric);
        });

        $rootScope.$on('OnPathsSelected', function (e, paths) {
          angular.element('#analysis').show('fast');
          scope.selectedPaths = _.map(paths, function (p) {
            var node_events = [];
            var metric_value;

            _.each(p.stages, function(s) {
              node_events.push(_.pluck(s.nodes, 'name'));
            });

            if (p.group_by === 'most_common_path') {
              metric_value = p.metrics.percentage.value;
            } else {
              metric_value = p.metrics[p.group_by].value;
            }

            var metrics = [];
            _.each(_.keys(p.metrics), function (k) {
              var v = p.metrics[k].value;
              if (v !== 0) {
                metrics.push(_.object([k], [v]));
              }
            });

            return {
              metrics: _.flatten(metrics),
              path: p.group_by,
              metric_value: parseFloat(metric_value),
              measure: p.measure || 'max'
            };
          });
          scope.selectedMetric = _.find(scope.metrics, {metric: 'paths-comparison'});
          scope.exclude(scope.selectedMetric);
        });

        scope.$on('ANALYSIS_FUNNEL_SELECTED', function (obj, data) {
          scope.selectedMetric = _.find(scope.metrics, {metric: 'conversion'});
          scope.funnelData = data.funnelData;
          scope.exclude(scope.selectedMetric);
        });

        scope.exclude = function (selected) {
          scope.flags = resetFlags();
          scope.resultMetric = null;

          $timeout(function () {
            scope.selectedMetric = selected;
            if (selected.metric_type === 'Numeric') {
              scope.flags.showSlider = true;
              scope.selectedMetric.step = getStep();
              scope.updateBuckets(scope.selectedMetric.metric_values_range);
            } else if (selected.metric_type === 'Label') {
              if (selected.metric === 'stage-paths') {
                scope.flags.showPathsSelection = true;
                scope.labels = [];
              } else if (selected.metric === 'paths-comparison') {
                scope.labels = [];
              } else if (selected.metric === 'conversion') {
                scope.flags.showLabels = true;
                scope.flags.showConversionSelection = true;
                scope.labels = conversionLabels;
              } else {
                scope.flags.showLabels = true;
                scope.labels = _.map(selected.metric_values, function (m) {
                  return {name: m, checked: true};
                });
              }
            }
            scope.reportName = selected.metric + '_Report';
          }, 100);
        };

        scope.updateBuckets = function (metric_values) {
          var min = scope.selectedMetric.metric_values_range[0],
            max = scope.selectedMetric.metric_values_range[1],
            step = scope.selectedMetric.step;

          scope.sliderValue = metric_values;
          var nVal = metric_values;
          var result = '';

          // TODO[sabr]: This should be moved out to the service
          if (nVal[0] !== min) {
            result += min + ' - ' + nVal[0] + ' | ';
            if (_.uniq(nVal).length !== 1) {
              result += (nVal[0] + step) + ' - ' + nVal[1];
            }
          } else {
            result += nVal[0] + ' - ' + nVal[1];
          }

          if (nVal[1] !== max) {
            if ((nVal[1] + step) !== max) {
              result += ' | ' + (nVal[1] + step) + ' - ' + max;
            } else {
              result += ' | ' + max;
            }
          }

          scope.selectedMetric.metric_values = nVal;
          scope.resultMetric = result;
        };

        function validatePath() {
          return (scope.selectedPaths && scope.selectedPaths.length === 2 && _.pluck(scope.selectedPaths, 'measure').length === 2);
        }

        function getMetricValues() {
          if (scope.selectedMetric.metric === 'paths-comparison') {
            var validation = validatePath();
            if (!validation) {
              toaster.pop('error', 'No selection to compare: please select at least 2 paths for running comparative analysis');
              scope.analyzing = false;
              return;
            }
            return scope.selectedPaths;
          } else if (scope.selectedMetric.metric === 'stage-paths') {
            if (!scope.selectedNodes || _.isEmpty(scope.selectedNodes)) {
              toaster.pop('error', 'No selection to compare: please select at least 2 stages for running comparative analysis');
              scope.analyzing = false;
              return;
            }
            return scope.selectedNodes;
          } else if (scope.selectedMetric.metric === 'conversion') {
            if (_.every(scope.labels, function (l) { return !l.checked; })) {
              toaster.pop('error', 'No labels selected: please select at least 1 label');
              scope.analyzing = false;
              return;
            }
            return _.pluck(_.where(scope.labels, {checked: true}), 'name');
          } else if (scope.selectedMetric.metric_type === 'Boolean') {
            return ['true', 'false'];
          } else if (scope.selectedMetric.metric_type === 'Numeric') {
            return scope.sliderValue.toString().split(',')
          } else if (scope.selectedMetric.metric_type === 'Label') {
            return _.pluck(_.where(scope.labels, {checked: true}), 'name');
          }
        }

        function getAnalysisType() {
          var CLASSIFICATION = 'classification',
            REGRESSION = 'regression';

          if (scope.flags.showSlider) {
            var diff = Utils.compareArrays(scope.sliderValue, scope.selectedMetric.metric_values_range);
            if (diff) {
              return REGRESSION;
            } else {
              return CLASSIFICATION;
            }
          } else {
            return CLASSIFICATION;
          }
        }

        initParams();

        scope.$watch('analysisFilters', function (nVal) {
          if (!nVal) return;
          filters = nVal;
        }, true);

        scope.$on('ANALYSIS_PARAMS_CHANGED', function (e, data) {
          extraParams = data;
          resetAnalysisParams();
        });
      }
    }
  }
})();
