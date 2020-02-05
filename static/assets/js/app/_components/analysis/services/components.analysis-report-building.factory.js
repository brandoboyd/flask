(function () {
  'use strict';

  angular.module('slr.analysis')
    .factory('AnalysisReport', AnalysisReport);

  /** @ngInject*/
  function AnalysisReport(Utils,
                          $window,
                          AnalysisService,
                          AnalysisClassification,
                          AnalysisRegression,
                          AnalysisRest) {
    var Analysis = new AnalysisRest();

    var getParsedSemantics = function (results) {
      _.each(results, function (r, rI) {
        results[rI].key = (r.key.replace(/[_:]/g, ' '));
      });

      return results;
    };

    var disableFlags = function () {
      return {
        showBar: false, showPie: false,
        showScatter: false, showTrend: false,
        showBoxPlot: false, showSwitchBtns: false,
        showTable: false, showCharts: true, showMultichart: false
      }
    };

    var deleteReport = function (report, callback) {
      Analysis.remove(report.id)
        .success(function (res) {
          callback(res);
        });
    };

    var buildReport = function (report, callback) {
      var metricData;
      var tabs = [];

      if (_.has(report.filters, 'facets')) {
        _.extend(report, {dynFacets: report.filters.facets});
        delete report.filters.facets;
      }

      _.extend(report, {
        parsedFilters: Utils.objToArray(report.filters),
        parsedResults: _.sortBy(Utils.objToArray(report.results), function (r) {
            return r.value.discriminative_weight || r.value.score;
          }).reverse()
      });

      var arr = [];
      _.each(report.parsedResults, function (r, index) {
        if (report.analysis_type === 'classification') {
          report.parsedResults[index].value.crosstab_results = Utils.objToArray(r.value.crosstab_results);
        }

        if (r.key === report.analyzed_metric) {
          metricData = report.parsedResults[index];
        } else {
          arr.push(report.parsedResults[index]);
        }
      });

      report.parsedResults = getParsedSemantics(arr);

      report.parsedFilters.forEach(function (obj) {
        if (['from', 'to'].indexOf(obj.key) >= 0) {
          obj.value = moment.utc(obj.value).local().format('lll');
        }
      });

      var diff = Utils.compareArrays(report.metric_values, report.metric_values_range);

      if (report.analysis_type == 'classification' ||
        (report.metric_values && report.metric_values.length > 1 && diff)) {
      }

      _.extend(report, {parsed_analyzed_metric: report.analyzed_metric});

      _.each(report.parsedResults, function (r) {
        if (r.value.values.length) {
          tabs.push({
            name: r.key,
            active: false
          });
        }
      });

      report.width = $window.innerWidth - 500;

      delete report.results;

      AnalysisService.setAsBuilt();  // this marks the flag as true, and already built (pre-processed) reports won't be built again

      callback({
        report: report,
        metricData: metricData,
        tabs: tabs
      });
    };

    var exportTable = function (report, selectedFeature) {
      var blob = new Blob([document.getElementById('table-results').innerHTML], {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;charset=utf-8"
      });
      saveAs(blob, report.title + ' - ' + selectedFeature + ".xls");
    };

    var selectFeature = function (data, callback) {
      var report = data.report;
      var analysis_type = report.analysis_type;

      if (_.isUndefined(analysis_type) || analysis_type == null) {
        analysis_type = (report.metric_values.length > 1 && report.metric_values !== ['0', '10'])
          ? 'classification' : 'regression';
      }

      if (analysis_type == 'classification') {
        AnalysisClassification.getSelectedFeatureData(data, function (rep) {
          callback(rep);
        });
      } else if (analysis_type == 'regression') {
        AnalysisRegression.getSelectedFeatureData(data, function (rep) {
          callback(rep);
        });
      }
    };

    var paginate = function (direction, charts, chart) {
      _.each(charts, function (c) {
        if (chart.chart_id === c.chart_id) {
          var rS = c.offset * c.page, rE = c.offset * (c.page + 1);
          var lS = c.offset * (c.page - 2), lE = c.offset * (c.page - 1);

          if (direction === 'right' && c.page + 1 <= Math.ceil(c.full_data.length / c.offset)) {
            if (chart.settings.chart_type === 'BAR') {
              c.data = c.full_data;
              c.data[0].values = c.full_data[0].values.slice(rS, rE);
            } else {
              c.data = c.full_data.slice(rS, rE);
            }
            c.page++;
          } else if (direction === 'left' && c.page - 1 >= 1) {
            if (chart.settings.chart_type === 'BAR') {
              c.data = c.full_data;
              c.data[0].values = c.full_data[0].values.slice(lS, lE);
            } else {
              c.data = c.full_data.slice(lS, lE);
            }
            c.page--;
          }
        }
      });

      return charts;
    };

    return {
      buildReport: buildReport,
      selectFeature: selectFeature,
      exportTable: exportTable,
      disableFlags: disableFlags,
      deleteReport: deleteReport,
      paginate: paginate,
      getParsedSemantics: getParsedSemantics
    }
  }
}());