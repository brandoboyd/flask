(function () {
  'use strict';

  angular
    .module('omni.journeys')
    .controller('JourneysReportsCtrl', JourneysReportsCtrl);

  /** @ngInject */
  function JourneysReportsCtrl($scope, AnalysisService, AnalysisReport, $rootScope, $window, $stateParams,
                               JourneyTypesRest,
                               JourneyTagsRest,
                               JourneyFunnelsRest,
                               ChannelsRest) {
    var JourneyTypes = new JourneyTypesRest(),
      JourneyTags = new JourneyTagsRest(),
      JourneyFunnels = new JourneyFunnelsRest(),
      _ChannelsRest = new ChannelsRest();
    var reports = AnalysisService.getReports();

    var init = function () {
      $scope.reports = [];
      $scope.ready = false;
      $scope.layout = {
        slimscroll: {
          height: '850px',
          wheelStep: 25,
          width: '215px'
        }
      };
      $scope.flags = AnalysisReport.disableFlags();
      angular.element('#analysis').hide();

      $scope.reports = _.sortBy(reports, 'created_at').reverse();

      if (!AnalysisService.isBuilt()) {
        _.each($scope.reports, function (report, index) {
          AnalysisReport.buildReport(report, function (rep) {
            $scope.reports[index] = rep.report;
            $scope.reports[index].tabs = rep.tabs;
            $scope.reports[index].metric_buckets = rep.report.metric_values;
            $scope.reports[index].parsedFilters = getParsedJourneyFilters(rep.report);
            if (rep.metricData) {
              $scope.reports[index].metricData = rep.metricData;
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
        if (AnalysisService.isEmpty()) {
          return;
        }

        var debounce = _.debounce(function () {
          reports = AnalysisService.getReports();
          initReports();
        }, 10);
        debounce();
      }
    }

    function getParsedJourneyFilters(report) {
      var filters = report.parsedFilters;
      var dynFacets = report.dynFacets;
      var funnel;

      var processed_facets = [];
      var facet_keys = _.keys(dynFacets);

      _.each(facet_keys, function (facet_key) {
        var facet_val = dynFacets[facet_key];
        if (dynFacets[facet_key].length) {
          facet_val = dynFacets[facet_key].join(', ');
        }
        processed_facets.push({
          key: facet_key,
          value: facet_val
        });
      });

      // values
      _.each(filters, function (f) {
        if (f.key == 'journey_type' && (f.value.length || f.value)) {
          if (f.value.length) {
            f.value = f.value[0]; // due to historical changes, journey_type can be the array of 1 only element...
          }
          JourneyTypes.getOne(f.value)
            .success(function (res) {
              f.value = res.data.display_name;
            });

        } else if (f.key === 'journey_tags' && f.value.length) {
          var jTags = [];
          _.each(f.value, function (id) {
            JourneyTags.getOne(id)
              .success(function (res) {
                jTags.push(res.data.display_name);
              });
          });
          f.value = jTags.join(', ').toString();

        } else if (f.key === 'funnel_id' && f.value) {
          JourneyFunnels.getOne(f.value)
            .success(function (res) {
              funnel = res.data;

              var found = _.findWhere(filters, {key: 'stage_id'});

              if (typeof found !== 'undefined') {
                JourneyTypes.getStages(funnel.journey_type)
                  .success(function (stage) {
                    filters[filters.indexOf(found)].value = _.findWhere(stage.data, {id: found.value}).display_name;
                  });
              }

              f.value = funnel.name;
            });
        } else if (f.key === 'channels' && f.value.length) {
          _ChannelsRest.getOne(f.value)
            .success(function (res) {
              f.value = res.item.title;
            });
        } else {
          f.value = f.value.toString();
        }
      });

      filters = _.without(filters, _.findWhere(filters, function (f) {
        return ['timerange', 'facets'].indexOf(f.key) >= 0;
      }));

      if (dynFacets) {
        filters = filters.concat(processed_facets);
      }

      return filters; // we already have - from, to
    }

    initReports();
  }
})();