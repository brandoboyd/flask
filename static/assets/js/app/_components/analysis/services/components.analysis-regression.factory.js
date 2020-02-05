(function () {
  'use strict';

  angular.module('slr.analysis')
    .factory('AnalysisRegression', AnalysisRegression);

  /** @ngInject */
  function AnalysisRegression(Utils, $timeout) {

    function buildModeStatement(list) {
      var mode = Utils.roundUpTo2precision(list[0]), repeat = list[1], res = '';
      if (repeat > 1 && !isNaN(repeat) && !isNaN(mode)) {
        res += mode + ' (Repeats ' + repeat + ' times)';
      } else {
        res = mode;
      }
      return res;
    }

    var getSelectedFeatureData = function (data, callback) {
      // TODO[sabr]: Add eager objects initialization - $scope.charts for example
      var charts = [];
      var feature = data.feature;
      var flags = data.flags;
      var report = data.report;
      var score;
      var table;

      var integer = '.0f';

      if (feature == 'Overall') {
        flags.showMultichart = true;
        var lineBarChart = _.map(report.timerange_results, function (each, index) {
          var isMetric = each.label !== report.analyzed_metric;
          return {
            key: each.label,
            bar: isMetric,
            color: isMetric ? '#4AC764' : '#EA4F6B',
            values: each.data
          };
        });

        charts.push({
          data: lineBarChart,
          header: "Overall",
          settings: {
            chart_type: 'LINEBAR',
            charts_settings: [
              { type: 'bar', color: '#4AC764', yAxis: 1 }, // count
              { type: 'line', color: '#EA4F6B', yAxis: 2 } // metric
            ],
            height: '400px',
            yAxisFormat: integer,
            level: report.level,
            isMetric: true,
            yAxisLabel: report.analyzed_metric,
            yAxis2Label: lineBarChart[1].key,
            visible: flags.showMultichart
          }
        });

        table = {
          thWidths: ['45px', '48%', '48%'],
          th: ['Rank', 'Feature', 'Feature Score'],
          tr: _.map(report.parsedResults, function (pr) {
            return {td: [pr.value.rank, pr.key, Utils.roundUpTo2precision(pr.value.score)]};
          })
        };

      } else {
        var filtered = _.find(report.parsedResults, {key: feature}).value;
        var _data, _full_data = [], page = 0;
        score = Utils.roundUpTo2precision(filtered.score);

        if (filtered.value_type === 'Label') {
          // categorical feature
          var cat_descriptive_analysis = [];
          _.each(filtered.boxplot, function (cr) {
            var values = cr.values || cr.value;
            cat_descriptive_analysis.push({
              feature_value: cr.label,
              mean: Utils.roundUpTo2precision(values.mean),
              mode: buildModeStatement(values.mode),
              median: Utils.roundUpTo2precision(values['Q2'])
            });
          });

          if (filtered.boxplot.length > 40) {
            _full_data = filtered.boxplot;
            _data = filtered.boxplot.slice(0, 40);
            page = 1;
          } else {
            _data = filtered.boxplot;
          }

          flags.showBoxChart = true;
          // flags.showPie = true;
          charts.push({
            data: _data,
            full_data: _full_data,
            header: "Box plot",
            width: 100, // %
            offset: _full_data.length ? 40 : 0,
            page: page,
            settings: {
              chart_type: 'BOXPLOT',
              isMetric: true,
              height: '400px',
              yDomain: report.metric_values_range,
              yAxisFormat: integer,
              yAxisLabel: report.parsed_analyzed_metric || 'Metric',
              xAxisLabel: feature,
              showXAxis: _data.length <= 10,
              visible: flags.showBoxChart
            }
          });

          // charts.push({
          //   data: filtered.pie,
          //   header: "Pie chart",
          //   width: 33,
          //   class: 'pull-right',
          //   settings: {
          //     chart_type: 'PIE',
          //     height: '400px',
          //     valueFormat: integer,
          //     visible: flags.showPie
          //   }
          // });

          table = {
            thWidths: ['120px', '30%', '30%', '30%'],
            th: ['Feature Value', 'Mean', 'Median', 'Mode'],
            tr: _.map(cat_descriptive_analysis, function (ua) {
              return {td: [ua['feature_value'], ua['mean'], ua['median'], ua['mode']]}
            })
          };
        } else {
          // continuous feature
          var cont_cat_descriptive_analysis = _.map(filtered.boxplot, function (ua) {
            return {
              feature_value: ua.label,
              mean: Utils.roundUpTo2precision(ua.values.mean),
              mode: buildModeStatement(ua.values.mode),
              median: Utils.roundUpTo2precision(ua.values['Q2'])
            };
          });

          /** Scatter */
          // if (filtered.scatter.length > 40) {
          //   _full_data = filtered.scatter;
          //   _data = filtered.scatter.slice(0, 40);
          //   page = 1;
          // } else {
          //   _data = filtered.scatter;
          // }

          /** Boxplot */
          var boxplot = [], _boxplot;
          if (filtered.boxplot.length > 40) {
            boxplot = filtered.boxplot;
            _boxplot = filtered.boxplot.slice(0, 40);
            page = 1;
          } else {
            _boxplot = filtered.boxplot;
          }

          flags.showBoxChart = true;
          charts.push({
            data: _boxplot,
            full_data: boxplot,
            header: "Box plot",
            width: 100, // %
            offset: boxplot.length ? 40 : 0,
            page: page,
            settings: {
              chart_type: 'BOXPLOT',
              isMetric: true,
              height: '400px',
              yDomain: report.metric_values_range,
              showXAxis: true,
              xAxisFormat: integer,
              yAxisFormat: integer,
              yAxisLabel: report.parsed_analyzed_metric || 'Metric',
              xAxisLabel: feature,
              visible: flags.showBoxChart
            }
          });

          /** Scatter plot */
          // flags.showScatter = true;
          // charts.push({
          //   data: _data,
          //   full_data: _full_data,
          //   offset: _full_data.length ? 40 : 0,
          //   page: page,
          //   header: "Scatter plot",
          //   settings: {
          //     chart_type: 'SCATTER',
          //     width: 100,
          //     isMetric: true,
          //     categorized: false, // need to check if Feature Values has labels
          //     height: '400px',
          //     yDomain: report.metric_values_range,
          //     yAxisLabel: report.parsed_analyzed_metric || 'Metric',
          //     xAxisLabel: feature,
          //     visible: flags.showScatter
          //   }
          // });

          /** Bar chart */
          var barData = [], _barData;
          if (filtered.bar.length > 40) {
            _barData = filtered.bar.slice(0, 40);
          } else {
            _barData = filtered.bar;
          }

          _barData[0].metric = report.parsed_analyzed_metric;

          flags.showBar = false;
          flags.showSwitchBtns = true;
          charts.push({
            data: _barData,
            full_data: barData,
            offset: barData.length ? 40 : 0,
            page: page,
            settings: {
              chart_type: 'BAR',
              stacked: false,
              height: '400px',
              yAxisFormat: integer,
              xAxisFormat: integer,
              yDomain: report.metric_values_range,
              yAxisLabel: 'Count',
              xAxisLabel: '', // TODO[sabr]: until Feature value has categories
              visible: flags.showBar
            },
            header: 'Bar chart',
            width: 100
          });

          /** Table */
          table = {
            thWidths: ['100px', '30%', '30%', '30%'],
            th: ['Feature', 'Mean', 'Median', 'Mode'],
            tr: _.map(cont_cat_descriptive_analysis, function (ua) {
              return {td: [ua['feature_value'], ua['mean'], ua['median'], ua['mode']]}
            })
          };
        }
      }

      buildTable(table);

      callback({
        feature_order: score,
        table: table,
        flags: flags,
        charts: _.map(charts, function (c) {
          return _.extend(c, {chart_id: Math.floor((1 + Math.random()) * 0x10000).toString(16)});
        })
      });
    };

    function buildTable(tableData) {
      angular.element('#table-results > table').remove();

      var table = document.createElement('table'),
        thead = document.createElement('thead'),
        tbody = document.createElement('tbody');

      table.className = 'table table-default';

      var trHead = document.createElement('tr');

      // head
      _.each(tableData.th, function(th, i) {
        var emptyHead = document.createElement('th');
        emptyHead.setAttribute('style', 'width: ' + tableData.thWidths[i]);
        emptyHead.innerHTML = th;
        trHead.appendChild(emptyHead);
      });

      // body
      _.each(tableData.tr, function(tr) {
        var emptyRow = document.createElement('tr');
        _.each(tr.td, function(td) {
          var emptyCell = document.createElement('td');
          emptyCell.innerHTML = td;
          emptyRow.appendChild(emptyCell);
        });
        tbody.appendChild(emptyRow);
      });

      thead.appendChild(trHead);
      table.appendChild(thead);
      table.appendChild(tbody);
      $timeout(function() {
        angular.element('#table-results').append(table);
      });
    }

    return {
      getSelectedFeatureData: getSelectedFeatureData,
      buildTable: buildTable
    }
  }
}());