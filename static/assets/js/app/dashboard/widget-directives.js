(function () {
    'use strict';
    angular
        .module('dashboard')
        .factory('uxSettings', uxSettings)
        .directive('trendChart', trendChart)
        .directive('distributionChart', distributionChart)
        .directive('funnelChart', funnelChart)
        .directive('topicsCloud', topicsCloud)
        .directive('stackedBarChart', stackedBarChart)
        .directive('distribBarChart', distribBarChart)
        .directive('horizontalBarChart', horizontalBarChart)
        .directive('pieChart', pieChart)
        .directive('trendBarChart', trendBarChart)
        .directive('tableDataChart', dataTableChart)
        .directive('addWidget', addWidget);

    function uxSettings() {
        return {
            'ordinalColors': getOrdinalColors(),
            'threeColors': getThreeColors(),
            'fourColors': getFourColors(),
        };

        function getGenesysColors() {
            return ["#2E69DB", "#5E99FF", "#9BBCE0", "#5A6B8C", "#0F6A51", "#569180", "#14819C",
                "#7EC0C2", "#AFD6D2", "#584FB3", "#7272E0", "#B9B9F0", "#575746", "#827C75", "#C9C4B7", "#8C6542",
                "#8A4D67", "#C48C88", "#EBC8BE", "#724787", "#B07EC2", "#D1B4D9"];
        }
        function getOrdinalColors() {
            return ['#4AC764', '#F8A740', '#EA4F6B', '#203B73'].concat(getGenesysColors());
        }
        function getThreeColors() {
            return ['#EA4F6B', '#F8A740', '#4AC764'].concat(getGenesysColors());
        }
        function getFourColors() {
            return ['#203B73', '#EA4F6B', '#F8A740', '#4AC764'].concat(getGenesysColors());
        }
    }

    function trendChart($rootScope, uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                postParams: '=',
                extraInfo: '='
            },
            template: '<svg ng-show="chartData" style="width:100%; height:100%"></svg>' +
                '<h3  ng-hide="chartData" style="position: absolute;top: 20%;left: 45%">No Data Available</h3>',
            link: function (scope, element) {
                // -------------------
                // Draw "Trends" chart
                //
                function drawStackedChart() {
                    if (!scope.chartData) {
                        return;
                    }
                    nv.addGraph(function () {

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
                            .color(uxSettings.ordinalColors);

                        //Format x-axis labels with custom function.

                        if (scope.chartData.length === 1) { // does not make sense when there's 1 legend
                            chart.showLegend(false);
                        }

                        chart.xAxis
                            .showMaxMin(false)
                            .tickFormat(function(d) {
                                if(scope.postParams.level !== 'hour') {
                                    return d3.time.format('%d %b')(new Date(d));
                                } else {
                                    return d3.time.format('%I%p')(new Date(d)).toLowerCase().replace(/^0+/, '');
                                }
                            });
                        chart.xScale(d3.time.scale.utc());  // Align x-axis ticks exactly with actual data points

                        var yAxisFormat = scope.extraInfo.yAxisFormat || ',.2f';
                        chart.yAxis
                            .axisLabel(scope.extraInfo.yAxisLabel)
                            .tickFormat(d3.format(yAxisFormat));

                        d3.select(svgDOM).selectAll('*').remove();
                        d3.select(container).selectAll('.nvtooltip').remove();

                        d3.select(svgDOM)
                            .datum(scope.chartData)
                            .transition().duration(350)
                            .call(chart);

                        nv.utils.windowResize(chart.update);


                        return chart;
                    });
                }

                var container = angular.element(element)[0];
                var svgDOM = angular.element(element).children('svg')[0];

                var debouncedRender = _.debounce(drawStackedChart, 500);
                $(container.parentElement).resize(debouncedRender);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRender();
                });
            }
        }
    }

    function distributionChart($rootScope, uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                postParams: '=',
                extraInfo: '='
            },
            template: '<svg ng-show="chartData" style="width:100%; height:100%"></svg>' +
            '<h3  ng-hide="chartData" style="position: absolute;top: 20%;left: 45%">No Data Available</h3>',
            link: function (scope, element) {
                // -------------------------
                // Draw "Distribution" chart
                //
                function drawPieChart() {
                    if (!scope.chartData) {
                        return;
                    }

                    var activeFilter = scope.extraInfo.active_filter;
                    var yAxisFormat = scope.extraInfo.yAxisFormat || ',.2f';

                    nv.addGraph(function () {
                        var chart = nv.models.pieChart()
                            .x(function (d) { return d.label.toLowerCase() })
                            .y(function (d) { return d.value })
                            .valueFormat(d3.format(yAxisFormat))
                            .showLabels(true)     //Display pie labels
                            .labelsOutside(true)
                            .labelThreshold(.05)  //Configure the minimum slice size for labels to show up
                            .labelType("percent") //Configure what type of data to show in the label. Can be "key", "value" or "percent"
                            //.donut(true)          //Turn on Donut mode. Makes pie chart look tasty!
                            .donutRatio(0.88)     //Configure how big you want the donut hole size to be.
                            .color(uxSettings.ordinalColors)
                            .legendPosition("right");

                        if (scope.chartData.length > 10) {
                            chart.showLegend(false); // TODO: ENCAPSULATE THEM IN SEPARATE POPOVER
                        }

                        d3.select(svgDOM)
                          .datum(scope.chartData)
                          .transition().duration(350)
                          .call(chart);

                        chart.pie.dispatch.on("elementClick", function (e) {
                            var params = {filterName: activeFilter, filterValue: e.label};
                              if (typeof nv.tooltip.cleanup == 'function') {
                                nv.tooltip.cleanup();
                              }
                              d3.selectAll('.nvtooltip').remove(); // workaround for now to cleanup tooltips
                            //$state.go('journeys.details.distribution', params)
                            $rootScope.$emit('journeys.details.distribution', params);
                        });

                        // Disable grow on hover of a slice
                        // @ https://github.com/novus/nvd3/issues/884
                        chart.growOnHover(false);

                        nv.utils.windowResize(chart.update);

                        return chart;
                    });
                }

                var container = angular.element(element)[0];
                var svgDOM = angular.element(element).children('svg')[0];

                var debouncedRender = _.debounce(drawPieChart, 500);
                $(container.parentElement).resize(debouncedRender);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRender();
                });
            }
        }
    }

    function funnelChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                postParams: '=',
                extraInfo: '='
            },
            template: '<svg id="funnel_{{widgetId}}" ng-show="chartData" style="width:100%; height:100%" class="stacked-bar-chart clickable-x-axis"></svg>' +
            '<h3  ng-hide="chartData" style="position: absolute;top: 20%;left: 45%">No Data Available</h3>',
            link: function (scope, element) {
                // -------------------
                // Draw "Funnel" chart
                //
                function drawFunnelChart() {
                    if (!scope.formattedData) {
                        return;
                    }
                    var domID = '#funnel_' + scope.widgetId + ' ';

                    var getJourneyStageName = function(stageId) {
                        if (scope.extraInfo && scope.extraInfo.journey_stages) {
                            return _.result(_.find(scope.extraInfo.journey_stages, {'id': stageId}), 'display_name');
                        }
                        return 'N/A';
                    };
                    var isLastStep = function(stepId) {
                        var temp = angular.copy(scope.extraInfo.funnel_steps);
                        return stepId == temp.pop();
                    };
                    var getTransitionPercent = function(stepId) {
                        var sum = 0;
                        var converted = 0;
                        var percent = 0;

                        _.each(scope.formattedData, function(seriesData) {
                            var value = _.result(_.find(seriesData.values, {'x': stepId}),'y');
                            if (seriesData.key == 'converted') converted = value;
                            sum += value;
                        });

                        if (converted > 0 && sum > 0) {
                            percent = converted / sum;
                        }
                        return percent;
                    };

                    var chartDrawFinished = function() {
                        // Show count of journeys on each bar snippet
                        d3.select(domID + 'g.labels').remove();
                        var allBars = d3.selectAll(domID + '.nv-bar')[0];
                        var gValues = d3.select(domID + '.nv-wrap g').append('g').classed('labels', true);

                        _.each(allBars, function(bar) {
                            var w = +bar.getAttribute('width');
                            var h = +bar.getAttribute('height');
                            var x = +bar.getAttribute('x');
                            var y = +bar.getAttribute('y');
                            var value = bar.__data__.y;

                            if (h < 20 || value == 0) return;
                            gValues.append('text')
                                .attr('text-anchor', 'middle')
                                .attr('fill', 'white')
                                .attr('x', x + w/2)
                                .attr('y', y + h/2 + 5)
                                .attr('series', bar.__data__.series)
                                .attr('stage', bar.__data__.x)
                                .attr('transform', bar.getAttribute('transform'))
                                .text(d3.format('s')(value))
                        });

                        // Show arrows with transition percent inside
                        d3.select(domID + 'g.arrows').remove();
                        var transBars = d3.selectAll(domID + '.nv-series-0 .nv-bar')[0];
                        var gArrows = d3.select(domID + '.nv-wrap g').append('g').classed('arrows', true);

                        _.each(transBars, function(bar) {
                            var barWidth = +bar.getAttribute('width');
                            var barHeight = +bar.getAttribute('height');
                            var x = barWidth * 2 - barWidth / 6;
                            var y = +bar.getAttribute('y') + barHeight / 2;
                            var w = barWidth * 2 / 3;
                            var h = 30;

                            var stepId = bar.__data__.x;
                            if (isLastStep(stepId)) return;
                            var percent = getTransitionPercent(stepId);

                            if (barHeight < h) {
                                y = y - h/2;
                            }

                            var pts = (x-w) + ',' + (y-h/2) + ' ' +
                                (x-.2*w) + ',' + (y-h/2) + ' ' +
                                x + ',' + y + ' ' +
                                (x-.2*w) + ',' + (y+h/2) + ' ' +
                                (x-w) + ',' + (y+h/2);

                            gArrows.append('polygon')
                                .attr('points', pts)
                                .attr('transform', bar.getAttribute('transform'))
                                .attr('style', 'fill: rgba(0,0,0,0.5);');

                            var px = barWidth + barWidth / 6 + barWidth * 4 / 15;

                            gArrows.append('text')
                                .attr('text-anchor', 'middle')
                                .attr('fill', 'white')
                                .attr('transform', bar.getAttribute('transform'))
                                .attr('x', px)
                                .attr('y', y + 5)
                                .text(d3.format('.3p')(percent));
                        });

                        // Show total count of journeys on top of each bar
                        d3.select(domID + 'g.labels-total').remove();
                        var totalBars = d3.selectAll(domID + '.nv-series-2 .nv-bar')[0];
                        var gTotalValues = d3.select(domID + '.nv-wrap g').append('g').classed('labels-total', true);

                        _.each(totalBars, function(bar) {
                            var w = +bar.getAttribute('width');
                            var x = +bar.getAttribute('x');
                            var y = +bar.getAttribute('y');
                            if (!isLastStep(bar.__data__.x)) return;

                            gTotalValues.append('text')
                                .attr('text-anchor', 'middle')
                                .attr('fill', 'black')
                                .attr('x', x + w/2)
                                .attr('y', y - 10)
                                .attr('transform', bar.getAttribute('transform'))
                                .text('END')
                        });

                        // Remove bars with zero value which are drawn as simple line
                        d3.selectAll(domID + '.nv-bar')
                            .attr('style', function(d) {
                                if (d.y == 0) return 'display:none';
                            });


                        // Draw buttons for x-axis ticks (steps)
                        var xAxisTicks = d3.selectAll(domID + '.nv-x .tick.zero text')[0];

                        _.each(xAxisTicks, function(tick) {
                            var rect = tick.getBBox();
                            var tickContainer = tick.parentElement;
                            if (!rect || !tickContainer) { return }
                                
                            var x = rect.x;
                            var y = rect.y;
                            var w = rect.width;
                            var h = rect.height;

                            d3.select(tickContainer)
                                .selectAll('rect')
                                .remove();

                            // When the graph is squeezed, x-axis tick might be hidden, 
                            // in this case, don't draw rect around it.
                            var isHidden = d3.select(tick).style('opacity') === '0';
                            if (isHidden) { return }

                            d3.select(tickContainer)
                                .insert('rect', 'text')
                                .attr('x', x - 20)
                                .attr('y', y - (30 - h) / 2)
                                .attr('rx', 4)
                                .attr('ry', 4)
                                .attr('width', w + 40)
                                .attr('height', 30);
                        });

                    };

                    nv.addGraph({
                        generate: function () {
                            var chart = nv.models.multiBarChart()
                                .showControls(false)
                                .showLegend(true)
                                .stacked(true)
                                .color(uxSettings.ordinalColors)
                                .groupSpacing(0.5);

                            chart.xAxis
                                .tickPadding(25)
                                .tickFormat(function (d) {
                                    return getJourneyStageName(d);
                                });

                            chart.yAxis
                                .tickPadding(10)
                                .tickFormat(d3.format('s'));

                            d3.selectAll(domID + '> *').remove();

                            d3.select(svgDOM)
                                .datum(scope.formattedData)
                                .transition().duration(600)
                                .call(chart)
                                .each('end', chartDrawFinished);

                            nv.utils.windowResize(chart.update);
                            nv.utils.windowResize(chartDrawFinished);

                            return chart;
                        },
                        callback: function (chart) {
                            function selectStage(stageId) {
                                d3.selectAll('g.nv-x.nv-axis .tick.zero')
                                    .classed('selected', function(d) { return d == stageId; });
                            }

                            chart.multibar.dispatch.on("elementClick", function(point) {
                                selectStage(point.data.x);
                            });

                            chart.legend.updateState(false);    // Disable legend click interaction

                            d3.selectAll('g.nv-x.nv-axis .tick.zero')
                                .on('click', function(x) {
                                    if (this.classList.contains('selected')) {
                                        selectStage(null);
                                    } else {
                                        selectStage(x);
                                    }
                                });

                            chart.tooltip.contentGenerator(function(point) {
                                var stageName = getJourneyStageName(point.data.x);
                                var status = point.data.key.toLowerCase() || '';
                                var steps = scope.extraInfo.funnel_steps || [];
                                var index = steps.indexOf(point.data.x);
                                var nps = scope.originalData[index]['nps'][status];
                                var count = scope.originalData[index]['count'][status];
                                var color = point.color;

                                stageName += ' (' + status + ')';

                                var template = [
                                    '<table>',
                                        '<thead>',
                                            '<tr>',
                                                '<td class="legend-color-guide">',
                                                    '<div style="background-color:' + color + '"></div>',
                                                '</td>',
                                                '<td>',
                                                    '<strong class="x-value">' + stageName + '</strong>',
                                                '</td>',
                                            '</tr>',
                                        '</thead>',
                                        '<tbody>',
                                            '<tr>',
                                                '<td class="key">Count</td>',
                                                '<td class="value">' + count + '</td>',
                                            '</tr>',
                                            '<tr>',
                                                '<td class="key">Average Bottom-up Score</td>',
                                                '<td class="value">' + d3.format(',.2f')(nps) + '</td>',
                                            '</tr>',
                                        '</tbody>' +
                                    '</table>'
                                ].join('');
                                return template;
                            });
                        }
                    });
                }

                var container = angular.element(element)[0];
                var svgDOM = angular.element(element).children('svg')[0];

                var debouncedRender = _.debounce(drawFunnelChart, 500);
                $(container.parentElement).resize(debouncedRender);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    scope.originalData = scope.chartData.original;
                    scope.formattedData = scope.chartData.formatted;
                    debouncedRender();
                });
            }
        }
    }

    function topicsCloud(Topics) {
        function fetch(scope, params) {
            var limit = params.plot_type ? 15 : null;
            return Topics.fetch(params, limit).then(function(d) {
                scope.topics = _.defaults(d, {active : ''});
                scope.count_max = _.max(scope.topics, function(topic) { return topic.term_count} )['term_count'];
                scope.count_min = _.min(scope.topics, function(topic) { return topic.term_count} )['term_count'];
            });
        }

        return {
            restrict: 'E',
            replace: false,
            scope : {
                settings : '='
            },
            template: '<div class="tagcloud maincloud widget-tagcloud"><ul><li ng-repeat="item in topics | orderBy:\'topic\':reverse"  ng-style="getTopicSize(item.term_count)[\'log\']"><span ng-bind="item.topic"></span></li></ul></div>',
            link: function (scope) {
                scope.getTopicSize = function(count) {
                    var fontMin = 12,
                        fontMax = 40;
                    var size = count == scope.count_min ? fontMin
                        : (Math.log(count) / Math.log(scope.count_max)) * (fontMax - fontMin) + fontMin;
                    var styles = {log : { 'font-size' : size + 'px'}};
                    return styles;
                };
                scope.$watch('settings', function(nVal) {
                    if (nVal && nVal.topics_params) {
                        fetch(scope, nVal.topics_params);
                    }
                });
            }
        };
    }

    /** New Charts */
    function stackedBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var keyDriversBarChart = dc.barChart(dom);

                    var driversDim = ndx.dimension(function (d) {return d.key_driver});

                    var npsByKeyDrivers = driversDim.group().reduce(
                      function(p, d) {
                          p.nps_total++;
                          p.nps_types[d.nps_type]['count']++;
                          p.nps_types[d.nps_type]['percentage'] = (p.nps_types[d.nps_type]['count']/p.nps_total)*100;
                          return p;
                      },
                      function (p, d) {
                          p.nps_total--;
                          p.nps_types[d.nps_type]['count']--;
                          p.nps_types[d.nps_type]['percentage'] = (p.nps_types[d.nps_type]['count']/p.nps_total)*100;
                          return p;
                      },
                      //init
                      function () {
                          return {
                              nps_total: 0,
                              nps_types: {
                                  Passive   : {count : 0, percentage : 0},
                                  Detractor : {count : 0, percentage : 0},
                                  Promoter  : {count : 0, percentage : 0}
                              }
                          };
                      }
                    );

                    keyDriversBarChart
                      .width(Math.floor(resolution.width))
                      .height(Math.floor(resolution.height))
                      .x(d3.scale.ordinal())
                      .xUnits(dc.units.ordinal)
                      .margins({left: 50, top: 10, right: 10, bottom: 150})
                      .brushOn(false)
                      .clipPadding(10)
                      .gap(5)
                      .yAxisLabel("NPS Distribution")
                      .round(dc.round.floor)
                      .y(d3.scale.linear().domain([0, 100]))
                      .group(npsByKeyDrivers, "Passive")
                      .dimension(driversDim)
                      .stack(npsByKeyDrivers, "Detractor", function(d){
                          var npsObj = d.value.nps_types['Detractor'];
                          return npsObj.count / d.value.nps_total * 100;
                      })
                      .stack(npsByKeyDrivers, "Promoter", function(d){
                          var npsObj = d.value.nps_types['Promoter'];
                          return npsObj.count / d.value.nps_total * 100;
                      })
                      .valueAccessor(function (d) {
                          var npsObj = d.value.nps_types['Passive'];
                          return npsObj.count / d.value.nps_total * 100;
                      })
                      //.legend(dc.legend().x(Math.floor(resolution.width) - 75).y(10))
                      .elasticY(false)
                      .ordinalColors(uxSettings.threeColors)
                      .on('renderlet', function(chart){

                        /*
                         Place the count labels on stacked bars
                         */
                        //Check if labels exist
                        var gLabels = chart.select(".labels");
                        if (gLabels.empty()){
                            gLabels = chart.select(".chart-body").append('g').classed('labels', true);
                        }

                        var gLabelsData = gLabels.selectAll("text").data(chart.selectAll(".bar")[0]);

                        gLabelsData.exit().remove(); //Remove unused elements

                        gLabelsData.enter().append("text") //Add new elements

                        gLabelsData
                          .attr('text-anchor', 'middle')
                          .attr('fill', 'white')
                          .text(function(d){
                              var labelObj = d3.select(d).data()[0].data.value;
                              var layerKey = d3.select(d).data()[0].layer;
                              return labelObj.nps_types[layerKey].count;
                          })
                          .attr('x', function(d){
                              return +d.getAttribute('x') + (d.getAttribute('width')/2);
                          })
                          .attr('y', function(d){ return +d.getAttribute('y') + 15; })
                          .attr('style', function(d){
                              if (+d.getAttribute('height') < 18) return "display:none";
                          });


                          chart.selectAll("rect.bar").attr("fill", function (d) {


                              if (d.layer == "Passive") {
                                  return '#F8A740';
                              } else if (d.layer == "Detractor") {
                                  return '#EA4F6B';
                              } else {
                                  //Promoter
                                  return '#4AC764';
                              }
                          });

                        /*
                         rotate the x-ticks labels and style them accordingly
                         */
                        chart.selectAll("g.x text")
                          .style("text-anchor", "end")
                          .attr("dx", "-.8em")
                          .attr("dy", ".15em")
                          .attr("font-size", "12px")
                          .attr("transform", "rotate(-30)");
                    });

                    keyDriversBarChart.yAxis().tickFormat(function(v) { return v + "%"; });

                    keyDriversBarChart.render();
                }
            }
        }
    }

    function distribBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var npsDistributionBarChart = dc.barChart(dom);

                    var npsDim = ndx.dimension(function (d) {
                        return d.nps
                    });
                    var npsByCount = npsDim.group();

                    npsDistributionBarChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .margins({left: 50, top: 10, right: 10, bottom: 60})
                        //.x(d3.scale.linear().domain([0,10]))
                        .x(d3.scale.ordinal())
                        .xUnits(dc.units.ordinal)
                        //.centerBar(true)
                        .gap(10)
                        .yAxisLabel("NPS Score")
                        .group(npsByCount)
                        .dimension(npsDim)
                        .elasticY(true)
                        .on('renderlet', function (chart) {
                            chart.selectAll("rect.bar").attr("fill", function (d) {
                                var nps_score = parseInt(d.data.key);
                                if (nps_score >= 9) {
                                    return '#4AC764';
                                } else if (nps_score >= 7 && nps_score < 9) {
                                    return '#F8A740';
                                } else if (nps_score < 7) {
                                    return '#EA4F6B';
                                } else {
                                    return '#203B73';
                                }
                            });
                        });

                    npsDistributionBarChart.render();
                }
            }
        }

    }

    function horizontalBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var regionsRowChart = dc.rowChart(dom);

                    var regionsDim = ndx.dimension(function (d) {return d.region});
                    var npsByRegions = regionsDim.group().reduce(
                        function(p, d) {
                            p.nps_total++;
                            return p;
                        },
                        function (p, d) {
                            p.nps_total--;
                            return p;
                        },
                        //init
                        function () {
                            return {
                                nps_total: 0
                            };
                        }
                    );

                    regionsRowChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .margins({top: 20, left: 10, right: 10, bottom: 20})
                        .group(npsByRegions)
                        .dimension(regionsDim)
                        .valueAccessor(function (d) {
                            return d.value.nps_total
                        })
                        .ordinalColors(uxSettings.genesysColors)
                        .elasticX(true);

                    regionsRowChart.render();
                }
            }
        }
    }

    function pieChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(dom.parentElement).width()),
                        height: Math.abs($(dom.parentElement).height())
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(dom.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var npsPieChart = dc.pieChart(dom);

                    var npsTypeDim = ndx.dimension(function (d) {return d.nps_type});
                    var npsByType = npsTypeDim.group();

                    npsPieChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .dimension(npsTypeDim)
                        .group(npsByType)
                        .label(function(d) {
                            return d.key + ' ' + d.value;
                        })
                        .ordinalColors(uxSettings.threeColors)
                        .innerRadius(50);

                    var colorScale = d3.scale.ordinal().domain(["Detractor", "Passive", "Promoter"])
                      .range(["#EA4F6B", "#F8A740", "#4AC764"]);

                    npsPieChart.colors(function(d){
                        return colorScale(d);
                    });

                    npsPieChart.render();
                }
            }
        }
    }


    function dataTableChart(uxSettings) {
        return {
            restrict: 'AE',
            replace: false,
            scope: {
                chartData: '='
            },
            template: '',
            link: function (scope, element) {

                var dom = angular.element(element)[0];

                console.log("INIT DATA TABLE WIDGET!!!");

                scope.$watch('chartData', function (newData, oldData) {

                    if (!newData) return;
                    render(newData)
                });

                function render(ndx) {
                    var dataTable = dc.dataTable(dom);

                    var allDim    = ndx.dimension(function(d) {return d;});
                    dataTable
                      .dimension(allDim)
                      .group(function (d) { return 'dc.js insists on putting a row here so I remove it using JS'; })
                      .size(1000)
                      .columns([
                          function (d) { return d.user_name },
                          function (d) { return d.text },
                          function (d) { return d.nps_type + "-" +d.nps },
                          function (d) { return d.csat; },
                          function (d) { return d.department; },
                          function (d) { return d.region; },
                          function (d) { return d.key_driver; }
                      ])
                      .sortBy(dc.pluck('nps'))
                      .order(d3.descending)

                      .on('renderlet', function (table) {
                          // each time table is rendered remove nasty extra row dc.js insists on adding
                          table.select('tr.dc-table-group').remove();
                      });

                    dataTable.render();

                }
            }
        }
    }

    function trendBarChart(uxSettings) {
        return {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '='
            },
            template:
                '<div style="float:left;width:60px;height:48px;text-align:center;font-weight:bold;font-size:14px;border:1px solid gray;margin-bottom:10px;">' +
                    '<p style="margin-bottom:0">NPS</p>' +
                    '<span class="number-display"></span>' +
                '</div>' +
                '<svg style="width:100%;height:100%"></svg>',
            link: function (scope, element) {
                var avgDOM = angular.element(element).children('div')[0];
                var chartDOM = angular.element(element).children('svg')[0];
                var container = angular.element(element)[0];

                var debouncedRedraw = _.debounce(function() {
                    var resolution = {
                        width: Math.abs($(container.parentElement).width()),
                        height: Math.abs($(container.parentElement).height()) - 60
                    };
                    if (typeof scope.chartData !== 'undefined') {
                        render(resolution, scope.chartData);
                    }
                }, 300);

                $(container.parentElement).resize(debouncedRedraw);

                scope.$watch('chartData', function (newData, oldData) {
                    if (!newData) return;
                    debouncedRedraw();
                });

                function render(resolution, ndx) {
                    var npsAvgText = dc.numberDisplay(avgDOM);
                    var npsByTimeBarChart = dc.barChart(chartDOM);

                    var npsDim = ndx.dimension(function (d) {return d.nps});
                    var timeDim        = ndx.dimension(function (d) {return d.end});
                    var npsTotalByTime = timeDim.group().reduce(
                        function(p, d) { p.tot += d.nps; p.n++; return p; },
                        function(p, d) { p.tot -= d.nps; p.n--; return p; },
                        function() {return {tot: 0, n: 0}; }
                    );
                    var npsAverage = function(d) {
                        return (d.value.n)? Math.round((d.value.tot / d.value.n) * 10): 0;
                    };
                    var npsAverage1 = function(d) {
                        return (d.n)? Math.round((d.tot / d.n) * 10): 0;
                    };

                    var npsTotal = ndx.groupAll().reduce(
                        function(p, d) { p.tot += d.nps; p.n++; return p;},
                        function(p, d) { p.tot -= d.nps; p.n--; return p; },
                        function() {return {tot: 0, n: 0}; }
                    );

                    npsAvgText
                        .formatNumber(d3.format("02d"))
                        .group(npsTotal)
                        .valueAccessor(npsAverage1);
                    npsAvgText.render();

                    npsByTimeBarChart
                        .width(Math.floor(resolution.width))
                        .height(Math.floor(resolution.height))
                        .margins({left: 50, top: 10, right: 10, bottom: 60})
                        .x(d3.scale.ordinal())
                        .xUnits(dc.units.ordinal)
                        .gap(5)
                        .yAxisLabel("NPS Score")
                        .group(npsTotalByTime)
                        .dimension(npsDim)
                        .valueAccessor(npsAverage)
                        .elasticY(true)
                        .on('renderlet', function(chart) {
                            /**
                             * output values on each bar
                             */
                            var drawnBars = chart.selectAll(".bar")[0];
                            var gLabels = chart.select(".labels");
                            if (gLabels.empty()){
                                gLabels = chart.select(".chart-body").append('g').classed('labels', true);
                            }

                            var gLabelsData = gLabels.selectAll("text").data(drawnBars);
                            gLabelsData.exit().remove(); //Remove unused elements
                            gLabelsData.enter().append("text"); //Add new elements

                            gLabelsData
                                .attr('text-anchor', 'middle')
                                .attr('fill', function(d) {
                                    return (+d.getAttribute('width') < 15)? 'black': 'white';
                                })
                                .text(function(d){
                                    return npsAverage(d3.select(d).data()[0].data);
                                })
                                .attr('x', function(d){ return +d.getAttribute('x') + (d.getAttribute('width')/2); })
                                .attr('y', function(d){ return +d.getAttribute('y') + 15; })
                                .attr('style', function(d){
                                    if (+d.getAttribute('height') < 18) return "display:none";
                                });

                            /**
                             * draw regression line between the first and last bar
                             */
                            if (drawnBars.length > 1) {
                                var firstBar = drawnBars[0];
                                var lastBar = drawnBars[drawnBars.length - 1];
                                var lineData = [{
                                    x: +firstBar.getAttribute('x') + (firstBar.getAttribute('width') / 2),
                                    y: +firstBar.getAttribute('y')
                                }, {
                                    x: +lastBar.getAttribute('x') + (lastBar.getAttribute('width') / 2),
                                    y: +lastBar.getAttribute('y')
                                }];
                                var line = d3.svg.line()
                                    .x(function (d) {
                                        return d.x;
                                    })
                                    .y(function (d) {
                                        return d.y;
                                    })
                                    .interpolate('linear');
                                var path = chart.select('g.chart-body').selectAll('path.extra').data([lineData]);
                                path.enter().append('path').attr('class', 'extra').attr('stroke', '#ff9900').attr('stroke-width', "3");
                                path.attr('d', line);
                            }

                            /**
                             * rotate the x-ticks labels and style them accordingly
                             */
                            chart.selectAll("g.x text")
                                .style("text-anchor", "end")
                                .attr("dx", "-.8em")
                                .attr("dy", ".15em")
                                .attr("font-size", "12px")
                                .attr("transform", "rotate(-45)");
                        });


                    npsByTimeBarChart.render();
                }
            }
        }
    }



    function addWidget() {
        return {
            restrict: 'E',
            template: '<span class="fonticon icon-add add-widget" ng-click="add()"></span>',
            link: function(scope, element, attrs) {
                $(element).parents('.widget-content').prev('.widget-title').find('.widget-title-text').remove();
                scope.add = function() {
                    scope.addNewWidget();
                }
            }
        }
    }
})();
