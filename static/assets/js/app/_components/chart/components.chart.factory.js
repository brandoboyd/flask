(function () {
  'use strict';

  angular
    .module('slr.chart')
    .factory('ChartFactory', ChartFactory);

  /** @ngInject */
  function ChartFactory(Utils) {

    // ------------------------------------------
    // Parse "Metrics" data response for Predictors
    //
    var parseMetricsData = function (response) {
      return _.map(response, function (item) {
        return {
          'key': item.label,
          'values': item.data
        };
      });
    };

    var d3Call = function (dom, data, chart, callback) {
      try {
        d3.select(dom)
          .datum(data)
          .transition().duration(350)
          .call(chart);
      } catch (e) {
        console.error(e);
        callback(true);
      }
    };

    // -----------------------------------------
    // Parse "Trends" data
    //
    var parseTrendsData = function (response) {
      var plot_d3_data = _.map(response, function (item) {
        return {key: item.label.toLowerCase(), values: item.data}
      });

      // Unify the timestamps for all stacks in case of multiple stacks
      // Add 0 values for missing timestamps
      // Number of data points may vary per stacks which results in d3 error
      if (plot_d3_data.length > 1) {
        var timestamps = [];
        _.each(plot_d3_data, function (series) {
          _.each(series.values, function (point) {
            timestamps.push(point[0]);
          })
        });
        timestamps = _.chain(timestamps)
          .uniq()
          .sortBy(function (n) {
            return n;
          })
          .value();

        _.each(plot_d3_data, function (series) {
          var newValues = [];
          _.each(timestamps, function (time) {
            var newPoint = _.find(series.values, function (point) {
              return point[0] == time;
            });
            if (!newPoint) newPoint = [time, 0];
            newValues.push(newPoint);
          });
          series.values = newValues;
        });
      }

      return plot_d3_data;
    };

    var setXAxisTimeFormat = function (chart, level) {
      switch (level) {
        case('hour'):
          chart.xAxis.tickFormat(function (d) {
            return d3.time.format('%a, %I %p')(new Date(d))
          });
          break;
        case('day'):
          chart.xAxis.tickFormat(function (d) {
            return d3.time.format('%d %b')(new Date(d))
          });
          break;
        case('month'):
          chart.xAxis.tickFormat(function (d) {
            return d3.time.format('%B')(new Date(d))
          });
          break;
        default:
          chart.xAxis.tickFormat(function (d) {
            return moment(d).calendar();
          });
      }
    };

    // -----------------------------------------
    // Colors
    //
    var genesysColors = ["#2E69DB", "#5E99FF", "#9BBCE0", "#5A6B8C", "#0F6A51", "#569180", "#14819C",
      "#7EC0C2", "#AFD6D2", "#584FB3", "#7272E0", "#B9B9F0", "#575746", "#827C75", "#C9C4B7", "#8C6542",
      "#8A4D67", "#C48C88", "#EBC8BE", "#724787", "#B07EC2", "#D1B4D9"];
    var ordinalColors = ['#4AC764', '#EA4F6B', '#F8A740', '#203B73'].concat(genesysColors); // green, red, orange, blue

    var getDefinedColors = function (d, i) {
      var k = d.label || d.key;

      var nps = ["promoter", "passive", "detractor"];
      var status = ["converted", "stuck", "abandoned"];
      var process = ["finished", "ongoing", "abandoned"];
      var sentiments = ["positive", "neutral", "negative"];

      function getColor(arr, value) {
        var colors = d3.scale.ordinal()
          .domain(arr)
          .range(['#4AC764', '#F8A740', '#EA4F6B']); // green, orange, red
        return colors(value);
      }

      if (nps.indexOf(k) >= 0) {
        return getColor(nps, k);
      } else if (status.indexOf(k) >= 0) {
        return getColor(status, k);
      } else if (process.indexOf(k) >=0){
        return getColor(process, k);
      } else if (sentiments.indexOf(k) >= 0) {
        return getColor(sentiments, k);
      } else {
        return ordinalColors[i] || '#'+(Math.random()*0xFFFFFF<<0).toString(16);
      }
    };

    var getGenesysColors = function () {
      return genesysColors;
    };

    var getOrdinalColors = function () {
      return ordinalColors;
    };

    var setTimeTooltip = function(chart, yFormat) {
      chart.interactiveLayer.tooltip.contentGenerator(function (data) {
        var series = data.series;
        var tpl = '<h5 style="padding-left: 5px;"><b>' + moment(data.value).calendar() + '</b></h5>';
        tpl += '<table><tbody>';
        var percentage = '';
        if (!yFormat) {
          percentage = '%';
        }

        _.each(series, function (d, i) {
          tpl += '<tr>' +
            '<td class="legend-color-guide"><div style="background-color:' + getDefinedColors(d, i) + ';"></div></td>' +
            '<td class="key">' + d.key + '</td>' +
            '<td class="value">' + Utils.roundUpTo2precision(d.value) + percentage + '</td>' +
            '</tr>'
        });

        tpl += '</tbody></table>';
        return tpl;
      });
    };

    var getFilterValue = function (chart, scope, timestamp, mouseY) {
      console.log('scope.chartData', scope.chartData);
      console.log('scope.level', scope.level);
      console.log('scope.settings', scope.settings);
      console.log('timestamp', timestamp);
      console.log('mouseY', mouseY);

      var yScale = chart.yAxis.scale();
      var pointYValue = yScale.invert(mouseY);
      console.log('pointYValue', pointYValue);

      // find the index of clicked point in the x-axis data
      var xIndex = -1;
      var verticalGapSecond = scope.level === 'day' ? 24 * 3600 * 1000 : 3600 * 1000;
      console.log('verticalGapSecond', verticalGapSecond);

      _.each(scope.chartData[0].data, function (data, idx) {
        if (Math.abs(data[0] - timestamp) < verticalGapSecond) {
          xIndex = idx;
          return false;
        }
      });

      if (xIndex === -1) {
        console.log("xIndex not found.");
        return;
      }
      console.log('xIndex', xIndex);

      // find active legends to match with series label name in chartData
      // use case-insensitive matching
      var selectedLegends = angular.element('svg g.nv-legendWrap g.nv-series')
        .has('circle[style*="fill-opacity: 1"]')
        .map(function (idx, series) {
          var elm = angular.element(series);
          var legend = elm.find('title');
          if (!legend.length) {
            legend = elm.find('text');
          }
          return legend.text().toLowerCase();
        })
        .toArray();
      console.log('selectedLegends', selectedLegends);

      // find the y-values at the point of click (same as seen on tooltip)
      var clickedVerticalLineValues = _.chain(scope.chartData)
        .filter(function (series) {
          return selectedLegends.indexOf(series.label.toLowerCase()) >= 0;
        })
        .map(function (series) {
          return series.data[xIndex][1];
        })
        .value();
      console.log('clickedVerticalLineValues', clickedVerticalLineValues);

      var hotspotYCoordinates = [];
      var chartType = scope.settings.chart_type;
      if (chartType === 'LINE') {
        hotspotYCoordinates = clickedVerticalLineValues;
      } else if (chartType === 'STACKED') {
        var base = 0;
        hotspotYCoordinates = _.map(clickedVerticalLineValues, function (y) {
          base += y;
          return base;
        });
      } else {
          throw Error("Couldn't compute filter value for chart type '" + scope.settings.chart_type + "'.");
      }
      console.log('hotspotYCoordinates', hotspotYCoordinates);

      // find the height of the current graph in the same unit as that of y-axis
      var highestYCoordinates = [];
      var rowVectors = _.chain(scope.chartData)
        .filter(function (series) {
          return selectedLegends.indexOf(series.label.toLowerCase()) >= 0;
        })
        .map(function (series) {
          return _.map(series.data, function (elm) {
            return elm[1];
          });
        })
        .value();
      console.log('rowVectors', rowVectors);

      _.each(rowVectors, function (vector) {
        if (!highestYCoordinates.length) {
          highestYCoordinates = vector;
        } else {
          for (var i = 0; i < vector.length; i++) {
            if (chartType === 'LINE') {
              highestYCoordinates[i] = Math.max(highestYCoordinates[i], vector[i]);
            } else if (chartType === 'STACKED') {
              highestYCoordinates[i] += vector[i];
            }
          }
        }
      });
      console.log('highestYCoordinates', highestYCoordinates);

      var graphHeight = Math.max.apply(Math, highestYCoordinates);
      console.log('graphHeight', graphHeight);
      // find the radius of the hotspot circle ~ 6px
      var hotspotRadius = graphHeight - yScale.invert(6);
      console.log('hotspotRadius', hotspotRadius);

      var legendIndex = -1;
      _.each(hotspotYCoordinates, function (y, i) {
        // tooltip won't show highlighting, so treat whole data point as same region
        // if highlighting would work (as with data with 3 or more series),
        // north hemisphere of data point would lie in upper region, while south one in lower region
        var tolerance = selectedLegends.length <= 2 ? hotspotRadius : 0;
        if (pointYValue - y <= tolerance) {
          legendIndex = i;
          return false;
        }
      });
      console.log('legendIndex', legendIndex);

      if (legendIndex === -1) {
        // Regard click on the hotspot circle at the top most data series as the
        // click on data point, though highlighting in tooltip will not 'highlight' the series label
        if (pointYValue - hotspotYCoordinates[hotspotYCoordinates.length - 1] <= hotspotRadius) {
          legendIndex = clickedVerticalLineValues.length - 1;
        } else {
          console.log("Couldn't detect the series.");
          return;
        }
      }
      console.log('legendIndex', legendIndex);

      var legend = selectedLegends[legendIndex];
      console.log('legend', legend);

      var chartDataSeries = _.find(scope.chartData, function (series) {
        if (legend === series.label.toLowerCase()) {
          return series;
        }
      });
      console.log('chartDataSeries', chartDataSeries);

      var filterValue = chartDataSeries._internalLabel || chartDataSeries.label;
      console.log('filterValue', filterValue);
      return filterValue;
    };

    return {
      parseTrendsData: parseTrendsData,
      parseMetricsData: parseMetricsData,
      getGenesysColors: getGenesysColors,
      getOrdinalColors: getOrdinalColors,
      getDefinedColors: getDefinedColors,
      d3Call: d3Call,
      setXAxisTimeFormat: setXAxisTimeFormat,
      setTimeTooltip: setTimeTooltip,
      getFilterValue: getFilterValue
    }
  }
})();
