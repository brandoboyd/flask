(function () {
    'use strict';

    angular.module('omni.journeys')
        .controller('JourneysFunnelsCtrl', function ($scope, $http, JourneyTypesRest, JourneyFunnelsRest) {
            var JourneyTypes = new JourneyTypesRest();
            var JourneyFunnels = new JourneyFunnelsRest();

            var ordinalColors = ['#4AC764', '#F8A740', '#EA4F6B'];
            $scope.allFunnels = [];
            $scope.currentFunnelId = null;
            $scope.currentFunnel = null;
            $scope.currentBar = null;
            $scope.selectedStageId = null;
            $scope.loading = true;

            angular.element('#analysis').hide();

            $http
                .post('/select_strategy', {strategy: 'default'})
                .then(function() {
                    $scope.loading = false;
                    var fetchFunnels = JourneyFunnels.list();
                    return (fetchFunnels.then && fetchFunnels || fetchFunnels.$promise);
                })
                .then(function(res) {
                    $scope.allFunnels = res.data.data;
                    $scope.funnels = _.filter($scope.allFunnels, function (item) {
                        return item.journey_type == $scope.filters.journey_type.id
                    });
                    if ($scope.funnels.length) {
                        $scope.currentFunnelId = $scope.funnels[0].id;
                    }

                    JourneyTypes.list().success(function (jTypes) {
                        $scope.journeyStages = {};
                        _.each(jTypes.data, function (jt) {
                            JourneyTypes.getStages(jt.id)
                              .success(function (stages) {
                                $scope.journeyStages[jt.id] = stages.data;
                                $scope.funnelSelected();
                            });
                        });
                    });
                });

            $scope.toggleAnalyticsPanel = function(toShow) {
                var analysisPanel = angular.element('#analysis');
                if (toShow && analysisPanel.is(':hidden'))
                    analysisPanel.show('fast');
                else if (!toShow && analysisPanel.is(':visible'))
                    analysisPanel.hide('fast');
            };

            $scope.funnelSelected = function() {
                $scope.currentFunnel = _.find($scope.funnels, {'id': $scope.currentFunnelId});
                $scope.searchDetails($scope.getJourneySearchParams());
                $scope.emitFunnelStatus();
            };

            $scope.emitFunnelStatus = function() {
                if (!$scope.currentFunnel) return;
                var jtId = $scope.currentFunnel.journey_type;
                var stages = _.map($scope.journeyStages[jtId], _.partialRight(_.pick, ['id', 'display_name']));

                $scope.$emit('FUNNEL_SELECTED', {
                    funnel_id: $scope.currentFunnelId,
                    funnel_name: $scope.currentFunnel && $scope.currentFunnel.name,
                    journey_stages: stages,
                    funnel_steps: $scope.currentFunnel.steps,
                    stage_id: $scope.selectedStageId,
                    stage_name: $scope.getJourneyStageName($scope.currentFunnel.journey_type, $scope.selectedStageId)
                });
            };

            $scope.$on('FUNNEL_WIDGET_LOADED', function(evt, data) {
                $scope.currentFunnelId = data.funnel_id;
                $scope.funnelSelected();
            });

            $scope.getJourneyStageName = function(journeyTypeId, journeyStageId) {
                if ($scope.journeyStages && $scope.journeyStages[journeyTypeId]) {
                    var stage = _.find($scope.journeyStages[journeyTypeId], {'id': journeyStageId});
                    if (stage) return stage.display_name;
                }
                return 'N/A';
            };

            $scope.isLastStep = function(stepId) {
                if (!$scope.currentFunnel) return false;
                var temp = angular.copy($scope.currentFunnel.steps);
                return stepId == temp.pop();
            };

            $scope.searchDetails = _.debounce(function (params) {
                if (!$scope.currentFunnelId) {
                    return;
                }

                var postParams = angular.extend(params, {
                    funnel_id: $scope.currentFunnelId,
                    group_by: 'abandonment_rate',
                })
                postParams.from = moment(params.from).format('MM/DD/YYYY');
                postParams.to = moment(params.to).format('MM/DD/YYYY');

                function isEmpty(data) {
                    return !(_.some(data, function(item) {
                        return item['count']['sum'] > 0;
                    }));
                }

                $http.post("/funnel/facets", postParams)
                    .success(function(resp){
                        var statuses = ['converted', 'stuck', 'abandoned'];
                        var rawData = resp.list.data;
                        var chartData = [];

                        if (!isEmpty(rawData)) {
                            chartData = _.map(statuses, function (status) {
                                var obj = {
                                    key: status,
                                    values: []
                                };
                                var funnel = $scope.currentFunnel;

                                obj.values = _.map(funnel.steps, function (step, index) {
                                    return {x: step, y: rawData[index]['count'][status] || 0};
                                });
                                return obj;
                            });
                        }

                        $scope.chartData = chartData;

                        $scope.renderFunnels(chartData, rawData);
                    })
                    .error(function(err) {
                        console.log(err);
                    });

            }, 600);


            $scope.renderFunnels = function(chartData, originalData) {

                var chartDrawFinished = function() {
                    // Show count of journeys on each bar snippet
                    d3.select('g.labels').remove();
                    var allBars = d3.selectAll('.nv-bar')[0];
                    var gValues = d3.select('.nv-wrap g').append('g').classed('labels', true);

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
                    d3.select('g.arrows').remove();
                    var transBars = d3.selectAll('.nv-series-0 .nv-bar')[0];
                    var gArrows = d3.select('.nv-wrap g').append('g').classed('arrows', true);

                    _.each(transBars, function(bar) {
                        var barWidth = +bar.getAttribute('width');
                        var barHeight = +bar.getAttribute('height');
                        var x = barWidth * 2 - barWidth / 6;
                        var y = +bar.getAttribute('y') + barHeight / 2;
                        var w = barWidth * 2 / 3;
                        var h = 30;

                        var stageId = bar.__data__.x;
                        var steps = $scope.currentFunnel.steps;
                        var ind = steps.indexOf(stageId);
                        var percent = 0;
                        if ($scope.isLastStep(stageId) || !originalData[ind]) return;
                        var convertedCount = originalData[ind]['count']['converted'];
                        var totalCount = originalData[ind]['count']['sum'];
                        if (convertedCount > 0 && totalCount > 0) {
                            percent = convertedCount / totalCount;
                        }

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
                    d3.select('g.labels-total').remove();
                    var totalBars = d3.selectAll('.nv-series-2 .nv-bar')[0];
                    var gTotalValues = d3.select('.nv-wrap g').append('g').classed('labels-total', true);

                    _.each(totalBars, function(bar) {
                        var w = +bar.getAttribute('width');
                        var x = +bar.getAttribute('x');
                        var y = +bar.getAttribute('y');
                        if (!$scope.isLastStep(bar.__data__.x)) return;

                        gTotalValues.append('text')
                            .attr('text-anchor', 'middle')
                            .attr('fill', 'black')
                            .attr('x', x + w/2)
                            .attr('y', y - 10)
                            .attr('transform', bar.getAttribute('transform'))
                            .text('END')
                    });

                    // Remove bars with zero value which are drawn as simple line
                    d3.selectAll('.nv-bar')
                        .attr('style', function(d) {
                            if (d.y == 0) return 'display:none';
                        });


                    // Draw buttons for x-axis ticks (steps)
                    var xAxisTicks = d3.selectAll('.nv-x .tick.zero text')[0];

                    _.each(xAxisTicks, function(tick) {
                        var rect = tick.getBBox();
                        var tickContainer = tick.parentElement;
                        if (!rect || !tickContainer) return;
                        
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


                //////////////////////////////
                // Generate multi bar chart //
                nv.addGraph({
                    generate: function () {
                        var chart = nv.models.multiBarChart()
                            .color(ordinalColors)
                            .showControls(false)
                            .showLegend(true)
                            .stacked(true)
                            .groupSpacing(0.5);

                        chart.xAxis
                            .tickPadding(25)
                            .tickFormat(function (d) {
                                return $scope.getJourneyStageName($scope.currentFunnel.journey_type, d);
                            });
                        chart.yAxis
                            .tickPadding(10)
                            .tickFormat(d3.format('s'));

                        d3.selectAll('.funnel-chart svg > *').remove();

                        d3.select('.funnel-chart svg')
                            .datum(chartData)
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
                            $scope.selectedStageId = stageId;
                            $scope.toggleAnalyticsPanel($scope.selectedStageId !== null);
                            $scope.emitFunnelStatus();
                        }

                        chart.legend.updateState(false);    // Disable legend click interaction

                        chart.tooltip.chartContainer('.funnel-chart');
                        chart.tooltip.offset({left: 300, top: 230});    // DO NOT REMOVE!

                        chart.multibar.dispatch.on("elementClick", function(point) {
                            selectStage(point.data.x);
                        });

                        d3.selectAll('g.nv-x.nv-axis .tick.zero')
                            .on('click', function(x) {
                                if (this.classList.contains('selected')) {
                                    selectStage(null);
                                } else {
                                    selectStage(x);
                                }
                            });

                        chart.tooltip.contentGenerator(function(point) {
                            var stageName = $scope.getJourneyStageName($scope.currentFunnel.journey_type, point.data.x);
                            var status = point.data.key.toLowerCase() || '';
                            var steps = ($scope.currentFunnel)? $scope.currentFunnel.steps: [];
                            var index = steps.indexOf(point.data.x);
                            // var nps = originalData[index]['nps'][status];
                            var count = originalData[index]['count'][status];
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
                                        // '<tr>',
                                        //     '<td class="key">Average Bottom-up Score</td>',
                                        //     '<td class="value">' + d3.format(',.2f')(nps) + '</td>',
                                        // '</tr>',
                                    '</tbody>' +
                                '</table>'
                            ].join('');
                            return template;
                        });
                    }
                });
            };

            $scope.$on("ON_JOURNEY_TYPE_CHANGE", function () {
                $scope.funnels = _.filter($scope.allFunnels, 
                    { journey_type: $scope.filters.journey_type.id }
                );

                var isPresent = _.some($scope.funnels, { id: $scope.currentFunnelId });

                if ($scope.funnels && ! isPresent) {
                    $scope.currentFunnelId = $scope.funnels[0].id;
                    $scope.funnelSelected();
                }
            });

            $scope.$on("ON_JOURNEY_FACETS_UPDATE", function() {
                if ($scope.currentFunnel) $scope.searchDetails($scope.getJourneySearchParams());
            });
        });

}());
