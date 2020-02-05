(function () {
  'use strict';
  angular
    .module('slr.chart')
    .directive('chart', chart);

  // TODO: 1) sankey requires some flexibility, it is very tied to Journeys
  //       2) funnels should be placed here too from omni...funnels.js with flexibile data structure
  //       3) drilldowns should be flexible too - they are tied to the specific event name

  /**
   * Settings may include:
   * @chart_type: PIE / STACKED / LINE / SANKEY / SCATTER / BOXPLOT / BAR / MULTICHART / DISCRETEBAR / LINEBAR
   * @yAxisFormat: String
   * @yAxisLabel: String
   * @xAxisFormat: String
   * @xAxisLabel: String
   * @valueFormat: String
   * @isMetric: Boolean
   * @level: hour / day / month
   * @xAxisLabel: String
   * @target: OMNI_CUSTOMERS / OMNI / OMNI_AGENTS / ANALYTICS / REPORTS / PREDICTORS
   * @drilldownEnabled: Boolean
   * @labelType: String
   * @active_filter: Object
   * @stacked: Boolean
   * @computed_metric: csat
   */

  /** @ngInject */
  function chart($rootScope, $window, ChartFactory, Utils, PlotTypes, FilterService) {
    return {
      restrict: 'E',
      replace: false,
      scope: {
        chartData: '=',
        settings: '='
      },
      template: '<svg ng-show="chartData.length || chartData.links.length"></svg>' +
      '<div class="alert alert-info text-center" ng-hide="chartData.length || chartData.links.length">' +
      '<i class=\'icon-alert-triangle\'></i> ' + '{{settings.noDataMsg || "No Data Available"}}' +
      '</div>',
      link: function (scope, element) {

        scope.$watch('chartData', function (newData) {
          if (!newData) return;

          var chartType;

          if (scope.settings) {
            chartType = scope.settings.chart_type;
          }

          switch (chartType) {
            case('PIE'):
              drawPieChart();
              break;
            case('STACKED'):
              drawStackedChart();
              break;
            case('LINE'):
              drawLineChart();
              break;
            case('SANKEY'):
              drawSankeyChart();
              break;
            case('SCATTER'):
              drawScatterChart();
              break;
            case('BOXPLOT'):
              drawBoxChart();
              break;
            case('BAR'):
              drawBarChart();
              break;
            case('MULTICHART'):
              drawMultiChart();
              break;
            case('DISCRETEBAR'):
              drawDiscreteBar();
              break;
            case('LINEBAR'):
              drawLineBar();
              break;
          }
        });

        var drilldown = function (type, params, target) {
          if (target == 'REPORTS') {
            var group_by = PlotTypes.getActiveFilter();
            if (group_by) {
              params.filterName = group_by + 's';
            }
            scope.$emit('reports.details.' + type, params);
          } else if (target == 'ANALYTICS') {
            scope.$emit('analytics.details.' + type, params);
          } else if (target == 'OMNI') {
            params.drilldown = true;
            scope.$apply();
            scope.$emit('journeys.details.' + type, params);
          } else if (target == 'OMNI_CUSTOMERS') {
            scope.$emit('customers.details.' + type, params);
          } else if (target == 'OMNI_AGENTS') {
            scope.$emit('agents.details.' + type, params);
          } else if (target == 'PREDICTORS') {
            scope.$emit('predictors.details.' + type, params);
          }
        };

        function drawLineBar() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var yFormat = scope.settings.yAxisFormat;
            var chart = nv.models.linePlusBarChart()
                .margin({right: 50, bottom: 85, top: 50})
                .options({focusEnable: false})
                //We can set x data accessor to use index. Reason? So the bars all appear evenly spaced.
                .x(function (d, i) { return i })
                .y(function (d, i) { return d[1] });

            if (scope.settings.isMetric) {
              var Yvalues = [];
              _.each(scope.chartData, function (p) {
                if (!_.has(p, 'values')) return;
                _.each(p.values, function (v) {
                  Yvalues.push(v[1]);
                });
              });
              chart.y1Axis.ticks([_.min(Yvalues), _.max(Yvalues)]);
            }

            if (yFormat) {
              chart.y1Axis.tickFormat(d3.format(yFormat));
              chart.y2Axis.tickFormat(d3.format(yFormat));
            }

            // TODO: moveout this
            function convertTime(dx) {
              switch (scope.settings.level) {
                case('hour'):
                  return d3.time.format('%a, %I %p')(new Date(dx));
                  break;
                case('day'):
                  return d3.time.format('%d %b')(new Date(dx));
                  break;
                case('month'):
                  return d3.time.format('%B')(new Date(dx));
                  break;
                default:
                  return moment(dx).calendar();
              }
            }

            chart.xAxis.tickFormat(function (d) {
              var dx = scope.chartData[0].values[d] && scope.chartData[0].values[d][0] || 0;
              return convertTime(dx);
            });

            chart.bars.forceY([0]);

            chart.y1Axis.axisLabel('Count');

            chart.tooltip.contentGenerator(function (data) {
              var series = data.series;
              var time;
              var value;
              var color;

              if (data.data && data.data.length) {
                time = data.data[0];
                value = data.data[1];
                color = data.color;
              } else {
                time = data.point[0];
                value = data.point[1];
              }

              var tpl = '<h5 style="padding-left: 5px;"><b>' + convertTime(time) + '</b></h5>';
              tpl += '<table><tbody>';
              var percentage = '';
              if (!yFormat) {
                percentage = '%';
              }

              _.each(series, function (d, i) {
                var key;
                if (_.has(d, 'key')) {
                  key = d.key;
                } else if ((d.originalKey && 'count' in d.originalKey.toLowerCase()) || !_.has(d.key)) {
                  key = 'Count';
                }
                tpl += '<tr>' +
                  '<td class="legend-color-guide"><div style="background-color:' + d.color + ';"></div></td>' +
                  '<td class="key">' + key + '</td>' +
                  '<td class="value">' + Utils.roundUpTo2precision(d.value) + percentage + '</td>' +
                  '</tr>'
              });

              tpl += '</tbody></table>';
              return tpl;
            });

            d3.selectAll('.nvtooltip').remove();


            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);
            return chart;
          });
        }

        function drawDiscreteBar() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var parsedData;
            if (!_.has(scope.chartData[0], 'data')) {
              parsedData = [{key: 'Discrete Bar', values: scope.chartData}];
            } else {
              parsedData = ChartFactory.parseMetricsData(scope.chartData);
            }

            var chart = nv.models.discreteBarChart()
              .x(function (d) {
                return d.label;
              })
              .y(function (d) {
                return d.value;
              })
              .staggerLabels(true)
              .color(ChartFactory.getOrdinalColors())
              .showValues(true);

            if (scope.settings.valueFormat) {
              chart.valueFormat(d3.format(scope.settings.valueFormat));
            } else {
              chart.valueFormat(function (d) {
                return d + '%';
              });
            }

            if (scope.chartData.length > 10) {
              chart.showLegend(false);
            }

            chart.discretebar.dispatch.on("elementClick", function (e) {
              if (!scope.settings.drilldownEnabled) return;
              var active_filter = scope.settings.active_filter;
              var target = scope.settings.target;
              var params = {
                  filterName: active_filter,
                  filterValue: e.data._internalLabel || e.data.label
              };

              if (typeof nv.tooltip.cleanup == 'function') {
                nv.tooltip.cleanup();
              }



              d3.selectAll('.nvtooltip').remove(); // workaround for now to cleanup tooltips
              drilldown('distribution', params, target);
            });

            d3.selectAll('.nvtooltip').remove();

            ChartFactory.d3Call(dom, parsedData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);
            return chart;
          });
        }

        function drawMultiChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var parsedData = ChartFactory.parseMetricsData(scope.chartData);
            var yFormat = scope.settings.yAxisFormat;

            _.each(parsedData, function(d, i) {
              _.extend(parsedData[i], scope.settings.charts_settings[i]);
            });

            var chart = nv.models.multiChart()
              .useInteractiveGuideline(true)
              .x(function (d) { return d[0] || d['x']; })   //We can modify the data accessor functions...
              .y(function (d) { return d[1] })   //...in case your data is formatted differently.
              .margin({right: 85, bottom: 85});

            if (scope.settings.isMetric) {
              var Yvalues = [];
              _.each(scope.chartData, function (p) {
                if (!_.has(p, 'values')) return;
                _.each(p.values, function (v) {
                  Yvalues.push(v[1]);
                });
              });
              chart.yAxis1.ticks([_.min(Yvalues), _.max(Yvalues)]);
              chart.yAxis2.ticks([_.min(Yvalues), _.max(Yvalues)]);
            }

            if (yFormat) {
              chart.yAxis1.tickFormat(d3.format(yFormat));
              chart.yAxis2.tickFormat(d3.format(yFormat));
            }

            ChartFactory.setXAxisTimeFormat(chart, scope.settings.level);
            ChartFactory.setTimeTooltip(chart, yFormat);

            chart.yAxis1
              .axisLabel(scope.settings.yAxisLabel);
            chart.yAxis2
              .axisLabel(scope.settings.yAxis2Label);


            d3.selectAll('.nvtooltip').remove();

            ChartFactory.d3Call(dom, parsedData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);
            return chart;
          });
        }

        function drawLineChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var parsedData = ChartFactory.parseMetricsData(scope.chartData);
            var yFormat = scope.settings.yAxisFormat;

            var chart = nv.models.lineChart()
              .useInteractiveGuideline(true)    //Tooltips which show all data points. Very nice!
              .x(function (d) {
                return d[0];
              })   //We can modify the data accessor functions...
              .y(function (d) {
                return d[1]
              })   //...in case your data is formatted differently.
              .margin({right: 50, bottom: 85})
              .showXAxis(true)
              .showYAxis(true)
              .clipEdge(false)
              // .yDomain(scope.settings.yDomain)
              .color(function (d, i) {
                return ChartFactory.getDefinedColors(d, i)
              });

            if (scope.settings.isMetric) {
              var Yvalues = [], Xvalues = [];
              _.each(scope.chartData, function (p) {
                var values = p.values || p.data;
                if (!values) return;
                _.each(values, function (v) {
                  Yvalues.push(v[1]);
                  Xvalues.push(v[0] || v['x']);
                });
              });
              var ymin = _.min(Yvalues), ymax = _.max(Yvalues);
              chart.yAxis.ticks([ymin, ymax]);
              if (Xvalues.length > 20) {
                var xmin = _.min(Xvalues), xmax = _.max(Xvalues);
                var xmean = (xmin + xmax) * 0.5;
                chart.xAxis.tickValues([xmin, xmean, xmax]);
              }
            }

            if (yFormat && yFormat !== 's') {
              chart.yAxis.tickFormat(d3.format(yFormat))
            } else if (yFormat === 's') {
              chart.yAxis.tickFormat(function(d) {
                var format = d3.format('s');
                return format(Math.ceil(d/100)*100);
              });
            } else {
              chart.yAxis.tickFormat(function(d) {
                return d + '%';
              });
            }

            ChartFactory.setXAxisTimeFormat(chart, scope.settings.level);
            ChartFactory.setTimeTooltip(chart, yFormat);

            chart.xScale(d3.time.scale.utc());  // Align x-axis ticks exactly with actual data points

            chart.yAxis
              .axisLabel(scope.settings.yAxisLabel);

            chart.duration(0);
            d3.selectAll('.nvtooltip').remove();

            ChartFactory.d3Call(dom, parsedData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            nv.utils.windowResize(chart.update);

            return chart;
          }, function (chart) {
            chart.interactiveLayer.dispatch.on('elementClick', function (point) {
              if (!scope.settings.drilldownEnabled) return;

              var level = FilterService.getSelectedGraphLevel();
              scope.level = level;

              var start = moment.utc(point.pointXValue).startOf(level).valueOf();
              var end = moment.utc(point.pointXValue).startOf(level).add(level, 1).valueOf();
              var timestamp = moment.utc(point.pointXValue).valueOf();

              // The x-axis timestamp differs slightly form the original value
              // So select the most nearest timestamp
              if (end - timestamp > timestamp - start) {
                timestamp = start;
              } else {
                timestamp = end;
              }

              var filterValue = ChartFactory.getFilterValue(chart, scope, timestamp, point.mouseY);
              if (!filterValue) {
                return;
              }

              var target = scope.settings.target;
              var params = {
                timestamp: timestamp,
                filterName: scope.settings.active_filter,
                filterValue: filterValue
              };

              drilldown('trends', params, target);
            });
          });
        }

        function drawScatterChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var chart = nv.models.scatterChart()
              .x(function(d) { return d.x || d[0] })
              .y(function(d) { return d.y || d[1] })
              .showDistX(false)    //showDist, when true, will display those little distribution lines on the axis.
              .showDistY(false)
              .margin({bottom: 100})
              .yDomain(scope.settings.yDomain)
              .pointRange([45,50]);

            chart.tooltip.contentGenerator(function (point) {
              var header = '<h5 style="padding-left: 5px;">' + scope.settings.yAxisLabel + ': ' + point.point.y + '</h5>';
              var tpl = header + '<table><tbody>';

              tpl += '<tr>' +
                '<td class="legend-color-guide"><div style="background-color:' + point.point.color + ';"></div></td>' +
                '<td class="key">' + point.series[0].key + '</td>' +
                '<td class="value">' + Utils.roundUpTo2precision(point.point.x) + '</td>' +
                '</tr>';
              tpl += '</tbody></table>';
              return tpl;
            });

            if (scope.settings.isMetric) {
            }

            if (scope.settings.categorized) {
              chart.color(function (d, i) {
                return ChartFactory.getOrdinalColors()[i];
              });
            } else {
              chart.color(['#203B73']); // all points/bubbles are blue color
            }

            if (scope.chartData.length > 10) {
              chart.showLegend(false);
            }

            //Axis settings
            chart.xAxis.tickFormat(d3.format('.0f'))
              .axisLabel(scope.settings.xAxisLabel);
            chart.yAxis.axisLabel(scope.settings.yAxisLabel);

            chart.duration(0);

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            return chart;
          });
        }

        function drawBoxChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          nv.addGraph(function () {
            var chart = nv.models.boxPlotChart()
              .x(function (d) {
                return d.label || d.key;
              })
              .margin({bottom: 100})
              .staggerLabels(true)
              .showXAxis(false)
              .maxBoxWidth(75) // prevent boxes from being incredibly wide
              .yDomain(scope.settings.yDomain)
              ;

            if (scope.settings.isMetric) {
              chart.yAxis.tickFormat(d3.format(scope.settings.yAxisFormat));
            }

            if (scope.settings.categorized) {
              chart.color(function (d, i) {
                return ChartFactory.getOrdinalColors()[i];
              });
            } else {
              chart.color(['#203B73']); // all points/bubbles are blue color
            }

            chart.yAxis.axisLabel(scope.settings.yAxisLabel);

            if (scope.settings.showXAxis) {
              if (scope.chartData.length > 40) {
                chart.showXAxis(false);
              } else {
                chart.showXAxis(true);
              }
            }

            if (scope.settings.xAxisFormat) {
              chart.xAxis.tickFormat(d3.format(scope.settings.xAxisFormat));
            }

            chart.duration(0);

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            return chart;
          });
        }

        // -------------------------
        // Draw "Distribution" chart
        //
        function drawPieChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          var target = scope.settings.target;

          nv.addGraph(function () {
            var chart = nv.models.pieChart()
              .x(function (d) {
                if (_.has(d, 'label')) {
                  return d.label.toLowerCase();
                } else {
                  return d.key.toLowerCase();
                }
              })
              .y(function (d) {
                var value = 0;
                if (!_.has(d, 'value')) {
                  return d.data[0][1];
                }
                if (d.value) {
                  if (_.has(d.value, 'sum')) {
                    return d.value.sum;
                  } else {
                    return d.value;
                  }
                } else if (d.data && angular.isArray(d.data)) {
                  value = d.data[0][1];
                }
                return value;
              })
              .margin({bottom: 100})
              .showLabels(true)     //Display pie labels
              .labelsOutside(true)
              .labelThreshold(.05)  //Configure the minimum slice size for labels to show up
              // .labelType('percent') //Configure what type of data to show in the label. Can be "key", "value" or "percent"
              .color(ChartFactory.getOrdinalColors())
              .legendPosition('top');

            chart.labelType(scope.settings.labelType || 'percent');

            if (scope.settings.valueFormat) {
              chart.valueFormat(d3.format(scope.settings.valueFormat));
            } else {
              chart.valueFormat(function (d) {
                return d + '%';
              });
            }

            if (scope.chartData.length > 10) {
              chart.showLegend(false);
            }

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });

            // if (scope.settings.tooltipSpecialKey) {
            //   chart.tooltip.contentGenerator(function (point) {
            //     var header = '<h5 style="padding-left: 5px;">' + point.data.label + '</h5>';
            //     var tpl = header + '<table><tbody>';
            //
            //     tpl += '<tr>' +
            //       '<td class="legend-color-guide"><div style="background-color:' + point.color + ';"></div></td>' +
            //       '<td class="key">' + scope.settings.tooltipSpecialKey.label + ': ' + '</td>' +
            //       '<td class="value">' + Utils.roundUpTo2precision(point.data[scope.settings.tooltipSpecialKey.key]) + '</td>' +
            //       '</tr>';
            //     tpl += '</tbody></table>';
            //     return tpl;
            //   });
            // }

            // DRILLDOWN
            chart.pie.dispatch.on("elementClick", function (e) {
              if (!scope.settings.drilldownEnabled) return;
              var active_filter = scope.settings.active_filter;
              var params = {
                  filterName: active_filter,
                  filterValue: e.data._internalLabel || e.data.label
              };

              if (typeof nv.tooltip.cleanup == 'function') {
                nv.tooltip.cleanup();
              }

              d3.selectAll('.nvtooltip').remove(); // workaround for now to cleanup tooltips

              drilldown('distribution', params, target);
            });

            // Disable grow on hover of a slice
            // @ https://github.com/novus/nvd3/issues/884
            chart.growOnHover(false);
            return chart;
          });
        }

        function drawBarChart() {
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;


          nv.addGraph(function () {
            var chart = nv.models.multiBarChart()
              .reduceXTicks(false)   //If 'false', every single x-axis tick label will be rendered.
              .showXAxis(true)
              .rotateLabels(0)      //Angle to rotate x-axis labels.
              .showControls(scope.settings.stacked)   //Allow user to switch between 'Grouped' and 'Stacked' mode.
              .stacked(scope.settings.stacked)
              // .interpolate("linear") // don't smooth out the lines
              .groupSpacing(0.5)    //Distance between each group of bars.
              .margin({bottom: 100})
              ;

            if (!scope.settings.stacked) {
              chart.x(function(d) { return d.label});
              chart.y(function(d) { return d.count});
            }

            if (scope.chartData[0] && scope.chartData[0].values.length > 10 && scope.chartData[0].values.length <= 20) {
              chart.margin({bottom: 130});
              // chart.showLegend(false);
              d3.selectAll("g.tick.zero text")
                .style("text-anchor", "end")
                .attr("dx", "-.8em")
                .attr("dy", ".15em")
                .attr("font-size", "12px")
                .attr("transform", "rotate(-45)");
            } else if (scope.chartData[0].values.length > 20) {
              // chart.showLegend(false);
              chart.showXAxis(false);
            } else if (scope.chartData.length === 1) {
              chart.showLegend(false);
            } else {
              chart.margin({bottom: 100});
            }

            chart.color(function (d, i) {
              return ChartFactory.getDefinedColors(d, i);
            });

            if (scope.settings.isMetric) {
              var Xvalues = [], Yvalues = [];
              _.each(scope.chartData, function (p) {
                if (!_.has(p, 'values')) return;
                _.each(p.values, function (v) {
                  Xvalues.push(v['x'] || v[0]);
                  Yvalues.push(v['y'] || v[1]);
                });
              });
              chart.xAxis.ticks([_.min(Xvalues), _.max(Xvalues)]);
              chart.yAxis.ticks([_.min(Yvalues), _.max(Yvalues)]);
            }

            if (scope.settings.yAxisFormat) {
              chart.yAxis.tickFormat(d3.format(scope.settings.yAxisFormat))
            } else {
              chart.yAxis.tickFormat(function (d) {
                return d + '%'
              });
            }

            if (scope.settings.xAxisFormat) {
              chart.xAxis.tickFormat(d3.format(scope.settings.xAxisFormat));
            }

            chart.yAxis.axisLabel(scope.settings.yAxisLabel);
            chart.xAxis.axisLabel(scope.settings.xAxisLabel);

            chart.duration(0);

            ChartFactory.d3Call(dom, scope.chartData, chart, function (res) {
              if (res) {
                scope.chartData = [];
              }
            });
            return chart;
          });
        }

        // -------------------
        // Draw "Stacked Area" chart
        //
        function drawStackedChart() {
          var stackedChartViewMode = 'stack';
          var dom = angular.element(element).children('svg')[0];
          if (!dom) return;

          var parsedData;
          var target = scope.settings.target;
          if (target == 'OMNI') {
            parsedData = ChartFactory.parseTrendsData(scope.chartData);
          } else if (['ANALYTICS', 'PREDICTORS', 'REPORTS', 'JOBS'].indexOf(target) >= 0) {
            parsedData = ChartFactory.parseMetricsData(scope.chartData);
          }

          nv.addGraph({
            generate: function () {
              var chart = nv.models.stackedAreaChart()
                .useInteractiveGuideline(true)    //Tooltips which show all data points. Very nice!
                .margin({right: 50})
                .x(function (d) {
                  return d[0]
                })   //We can modify the data accessor functions...
                .y(function (d) {
                  return d[1]
                })   //...in case your data is formatted differently.
                .showXAxis(true)
                .showYAxis(true)
                .clipEdge(false)
                .style(stackedChartViewMode)
                .color(function (d, i) {
                  return ChartFactory.getDefinedColors(d, i)
                });

              chart.showControls(false);  // hide controls and display only Stacked graph
              //chart._options.controlOptions = ['Stacked'];  // hide 'Stream' and 'Expanded' options

              //Format x-axis labels with custom function.
              //chart.xAxis
              //  .showMaxMin(false)
              //.tickValues(d3.range(chart.xAxis.scale().domain()[1], chart.xAxis.scale().domain()[1]));

              ChartFactory.setXAxisTimeFormat(chart, scope.settings.level);

              chart.xScale(d3.time.scale.utc());  // Align x-axis ticks exactly with actual data points

              chart.yAxis
                .axisLabel(scope.settings.yAxisLabel);

              var yAxisFormat = scope.settings.yAxisFormat;

              if (!yAxisFormat) {
                if (_.has(scope.settings, 'computed_metric')) {
                  yAxisFormat = ',.1f';
                } else {
                  yAxisFormat = ',.0d';
                }
              }

              chart.yAxis.tickFormat(d3.format(yAxisFormat));

              d3.select(dom).selectAll('*').remove();
              d3.selectAll('.nvtooltip').remove();

              ChartFactory.d3Call(dom, parsedData, chart, function (res) {
                if (res) {
                  scope.chartData = [];
                }
              });

              if (!scope.chartData.length) {
                d3.select('.nvd3').remove();
              }

              function disableAreaClick() {
                chart.stacked.dispatch.on("areaClick.toggle", null);

                if (chart.update) {
                  var originalUpdate = chart.update;

                  chart.update = function () {
                    originalUpdate();
                    disableAreaClick();
                  };
                }
              }

              disableAreaClick();

              nv.utils.windowResize(chart.update);

              return chart;
            },
            callback: function (chart) {
              chart.dispatch.on('stateChange', function (e) {
                stackedChartViewMode = e.style;
              });

              chart.interactiveLayer.dispatch.on('elementClick', function (point) {
                if (!scope.settings.drilldownEnabled) return;

                var level = FilterService.getSelectedGraphLevel();
                scope.level = level;

                var start = moment.utc(point.pointXValue).startOf(level).valueOf();
                var end = moment.utc(point.pointXValue).startOf(level).add(level, 1).valueOf();
                var timestamp = moment.utc(point.pointXValue).valueOf();

                // The x-axis timestamp differs slightly form the original value
                // So select the most nearest timestamp
                if (end - timestamp > timestamp - start) {
                  timestamp = start;
                } else {
                  timestamp = end;
                }

                var filterValue = ChartFactory.getFilterValue(chart, scope, timestamp, point.mouseY);
                if (!filterValue) {
                  return;
                }

                var target = scope.settings.target;
                var params = {
                  timestamp: timestamp,
                  filterName: scope.settings.active_filter,
                  filterValue: filterValue
                };

                drilldown('trends', params, target);
              });
            }
          });
        }

        // -------------------
        // Draw "Sankey" chart
        //
        function drawSankeyChart() {
          d3.selectAll('svg > *').remove();

          var dom = angular.element(element).children('svg')[0];

          var container = angular.element(element).parent().get(0);

          if (!dom) return;

          if (!scope.chartData.links) return;

          var graph = scope.chartData;  // same variable name as in journeys module
          var units = "Journeys";

          var steps = _.last(graph.nodes)['xPos'];

          var stepWithMaxNodes = _.chain(graph.nodes)
            .flatten()
            .groupBy('xPos')
            .map(function (value, key) {
              return {'step': key, 'value': value.length}
            })
            .max(function (step) {
              return step.value;
            })
            .value();

          var nodesWidth = steps > 4 ? 100 : 150;
          var nodePadding = 50; //steps > 4 ? 50 : 80;

          var widthConst = steps <= 3 ? steps * (nodesWidth * 3) : steps * (nodesWidth * 2);
          var heightConst = stepWithMaxNodes.value <= 4 ? $window.innerHeight-350 : $window.innerHeight;

          var margin = {top: 10, right: 10, bottom: 100, left: 10},
            width = widthConst - margin.left - margin.right,
            height = heightConst - margin.top - margin.bottom;

          var formatNumber = d3.format(",.0f"),    // zero decimal places
            format = function (d) {
              return formatNumber(d) + " " + units;
            },
            color = d3.scale.category20(),

            groupColor = d3.scale.ordinal()
              .domain(["Promoter", "Passive", "Detractor", "Not Present", "All"])
              .range(["green", "orange", "red", "grey", "#5E99FF"]);

          // append the svg canvas to the page
          var svg;
          if (dom) {
            svg = d3.select(dom);
          } else {
            svg = d3.select(element).append('svg');
          }
          svg
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .attr("transform",
              "translate(" + margin.left + "," + margin.top + ")");

          // Set the sankey diagram properties
          var sankey = d3.sankey()
            .nodeWidth(nodesWidth)
            .nodePadding(nodePadding)
            .size([width, height])
            .sinksRight(false);
          var path = sankey.link();

          sankey
            .nodes(graph.nodes)
            .links(graph.links)
            .layout(32);

          // add in the links
          var link = svg.append("g").selectAll(".link")
            .data(graph.links)
            .enter()
            .append("path")
            .attr("class", "link")
            .attr("d", path)
            .attr("id", function (d, i) {
              d.id = i;
              return "link-" + i;
            })
            .style("stroke-width", function (d) {
              return Math.max(1, Math.sqrt(d.dy));
              //return Math.max(1, d.dy);
            })
            .style("stroke", function (d) {
              return groupColor(d.group_name);
            })
            .style("stroke-opacity", 0.4)
            .sort(function (a, b) {
              return b.dy - a.dy;
              //return b.y - a.y;
            });

          // add the link titles
          link.append("title")
            .text(function (d) {
              var group_by = d.group_name ? d.group_name : "All"
              var label = d.source.name + " > " +
              d.target.name + "\n" + format(d.value);
              return label + "\n" + "GROUP BY: " + group_by;
            });

          // add in the nodes
          var node = svg.append("g").selectAll(".node")
            .data(graph.nodes)
            .enter().append("g")
            .attr("class", "node")
            .attr("id", makeId('node'))
            .attr("step", function (d) {
              return d.xPos;
            })
            .attr("data-clicked", 0)
            .attr("transform", function (d) {
              return "translate(" + d.x + "," + d.y + ")";
            });

          // add the rectangles for the nodes
          node.append("rect")
            .attr("y", 20)
            .attr("height", function (d) {
              if (d.dy < 20) {
                return 20
              } else {
                return d.dy;
              }
            })
            .attr("class", "stage")
            .attr("width", sankey.nodeWidth())
            .style("fill", function (d, i) {
              return d.color = '#f5f5f5'
            })
            .style("stroke", function (d) {
              return "#999"
            })
            .append("title")
            .text(function (d) {
              return d.name + "\n" + formatNumber(d.count);
            });

          //title rectangle
          node.append("rect")
            .attr("y", 0)
            .attr("height", function (d) {
              return 20
            })
            .attr("width", sankey.nodeWidth())
            .style("fill", function (d, i) {
              return d.color = d3.rgb(color(d.name.replace(/ .*/, ""))).darker(1)
            })
            .style("stroke", function (d) {
              return d3.rgb(d.color).darker(2);
            });

          // add in the title for the nodes
          node.append("text")
            .attr("class", "nodeLabel");

          node.selectAll("text.nodeLabel")
            .attr("x", 6)
            .attr("y", function (d) {
              return 10;
            })
            .attr("dy", ".35em")
            .attr("text-anchor", "start")
            .attr("transform", null)
            .text(function (d) {
              return d.name.split(":")[0]
            });

          node.append("text")
            .attr("class", "nodeValue")
            .text(function (d) {
              return d.name /* + "\n" + format(d.value)*/;
            });

          node.selectAll("text.nodeValue")
            .attr("x", 6)
            .attr("y", function (d) {
              return 32;
            })
            .attr("dy", ".35em")
            .attr("text-anchor", "start")
            .attr("transform", null)
            .text(function (d) {
              var sansStage = d.name.split(":");
              sansStage.shift();
              return sansStage.length > 0 ? sansStage.join(":") + ":" + formatNumber(d.count) : formatNumber(d.count);
            });

          // add the rectangles for the nodes
          node.append("rect")
            .filter(
              function(d,i) {
                var droppedOff = _.find(d.sourceLinks, function(item) {
                  //truthy
                  return ~item.target.name.indexOf('Abandon');
                })
                return !_.isEmpty(droppedOff);
              }
            )
            .attr("y", function(d) {
              return d.dy
            })
            .attr("x", function(d) {
              return d.dx-20
            })
            .attr("height", function (d) {
              return 20
            })
            .attr("class", "abandon")
            .attr("width", 20)
            .style("fill", function (d, i) {
              return 'red'
            })
            .append("title")
            .text(function (d) {
              return "Drop-Off";
            });

          node.append("text")
            .filter(
              function(d,i) {
                var droppedOff = _.find(d.sourceLinks, function(item) {
                  //truthy
                  return ~item.target.name.indexOf('Abandon');
                })
                return !_.isEmpty(droppedOff);
              }
            )
            .attr("class", "abandonValue");

          node.selectAll("text.abandonValue")
            .attr("y", function(d) {
              return d.dy + 15;
            })
            .attr("x", function(d) {
              return d.dx-20;
            })
            .attr("dx", ".36em")
            .attr("text-anchor", "start")
            .attr("transform", null)
            .style("fill", function (d, i) {
              return 'white'
            })
            .text(function (d) {
              return d.sourceLinks[0].target.count
            });



          var selected = {};
          var selectedData = {};
          var step = -1;

          function selectNodesToCompare(ctx, el) {
            var node = d3.select(ctx);
            var littleRect = node.select(".stage");

            if (node.classed('dimmed')) {
              return
            }

            var translation = d3.transform(node.attr("transform")).translate;

            var origWidth = parseInt(littleRect.attr("width"));
            var origHeight = parseInt(littleRect.attr("height"));


            var allNodesCount = svg.selectAll(".node")[0].length - 1;
            var lastStepNode = svg.selectAll(".node")[0][allNodesCount];
            var lastStep = d3.select(lastStepNode).attr('step');

            var allButSelected = null;


            if (node.attr("step") == lastStep || node.datum().sourceLinks.length == 0) {
              //don't select end nodes if the clicked one is in last step
              allButSelected = svg.selectAll(".node:not([step='" + node.attr("step") + "'])")
                .filter(function (d) {
                  return d.sourceLinks.length > 0
                })
            } else {
              allButSelected = svg.selectAll(".node:not([step='" + node.attr("step") + "'])");
            }

            allButSelected.classed("dimmed", true);

            //deselect selected
            if (node.attr("data-clicked") == "1") {
              svg.select('#selected' + node.attr("id")).remove();
              var prop = 'selected' + node.attr("id");
              delete selected[prop];
              delete selectedData[prop];
            } else {
              if (!node.classed('dimmed')) {
                var stageNode = svg.append("rect")
                  .attr("x", translation[0] - 5)
                  .attr("y", translation[1] - 5)
                  .attr("id", "selected" + node.attr("id"))
                  .attr("width", origWidth + 10)
                  .attr("height", origHeight + 30)
                  .style('stroke', 'red')
                  .style('stroke-width', '2')
                  .style('stroke-dasharray', '10 5')
                  .style('fill', 'none')
                selected[stageNode.attr('id')] = stageNode;
                selectedData[stageNode.attr('id')] = node.datum();
                step = node.attr("step");
              }

              if (_.keys(selected).length > 2) {
                var theKey = _.keys(selected)[0];
                var theId = selected[theKey].attr('id').replace('selected', '');
                //un-highlight the links
                var n = svg.select("#" + theId);
                highlight_node_links(n[0][0], n.datum());
                //remove highlight
                selected[theKey].remove();
                //remove the highlight rect
                delete selected[theKey]
                delete selectedData[theKey]
              }
            }


            if (_.keys(selected) == 0) {
              //allButSelected.classed("dimmed", false);
              svg.selectAll(".node").classed("dimmed", false);
            }


            var clicked = svg.selectAll("[data-clicked='1']");
            var analysisPanel = jQuery('#analysis');


            if (_.keys(selected).length == 2) {

              if (analysisPanel.is(':hidden')) {
                analysisPanel.show('fast');
              }

              var data = _.map(selectedData, function (d) {
                return {'stage': d.name, 'step': d.xPos}
              })
              $rootScope.$broadcast("OnNodesSelected", _.values(data))
            } else {

              if (analysisPanel.is(':visible')) {
                analysisPanel.hide('fast');
              }

            }

            highlight_node_links(ctx, el)
          }

          var currentObject = null;
          var drillDownMode = false;

          d3.selectAll(".link")
            .on("click", function (d) {
              var flow_params = {
                sourceName: d.source.name,
                targetName: d.target.name,
                step: d.source.xPos,
                filterValue: d.group_name,
              };
              $rootScope.$emit('journeys.details.flow.link', flow_params)
            })

          d3.selectAll(".node")
            .on("click", function (el) {
              if (drillDownMode) {
                var flow_params = {
                  stage: el.name,
                  step: el.xPos
                };
                $rootScope.$emit('journeys.details.flow.stage', flow_params)
              } else {
                d3.select(this).select(".stage").classed('highlight', false);
                selectNodesToCompare(this, el);
              }
            })

          d3.select('body').on('keydown', function (e) {
            if (d3.event.keyCode == 16) {
              drillDownMode = true;
              $rootScope.$broadcast("DRILL_DOWN_MODE", true)
            }
          })

          d3.select('body').on('keyup', function (e) {
            drillDownMode = false;
            $rootScope.$broadcast("DRILL_DOWN_MODE", false)
          })


          d3.selectAll(".link")
            .on("mouseover", function (d) {
              select_links_path(this, d)
            })
            .on("mouseout", function (d) {

              d3.selectAll('.link').classed('link-selected', false)
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.4);
            });

          d3.selectAll(".stage")
            .on("mouseover", function (d) {
              var parent = d3.select(this.parentNode);
              if (!parent.classed('dimmed')) {
                d3.select(this).classed('highlight', true);
                currentObject = this;
                highlight_node_links(this, d)
              }
            })
            .on("mouseout", function (d) {
              var parent = d3.select(this.parentNode);
              if (!parent.classed('dimmed')) {
                d3.select(this).classed('highlight', false);
                currentObject = null;
                highlight_node_links(this, d)
              }

            });

          function highlight_node_links(el, node) {

            var remainingNodes = [],
              nextNodes = [];

            var stroke_opacity = 0;
            if (d3.select(el).attr("data-clicked") == "1") {
              d3.select(el).attr("data-clicked", "0");
              stroke_opacity = 0;

            } else {
              d3.select(el).attr("data-clicked", "1");
              stroke_opacity = 1;
            }

            var traverse = [{
              linkType: "sourceLinks",
              nodeType: "target"
            }, {
              linkType: "targetLinks",
              nodeType: "source"
            }];


            var groupings = _.chain(node.sourceLinks.concat(node.targetLinks))
              .flatten()
              .pluck('group_name')
              .value();

            traverse.forEach(function (step) {
              node[step.linkType].forEach(function (link) {
                if (_.indexOf(groupings, link.group_name) > -1) {
                  remainingNodes.push(link[step.nodeType]);
                  highlight_link(link.id, stroke_opacity);
                }

              });

              while (remainingNodes.length) {
                nextNodes = [];
                remainingNodes.forEach(function (node) {
                  node[step.linkType].forEach(function (link) {
                    if (_.indexOf(groupings, link.group_name) > -1) {
                      nextNodes.push(link[step.nodeType]);
                      highlight_link(link.id, stroke_opacity);
                    }
                  });
                });
                remainingNodes = nextNodes;
              }

            });
            var selected = d3.select(el).classed('highlight');
            if (selected) {
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.1);
            } else {
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.4);
            }
          }

          function highlight_link(id, opacity) {
            //d3.select("#link-"+id).style("stroke-opacity", opacity);
            if (opacity > 0) {
              d3.select("#link-" + id).classed("link-selected", true);
            } else {
              d3.select("#link-" + id).classed("link-selected", false);
            }
          }

          function select_links_path(el, path) {
            var remainingNodes = [],
              nextNodes = [];

            var traverse = [{
              linkType: "sourceLinks",
              nodeType: "target"
            }, {
              linkType: "targetLinks",
              nodeType: "source"
            }];

            var grouping = path.group_name;

            remainingNodes.push(path);
            highlight_link(path.id, 1);

            traverse.forEach(function (step) {
              path[step.nodeType][step.linkType].forEach(function (link) {
                if (link.group_name == grouping) {
                  remainingNodes.push(link);
                  highlight_link(link.id, 1);
                }
              });

              while (remainingNodes.length) {
                nextNodes = [];
                remainingNodes.forEach(function (node) {
                  node[step.nodeType][step.linkType].forEach(function (link) {
                    if (link.group_name == grouping) {
                      nextNodes.push(link);
                      highlight_link(link.id, 1);
                    }
                  });
                });
                remainingNodes = nextNodes;
              }
            });

            var selected = d3.select(el).classed('link-selected');
            if (selected) {
              d3.selectAll(".link:not(.link-selected)").style("stroke-opacity", 0.1);
            }
          }

          function makeId(prefix) {
            prefix || (prefix = '');
            //return prefix + (Math.random() * 1e16).toFixed(0);
            var id = (function () {
              var a = 0;
              return function () {
                return prefix + a++
              }
            })();
            return id;
          }
        }
      }
    }
  }
})();
