(function() {
  'use strict';

  var callWithJQuery;

  callWithJQuery = function(pivotModule) {
    if (typeof exports === "object" && typeof module === "object") {
      return pivotModule(require("jquery"));
    } else if (typeof define === "function" && define.amd) {
      return define(["jquery"], pivotModule);
    } else {
      return pivotModule(jQuery);
    }
  };

  callWithJQuery(function($) {
    function parseData(pivotData, opts) {
      // ------------------------------------
      // Transform pivot data into chart data
      //
      var response = {
        'list': [],
        'xAxisValues': []
      };

      var defaults = {
        localeStrings: {
          vs: "vs",
          by: "by"
        }
      };
      opts = $.extend(true, defaults, opts);

      var rowKeys = pivotData.getRowKeys();
      if (rowKeys.length === 0) {
        rowKeys.push([]);
      }
      var colKeys = pivotData.getColKeys();
      if (colKeys.length === 0) {
        colKeys.push([]);
      }
      var columns = [];

      _.each(rowKeys, function(rowKey) {
        var row = [];
        _.each(colKeys, function(colKey, index) {
          var agg = pivotData.getAggregator(rowKey, colKey);
          var val = agg.value();
          var point = [index];
          if (val != null) {
            if ($.isNumeric(val)) {
              if (val < 1) {
                point.push(parseFloat(val.toPrecision(3)));
              } else {
                point.push(parseFloat(val.toFixed(3)));
              }
            } else {
              point.push(val);
            }
          } else {
            point.push(0);
          }
          row.push(point);
        });
        columns.push(row);
      });

      var keys = _.map(rowKeys, function (k) {
        var rowHeader = k.join("-");
        var row = rowHeader === "" ? pivotData.aggregatorName : rowHeader;
        return _.extend({}, {key: row});
      });
      var values = _.map(columns, function (v) {
        return _.extend({}, {values: v});
      });

      response.xAxisValues = _.map(colKeys, function(k) {
        return k.join("-");
      });

      response.list = _.map(keys, function(k, i) {
        return _.extend(k, values[i]);
      });

      var xAxisLabel = '';
      var yAxisLabel = '';
      var title = '';
      var groupByTitle = '';

      yAxisLabel = pivotData.aggregatorName + (pivotData.valAttrs.length ? "(" + (pivotData.valAttrs.join(", ")) + ")" : "");
      xAxisLabel = pivotData.colAttrs.join('-');

      title = pivotData.aggregatorName + (pivotData.valAttrs.length ? "(" + (pivotData.valAttrs.join(", ")) + ")" : "");
      if (xAxisLabel != '') {
        title += ' ' + opts.localeStrings.vs + ' ' + xAxisLabel;
      }

      groupByTitle = pivotData.rowAttrs.join('-');
      if (groupByTitle) {
        title += ' ' + opts.localeStrings.by + ' ' + groupByTitle;
      }

      response.xAxisLabel = xAxisLabel;
      response.yAxisLabel = yAxisLabel;
      response.title = title;
      return response;
    }

    function showTitle(title) {
      d3.select('.pvtRendererArea svg')
        .append("text")
        .attr("x", 50)
        .attr("y", 50)
        .style('font-size', '20px')
        .style('font-weight', 'bold')
        .attr("text-anchor", "start")
        .text(title);
    }

    function increaseAxisLabel() {
      d3.selectAll('.nv-axislabel')
        .style('font-weight', 'bold')
        .style('font-size', '15px');
    }

    return $.pivotUtilities.d3_renderers = {
      'Line Chart': function (pivotData, opts) {
        var parsedData = parseData(pivotData, opts);

        nv.addGraph(function () {
          var chart = nv.models.lineChart()
            .margin({'left': 100, 'right': 100, 'bottom': 100})
            .x(function (d) {
              return d[0];
            })
            .y(function (d) {
              return d[1];
            })
            .useInteractiveGuideline(true)
            .showLegend(true)
            .showXAxis(true)
            .showYAxis(true);

          chart.xAxis
            .axisLabel(parsedData.xAxisLabel)
            .axisLabelDistance(40)
            .staggerLabels(true)
            .tickPadding(10)
            .tickFormat(function(d) {
              return parsedData.xAxisValues[d];
            });


          chart.yAxis
            .tickPadding(10)
            .axisLabel(parsedData.yAxisLabel);

          var yAxisFormat = ',.0d';
          chart.yAxis.tickFormat(d3.format(yAxisFormat));

          chart.legend.margin({top:40, bottom:40});

          // Append svg element with the help of d3 selector
          // @ref https://github.com/novus/nvd3/issues/338
          d3.select('.pvtRendererArea')
              .append("svg")
              .attr("style", "height:600px");

          d3.select('.pvtRendererArea svg')
              .datum(parsedData.list)
              .transition(350)
              .call(chart);

          showTitle(parsedData.title);
          increaseAxisLabel();


          nv.utils.windowResize(chart.update);

          return chart;
        });

      },
      'Stacked Area Chart': function (pivotData, opts) {
        var parsedData = parseData(pivotData, opts);

        nv.addGraph(function () {
          var chart = nv.models.stackedAreaChart()
              .margin({'left': 100, 'right': 100, 'bottom': 100})
              .x(function (d) {
                return d[0];
              })
              .y(function (d) {
                return d[1];
              })
              .useInteractiveGuideline(true)
              .showLegend(true)
              .showXAxis(true)
              .showYAxis(true);

          chart.xAxis
              .axisLabel(parsedData.xAxisLabel)
              .axisLabelDistance(40)
              .staggerLabels(true)
              .tickPadding(10)
              .tickFormat(function(d) {
                return parsedData.xAxisValues[d];
              });


          chart.yAxis
              .tickPadding(10)
              .axisLabel(parsedData.yAxisLabel);

          var yAxisFormat = ',.0d';
          chart.yAxis.tickFormat(d3.format(yAxisFormat));

          chart.legend.margin({top:40, bottom:40});

          // Append svg element with the help of d3 selector
          // @ref https://github.com/novus/nvd3/issues/338
          d3.select('.pvtRendererArea')
              .append("svg")
              .attr("style", "height:600px");

          d3.select('.pvtRendererArea svg')
              .datum(parsedData.list)
              .transition(350)
              .call(chart);

          showTitle(parsedData.title);
          increaseAxisLabel();
          //Change the controls position a little down
          //d3.select('.nv-controlsWrap')
          //    .attr('transform', 'translate(0,-30)');

          nv.utils.windowResize(chart.update);

          return chart;
        });

      },
      'Bar Chart': function (pivotData, opts) {
        var parsedData = parseData(pivotData, opts);

        nv.addGraph(function () {
          var chart = nv.models.multiBarChart()
              .margin({right:100, bottom:100, left:100})
              .x(function (d) {
                return d[0];
              })
              .y(function (d) {
                return d[1];
              })
              .reduceXTicks(true)
              .showControls(true)
              .staggerLabels(true);

          chart.xAxis
              .axisLabel(parsedData.xAxisLabel)
              .axisLabelDistance(40)
              .showMaxMin(false)
              .tickPadding(10)
              .tickFormat(function(d) {
                return parsedData.xAxisValues[d];
              });

          chart.yAxis
              .tickPadding(10)
              .axisLabel(parsedData.yAxisLabel);

          var yAxisFormat = ',.0d';

          chart.yAxis.tickFormat(d3.format(yAxisFormat));

          chart.legend.margin({top:40, bottom:40});

          // Append svg element with the help of d3 selector
          // @ref https://github.com/novus/nvd3/issues/338
          d3.select('.pvtRendererArea')
              .append("svg")
              .attr("style", "height:600px");

          d3.select('.pvtRendererArea svg')
              .datum(parsedData.list)
              .transition(350)
              .call(chart);

          showTitle(parsedData.title);
          increaseAxisLabel();
          //d3.select('.nv-controlsWrap')
          //    .attr('transform', 'translate(0,-30)');

          nv.utils.windowResize(chart.update);

          return chart;
        });

      }
    };
  });

}).call(this);

//# sourceMappingURL=d3_renderers.js.map