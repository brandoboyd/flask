(function () {
    'use strict';
    angular
        .module('dashboard')
        .directive('journeyVolumesByJourneyType', journeyVolumesByJourneyType)
        .directive('npsTrends', npsTrends)
        .directive('npsByJourneyType', npsByJourneyType)
        .directive('npsByJourneyTag', npsByJourneyTag)
        .directive('statusByJourneyType', statusByJourneyType);

    /** Directives for Journey Dashboard Widgets */
    function journeyVolumesByJourneyType(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}"></svg>',
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);
            
            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'value');

                if (_.every(values, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.pieChart()
                        .duration(250)
                        .x(function(d) { return labels[d.key] || 'N/A' })
                        .y(function(d) { return d.value })
                        .color(uxSettings.ordinalColors)
                        .growOnHover(false)
                        .showLegend(true)
                        // .labelsOutside(true)
                        .labelType('value')
                        .noData('No Data Available')
                        .valueFormat(d3.format(',.0d'))

                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .call(chart);

                    return chart;
                }
                function callback(chart) {
                    chart.pie.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'journey_volumes_by_journey_type',
                            key: 'journey_type',
                            value: point.data.key
                        };
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // Apply grey color based on crossfilter selection
                    if (! (scope.crossFilter && scope.crossFilter.journey_type)) { return }

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var filter = scope.crossFilter.journey_type;

                    d3.selectAll(svgId + '.nv-slice')
                        .classed('deselected clickable', function(d) {
                            return ( filter.length && (filter.indexOf(d.data.key) < 0) );
                        })
                        .classed('selected', function(d) {
                            return ( filter.length && (filter.indexOf(d.data.key) >= 0) );
                        });
                }
            }
        }
    }

    function npsTrends(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                crossFilter: '=',
            },
            template: [
                '<div class="nps-trends-box">',
                    '<p style="margin-bottom:0">NPS</p>',
                    '<span class="number-display"></span>',
                '</div>',
                '<svg id="w_{{widgetId}}" style="width:calc(100% - 50px)"></svg>'].join(''),
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var avgDOM = angular.element(element).children('div')[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var container = angular.element(element)[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var width = $(container.parentElement).width();
                var height = $(container.parentElement).height();
                var data = scope.chartData.data;
                var granularity = scope.chartData.granularity;
                var values = _.pluck(data, 'values');

                if (_.every(values, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.linePlusBarChart()
                        .duration(0)
                        .x(function(d) { return d[0] })
                        .y(function(d) { return d[1] })
                        .width(width)
                        .height(height)
                        .margin({right: 100})
                        .color(['#1F77B4', '#F8A740'])
                        .showLegend(false)
                        .noData('No Data Available')
                        .focusHeight(60);

                    chart.xAxis.tickFormat(function(d) {
                        return formatLabel(d, granularity);
                    });
                    // Focus View Finder
                    chart.x2Axis.tickFormat((function(d) {
                        return d3.time.format('%x')(new Date(d));
                    }));
                    chart.bars.forceY([0]).padData(false);
                    chart.y1Axis.tickFormat(d3.format('d'));

                    d3.select(avgDOM).selectAll('text').remove();
                    d3.select(svgDOM).selectAll('*').remove();

                    d3.select(svgDOM)
                        .datum(data)
                        .call(chart);

                    return chart;
                }

                function formatLabel(d, level) {
                    if (level == 'week') {
                        return 'Week ' + d3.time.format('%U')(new Date(d));
                    } else {
                        return d3.time.format('%x')(new Date(d));
                    }
                }

                function callback(chart) {
                    var svgId = '#w_' + scope.widgetId + ' ';
                    var drawnBars = d3.selectAll(svgId + '.nv-bar')[0];
                    if (!drawnBars.length) return;

                    var values = data[0].values;

                    // Show view finder with full range by default
                    var len = values.length;
                    var start = values[0][0];
                    var end = values[len - 1][0];
                    chart.brushExtent([start, end]).update();

                    var debouncedBrushUpdate = _.debounce(brushUpdate, 500);
                    function brushUpdate(data) {
                        var newFilter = {
                            source: 'nps_trends',
                            key: 'date_subrange',
                            value: {
                                from: moment.utc(parseInt(data.extent[0])).format('YYYY-MM-DD HH:mm:ss'),
                                to: moment.utc(parseInt(data.extent[1])).format('YYYY-MM-DD HH:mm:ss'),
                                fromDate: moment.utc(parseInt(data.extent[0])).format('MMM DD, YYYY'),
                                toDate: moment.utc(parseInt(data.extent[1])).format('MMM DD, YYYY'),
                            }
                        };

                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    }
                    chart.dispatch.on('brush', debouncedBrushUpdate);

                    // Draw average nps value
                    var total = _.reduce(values, function(total, n) {
                        return total + n[1];
                    }, 0);
                    d3.select(avgDOM)
                        .append('text')
                        .attr('text-anchor', 'middle')
                        .attr('class', 'need-to-refresh')
                        .text(parseInt(total / values.length, 10));
                }
            }
        }
    }

    function npsByJourneyTag(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                widgetId: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}"></svg>',
            link: linkFn
        };
        return directive;
        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var width = $(container.parentElement).width();
                var height = $(container.parentElement).height();
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'value');

                if (_.every(values, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.multiBarChart()
                        .color(uxSettings.fourColors)
                        .duration(0)
                        .yDomain([0, 100])
                        .showControls(false)
                        .width(width)
                        .height(height + 30)
                        .stacked(true)
                        .rotateLabels(-15)
                        .reduceXTicks(true)
                        .noData('No Data Available')
                        .groupSpacing(0.5);

                    chart.showXAxis(false);
                    chart.xAxis
                        .tickFormat(function (d) {
                            return labels[d];
                        });
                    chart.yAxis
                        .tickPadding(10)
                        .tickFormat(function (d) {
                            return d3.format('p')(d / 100);
                        });
                    chart.tooltip.enabled(true);
                    chart.tooltip.valueFormatter(function (d) { return '' +d3.format(',.2f')(d) + '%'; })
                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .transition().duration(0)
                        .call(chart)
                        .each('end', drawFinished);

                    return chart;
                }
                function drawFinished() {
                    drawValueOnStackedBarChart(scope.widgetId, true);
                }
                function callback(chart) {
                    clearTooltip();
                    chart.multibar.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'nps_by_journey_tag',
                            key: 'journey_tags',
                            value: point.data.x
                        }
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // Apply grey color based on crossfilter selection
                    if ( !(scope.crossFilter && scope.crossFilter.journey_tags) ) { return }

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var filter = scope.crossFilter.journey_tags;

                    d3.selectAll(svgId + '.nv-bar')
                        .classed('deselected clickable', function(d) {
                            return ( filter.length && (filter.indexOf(d.x) < 0) );
                        });
                }
            }
        }
    }

    function npsByJourneyType(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                chartData: '=',
                widgetId: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}" class="stacked-bar-chart clickable-x-axis"></svg>',
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render() {
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'values');
                var npsValues = _.pluck(_.flatten(values), 'y');

                if (_.every(npsValues, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.multiBarChart()
                        .color(uxSettings.fourColors)
                        .duration(0)
                        .yDomain([0, 100])
                        .y(function(d) { return d.y })
                        .showControls(false)
                        // .showLegend(false)
                        .stacked(true)
                        .noData('No Data Available')
                        .groupSpacing(0.4);

                    chart.xAxis
                        .tickPadding(25)
                        .tickFormat(function (d) {
                            return labels[d];
                        });
                    chart.yAxis
                        .tickPadding(10)
                        .tickFormat(function (d) {
                            return d3.format('p')(d / 100);
                        });
                    chart.tooltip.enabled(false);
                    // chart.tooltip.valueFormatter(function (d) { return '' +d3.format(',.2f')(d) + '%'; })
                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .transition().duration(0)
                        .call(chart)
                        .each('end', drawFinished);

                    return chart;
                }
                function drawFinished() {
                    drawValueOnStackedBarChart(scope.widgetId);

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var xAxisTicks = d3.selectAll(svgId + '.nv-x .tick.zero text')[0];
                    drawRectOnXAxisTicks(xAxisTicks);
                }
                function callback(chart) {
                    chart.multibar.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'nps_by_journey_type',
                            key: 'nps',
                            value: point.data.key
                        };
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // X-Axis click handler
                    var svgId = '#w_' + scope.widgetId + ' ';
                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .on('click', function(jtId) {
                            var newFilter = {
                                source: 'journey_volumes_by_journey_type',
                                key: 'journey_type',
                                value: jtId
                            };
                            scope.$emit('CROSSFILTER_CHANGED', newFilter);
                        });

                    // Apply grey color based on crossfilter selection
                    if (!scope.crossFilter) { return }
                    var filter = scope.crossFilter;

                    d3.selectAll(svgId + '.nv-bar')
                        .classed('deselected', function(d) {
                            return (
                                (filter.journey_type.length && filter.journey_type.indexOf(d.x) < 0) ||
                                (filter.nps.length && filter.nps.indexOf(d.key) < 0)
                            );
                        });
                    d3.selectAll(svgId + '.nv-bar')
                        .classed('clickable', function(d) {
                            return filter.journey_type.length && (filter.journey_type.indexOf(d.x) >= 0);
                        });

                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .classed('selected', function(jtId) {
                            return (filter.journey_type.length && filter.journey_type.indexOf(jtId) >= 0);
                        })
                }
            }
        }
    }

    function statusByJourneyType(uxSettings) {
        var directive = {
            restrict: 'E',
            replace: false,
            scope: {
                widgetId: '=',
                chartData: '=',
                crossFilter: '=',
            },
            template: '<svg id="w_{{widgetId}}" class="stacked-bar-chart clickable-x-axis"></svg>',
            link: linkFn
        };
        return directive;

        function linkFn(scope, element) {
            var container = angular.element(element)[0];
            var svgDOM = angular.element(element).children('svg')[0];
            var debouncedRender = _.debounce(render, 300);

            $(container).parent().resize(debouncedRender);

            scope.$watch('chartData', function (newData, oldData) {
                if (!newData) { return }
                debouncedRender();
            }, true);

            function render(resolution, data) {
                var data = scope.chartData.data;
                var labels = scope.chartData.labels || {};
                var values = _.pluck(data, 'values');
                var npsValues = _.pluck(_.flatten(values), 'y');

                if (_.every(npsValues, function(v) { return v == 0; })) {
                    data = [];
                }

                nv.addGraph({
                    generate: drawGraph,
                    callback: callback
                });

                function drawGraph() {
                    var chart = nv.models.multiBarChart()
                        .color(uxSettings.threeColors)
                        .duration(0)
                        .y(function(d) { return d3.round(d.y, 2) })
                        .yDomain([0, 100])
                        .showControls(false)
                        // .showLegend(false)
                        .noData('No Data Available')
                        .stacked(true)
                        .groupSpacing(0.4);

                    chart.xAxis
                        .tickPadding(25)
                        .tickFormat(function (d) {
                            return labels[d] || 'N/A';
                        });
                    chart.yAxis
                        .tickPadding(10)
                        .tickFormat(function (d) {
                            return d3.format('p')(d / 100);
                        });
                    chart.tooltip.enabled(false);
                    chart.legend.updateState(false);

                    d3.select(svgDOM)
                        .datum(data)
                        .transition().duration(0)
                        .call(chart)
                        .each('end', drawFinished);

                    return chart;
                }
                function drawFinished() {
                    drawValueOnStackedBarChart(scope.widgetId);

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var xAxisTicks = d3.selectAll(svgId + '.nv-x .tick.zero text')[0];
                    drawRectOnXAxisTicks(xAxisTicks);
                }
                function callback(chart) {
                    chart.multibar.dispatch.on('elementClick', function(point) {
                        var newFilter = {
                            source: 'status_by_journey_type',
                            key: 'status',
                            value: point.data.key
                        }
                        scope.$emit('CROSSFILTER_CHANGED', newFilter);
                    });

                    // X-Axis click handler
                    var svgId = '#w_' + scope.widgetId + ' ';
                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .on('click', function(jtId) {
                            var newFilter = {
                                source: 'journey_volumes_by_journey_type',
                                key: 'journey_type',
                                value: jtId
                            };
                            scope.$emit('CROSSFILTER_CHANGED', newFilter);
                        });

                    // Apply grey color based on crossfilter selection
                    if (! (scope.crossFilter)) { return }

                    var svgId = '#w_' + scope.widgetId + ' ';
                    var filter = scope.crossFilter;

                    d3.selectAll(svgId + '.nv-bar')
                        .classed('deselected', function(d) {
                            return (
                                (filter.journey_type.length && filter.journey_type.indexOf(d.x) < 0) ||
                                (filter.status.length && filter.status.indexOf(d.key) < 0)
                            );
                        });
                    d3.selectAll(svgId + '.nv-bar')
                        .classed('clickable', function(d) {
                            return filter.journey_type.length && (filter.journey_type.indexOf(d.x) >= 0);
                        });

                    d3.selectAll(svgId + 'g.nv-x.nv-axis .tick.zero')
                        .classed('selected', function(jtId) {
                            return (filter.journey_type.length && filter.journey_type.indexOf(jtId) >= 0);
                        })    
                }
            }
        }
    }

    function drawValueOnStackedBarChart(widgetId, showCount) {
        var svgId = '#w_' + widgetId + ' ';
        d3.select(svgId + 'g.labels').remove();
        var allBars = d3.selectAll(svgId + '.nv-bar')[0];
        var gValues = d3.select(svgId + '.nv-wrap g').append('g').classed('labels', true);

        _.each(allBars, function(bar) {
            var w = +bar.getAttribute('width');
            var h = +bar.getAttribute('height');
            var x = +bar.getAttribute('x');
            var y = +bar.getAttribute('y');
            var value = (!showCount)
                ? d3.format('.1f')(bar.__data__.y) + '%'
                : d3.format(',')(bar.__data__.count);

            if (h < 20 || value == 0) return;
            gValues.append('text')
                .attr('text-anchor', 'middle')
                .attr('x', x + w/2)
                .attr('y', y + h/2 + 5)
                // .attr('series', bar.__data__.series)
                // .attr('stage', bar.__data__.x)
                .attr('transform', bar.getAttribute('transform'))
                .text(value)
        });
    }

    function drawRectOnXAxisTicks(xAxisTicks) {
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
                .attr('x', x - 15)
                .attr('y', y - (25 - h) / 2)
                .attr('rx', 4)
                .attr('ry', 4)
                .attr('width', w + 30)
                .attr('height', 25);
        });
    }

    function clearTooltip() {
        d3.selectAll('.nvtooltip').remove();
    }

})();