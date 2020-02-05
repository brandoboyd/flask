(function () {
  'use strict';

  angular.module('slr.analysis')
    .factory('AnalysisClassification', AnalysisClassification);

  /** @ngInject */
  function AnalysisClassification(Utils, $timeout) {

    var getPositions = function (cr, buckets) {
      var positions = [];
      var keys = _.keys(cr.value); // bucket index
      var values = _.values(cr.value); // % percentages

      _.each(buckets, function (buck, buckIndex) {
        _.each(keys, function (k, i) {
          if (buckIndex.toString() === k) {
            positions.push({
              key: cr.key,
              bucket: buck.trim(),
              value: Math.round(values[i])
            });
          }
        });
      });

      if (_.has(cr.value, '-1')) {
        var key = cr.key == 'None' ? '0' : cr.key;

        positions.push({
          key: key,
          bucket: 'N/A',
          value: Math.round(cr.value['-1'])
        });
      }

      return positions;
    };

    var getTrendData = function (timerange, buckets) {
      var data = [];

      _.each(timerange, function (t) {
        var foundBucket = buckets[t.class_key];
        if (angular.isDefined(foundBucket)) {
          data.push({
            label: foundBucket,
            data: t.timerange
          });
        }
      });

      return data;
    };

    var getDataForBar = function (crosstab_results, buckets) {
      var barData = [];
      var all = [];

      _.each(crosstab_results, function (cr) {
        var positions = getPositions(cr, buckets);
        all.push(positions);
      });

      var flatten = _.flatten(all);
      var allBuckets = _.uniq(_.pluck(flatten, 'bucket'));

      _.each(allBuckets, function (b) {
        if (['n/a'].indexOf(b.toLowerCase()) >= 0) return;  // '0 - 0 '
        var founds = _.where(flatten, {bucket: b});
        var values = [];

        _.each(founds, function (f) {
          values.push({
            x: f.key,
            y: Math.round(f.value)
          });
        });

        barData.push({
          key: b,
          values: values
        });
      });

      return barData;
    };

    var getDataForPie = function (crosstab_results, buckets) {
      var pieData = [];
      var all = [];

      _.each(crosstab_results, function (cr) {
        var positions = getPositions(cr, buckets);
        all.push(positions);
      });

      var flattenAll = _.flatten(all);
      var allBuckets = _.uniq(_.pluck(flattenAll, 'bucket'));

      _.each(allBuckets, function (b) {
        //if (b == '0 - 0') return;
        var foundVals = _.where(flattenAll, {bucket: b});
        var sum = 0;

        _.each(foundVals, function (fv) {
          sum += fv.value;
        });

        pieData.push({
          label: b,
          value: {
            sum: sum,
            data: _.without(foundVals, 'bucket')
          }
        });
      });

      return pieData;
    };

    var getSelectedFeatureData = function (data, callback) {
      var report = data.report;
      var metricData = data.metricData;
      var flags = data.flags;
      var feature = data.feature;
      var charts = [];
      var feature_order;

      report.buckets = report.metric_values.toString().split(',');

      if (feature === 'Overall') {
        var timerange = getTrendData(report.timerange_results, report.buckets);
        buildTable(report.parsedResults, report.buckets);

        if (timerange.length) {
          flags.showTrend = true;
          charts.push({
            data: timerange,
            settings: {
              chart_type: 'LINE',
              yAxisLabel: 'Count',
              yAxisFormat: '.f',
              height: '400px',
              level: report.level,
              visible: flags.showTrend
            },
            header: report.parsed_analyzed_metric + ' Trends',
            width: !_.isEmpty(metricData) ? 65 : 100
          });
        }

        if (!_.isEmpty(metricData)) {
          var pieData = getDataForPie(metricData.value.crosstab_results, report.buckets);

          flags.showPie = true;
          charts.push({
            data: pieData,
            settings: {
              isMetric: true,
              chart_type: 'PIE',
              height: '400px',
              visible: flags.showPie
            },
            class: 'pull-right',
            header: 'Pie chart',
            width: 33
          });
        }

      } else {
        /** Other Features */
        var filtered = [];

        _.each(report.parsedResults, function (pr) {
          if (pr.key === feature) {
            filtered.push(pr);
          }
        });

        if (filtered[0].value.crosstab_results.length > 30) {
          var _pieData = getDataForPie(filtered[0].value.crosstab_results, report.buckets);
          var pieProcessedData = [];

          _.each(_pieData, function(each) {
            var values = _.pluck(each.value.data, 'key');

            pieProcessedData.push({
              label: each.label,
              value: each.value.data.length, // count
              avg_val: Utils.mean(values)
            });
          });

          flags.showPie = true;
          charts.push({
            data: pieProcessedData,
            settings: {
              isMetric: true,
              tooltipSpecialKey: {label: 'Mean value', key: 'avg_val'},
              labelType: 'count',
              valueFormat: '.f',
              chart_type: 'PIE',
              height: '400px',
              visible: flags.showPie
            },
            class: 'pull-right',
            header: 'Pie chart',
            width: 100
          });
        } else {
          flags.showBar = true;
          var barData = getDataForBar(filtered[0].value.crosstab_results, report.buckets);

          charts.push({
            data: barData,
            settings: {
              chart_type: 'BAR',
              stacked: true,
              height: '400px',
              isMetric: true,
              yAxisLabel: 'Percentage',
              xAxisLabel: filtered.key,
              visible: flags.showBar
            },
            header: 'Bar chart',
            width: 100
          });
        }


        if (filtered[0].value.discriminative_weight) {
          feature_order = Utils.roundUpTo2precision(filtered[0].value.discriminative_weight);
        }

        buildTable(filtered, report.buckets);
      }

      callback({
        flags: flags,
        feature_order: feature_order,
        charts: _.map(charts, function (c) {
          return _.extend(c, {chart_id: Math.floor((1 + Math.random()) * 0x10000).toString(16)});
        })
      });
    };

    // special cross-table for classification
    function buildTable(parsedResults, buckets) {
      angular.element('#table-results > table').remove();

      var table = document.createElement('table'),
        thead = document.createElement('thead'),
        tbody = document.createElement('tbody');

      table.className = 'table table-default';

      var trHead = document.createElement('tr');
      var emptyHead = document.createElement('th');

      if (parsedResults.length > 1) {
        emptyHead.setAttribute('colspan', 2);
      } else {
        emptyHead.innerHTML = 'Value';
      }

      emptyHead.setAttribute('width', '20%');
      trHead.appendChild(emptyHead);

      // thead
      _.each(buckets, function (el) {
        var th = document.createElement('th');
        th.innerHTML = el;
        trHead.appendChild(th);
      });

      var lastHead = document.createElement('th');
      lastHead.innerHTML = 'N / A';
      trHead.appendChild(lastHead);

      thead.appendChild(trHead);
      table.appendChild(thead);

      /** tbody */
      _.each(parsedResults, function (pr) {

        _.each(pr.value.crosstab_results, function (cr, index) {
          var tr = document.createElement('tr');

          // label
          if (index === 0 && parsedResults.length > 1) {
            var tdLabel = document.createElement('td');
            tdLabel.setAttribute('rowspan', pr.value.crosstab_results.length);
            tdLabel.style.fontWeight = 'bold';

            var span = document.createElement('span');
            var space = document.createElement('br');
            span.className = 'badge';

            if (parsedResults.length > 1) {
              var weight = pr.value.discriminative_weight;
              if (weight >= 0.7) {
                span.style.backgroundColor = '#4AC764';
              } else if (weight <= 0.5) {
                span.style.backgroundColor = '#EA4F6B';
              }
              span.innerHTML = Utils.roundUpTo2precision(weight);
            }

            tdLabel.innerHTML = pr.key.replace(/_/g, ' ');
            tdLabel.appendChild(space);
            tdLabel.appendChild(span);
            tr.appendChild(tdLabel);
          }

          // key
          if (cr.key === 'null') {
            cr.key = 'n/a';
          }
          var td = document.createElement('td');
          td.setAttribute('colspan', 1);
          td.innerHTML = cr.key;
          tr.appendChild(td);

          var values = _.values(cr.value); // % percentages
          _.each(buckets, function (buck, buckIndex) {
            var tdValue = document.createElement('td');
            tdValue.setAttribute('colspan', 1);

            tdValue.innerHTML = Math.round(parseFloat(values[buckIndex])) + ' %';

            tr.appendChild(tdValue);
            //}
          });

          if (_.has(cr.value, '-1')) {
            var tdNA = document.createElement('td');
            tdNA.setAttribute('colspan', 1);
            tdNA.innerHTML = Math.round(cr.value['-1']) + ' %';
            tr.appendChild(tdNA);
          }

          tbody.appendChild(tr);
        });
      });

      table.appendChild(tbody);

      $timeout(function() {
        angular.element('#table-results').append(table);
      });
    }

    return {
      buildTable: buildTable,
      getSelectedFeatureData: getSelectedFeatureData,
      getDataForPie: getDataForPie,
      getDataForBar: getDataForBar,
      getTrendData: getTrendData,
      getPositions: getPositions
    }
  }
}());