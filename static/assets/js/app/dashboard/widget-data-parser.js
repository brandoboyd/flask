(function () {
    'use strict';

    angular.module('dashboard')

        // Temporarily used factory to parse data so that they can be drawn properly on various types of charts
        // TODO: Backend changes needed to return data in a unified manner
        .factory('WidgetDataParser', function () {
            return {
                parse: parse,
                parseJourneyDashboardData: parseJourneyDashboardData
            };

            // --------------------------------------------------
            // Parse "Trends" data response for Interactions page
            //
            function parseInteractionTrendsData(response) {
                return _.map(response, function (item) {
                    // WORKAROUND to change 'actual' to 'replied'
                    return {
                        key: (item.label === 'actual')? 'replied': item.label,
                        values: item.data
                    };
                });
            }

            // --------------------------------------------------
            // Parse "Distribution" data response for Interactions page
            //
            function parseInteractionDistData(response) {
                return _.map(response, function(item) {
                    // WORKAROUND to change 'actual' to 'replied'
                    return {
                        label: (item.label === 'actual')? 'replied': item.label,
                        value: item.data[0][1]
                    };
                });
            }

            // -----------------------------------------
            // Parse "Trends" data response for journeys
            //
            function parseJourneyTrendsData(response) {
                var plot_d3_data = _.map(response, function (item) {
                    return {
                        key: item.label,
                        values: item.data
                    }
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
                        .sortBy(function(n) { return n; })
                        .value();

                    _.each(plot_d3_data, function (series) {
                        var newValues = [];
                        _.each(timestamps, function (time) {
                            var newPoint = _.find(series.values, function(point) {
                                return point[0] == time;
                            });
                            if (!newPoint) newPoint = [time, 0];
                            newValues.push(newPoint);
                        });
                        series.values = newValues;
                    });
                }

                return plot_d3_data;
            }

            // ------------------------------------------
            // Parse "Metrics" data response for Advisors
            //
            function parsePredictorTrendsData(response) {
                return _.map(response, function (item) {
                    return {
                        key: item.label,
                        values: item.data
                    };
                });
            }

            // ----------------------------------------------------------
            // Parse "Distribution" data response for Agents and Customers
            //
            function parseDistributionData(response) {
                return _.map(response, function(item) {
                    return {
                        label: item.label,
                        data: [item.value],
                    };
                });
            }

            // ----------------------------------------------------------
            // Parse "Funnel" data response for journeys
            //
            function parseFunnelData(response, funnel_steps) {

                function isEmpty(data) {
                    return !(_.some(data, function(item) {
                        return item['count']['sum'] > 0;
                    }));
                }

                var statuses = ['converted', 'stuck', 'abandoned'];
                var rawData = response.data;
                var chartData = [];

                if (!isEmpty(rawData)) {
                    chartData = _.map(statuses, function (status) {
                        var obj = {
                            key: status,
                            values: []
                        };

                        obj.values = _.map(funnel_steps, function (step, index) {
                            return {x: step, y: rawData[index]['count'][status] || 0};
                        });
                        return obj;
                    });
                }

                return {
                    formatted: chartData,
                    original: rawData
                };
            }



            function parse(response, widgetInfo) {
                switch (widgetInfo.target) {
                    case 'JOURNEY-TREND':
                        return parseJourneyTrendsData(response);
                    case 'OMNI_AGENTS':
                    case 'OMNI_CUSTOMERS':
                        return parseDistributionData(response);
                    case 'PREDICTOR-TREND':
                        // Will be depreciated, 'chart' directive will also handle data parsing for dashboard widgets.
                        // target is 'PREDICTORS' now.
                        return parsePredictorTrendsData(response);
                    case 'INTERACTION-TREND':
                        return parseInteractionTrendsData(response);
                    case 'NORMAL-TREND':
                        return parsePredictorTrendsData(response);
                    case 'INTERACTION-DISTRIBUTION':
                        return parseInteractionDistData(response);
                    case 'NORMAL-DISTRIBUTION':
                        return parseDistributionData(response);
                    case 'JOURNEY-FUNNEL':
                        return parseFunnelData(response, widgetInfo.funnel_steps);
                    default:
                        return response;
                }
            }

            function parseJourneyDashboardData(response, widgetType) {

                var parsedData = {};

                if (widgetType == 'journey_volumes_by_journey_type') {
                    parsedData.labels = response.labels;
                    parsedData.data = _.map(response.data, function(value, key) {
                        return {
                            key: key,
                            value: value
                        }
                    });
                } else if (widgetType == 'status_by_journey_type') {
                    parsedData.labels = response.labels;
                    parsedData.legends = ['abandoned', 'ongoing', 'finished']; // Re-order for now
                    parsedData.data = _.map(response.data, function(obj, key) {
                        return {
                            key: key,
                            values: _.map(parsedData.legends, function(legend) { return obj[legend]; })
                        };
                    });
                    parsedData.data = normalizeStackedData(parsedData);
                } else if (widgetType == 'nps_by_journey_type') {
                    parsedData.labels = response.labels;
                    parsedData.legends = ['n/a', 'detractor', 'passive', 'promoter'];
                    parsedData.data = _.map(response.data, function(obj, key) {
                        return {
                            key: key,
                            values: _.map(parsedData.legends, function(legend) { return obj[legend]; })
                        };
                    });
                    parsedData.data = normalizeStackedData(parsedData);
                } else if (widgetType == 'nps_by_journey_tag') {
                    parsedData.labels = response.labels;
                    parsedData.legends = ['n/a', 'detractor', 'passive', 'promoter'];
                    parsedData.data = _.map(response.data, function(obj, key) {
                        return {
                            key: key,
                            values: _.map(parsedData.legends, function(legend) { return obj[legend]; })
                        };
                    });
                    parsedData.data = normalizeStackedData(parsedData);
                } else if (widgetType == 'nps_trends') {
                    parsedData.data = [{
                        bar: true,
                        values: [],
                    }];
                    parsedData.data[0].values = _.map(response.data, function(val, key) {
                        return [ 1000 * parseInt(key, 10), val];
                    });
                    parsedData.granularity = response.granularity;

                    // This is for yellow line in 'NPS Trends' widget
                    // parsedData.data = [{
                    //     bar: true,
                    //     values: [],
                    // }, {
                    //     key: '',
                    //     values: []
                    // }];
                    // parsedData.data[0].values = _.map(response.data, function(val, key) {
                    //     return [parseInt(key, 10), val];
                    // });
                    // parsedData.data[1].values = parsedData.data[0].values;
                }

                return parsedData;

                function normalizeStackedData(rawData) {
                    var temp = [];
                    var xAxisKeys = _.pluck(rawData.data, 'key');

                    // Normalize data -> convert to percentage
                    _.each(rawData.data, function(item) {
                        var values = item.values;
                        var total = _.reduce(values, function(total, n) { return total + n }, 0);
                        values = _.map(values, function(d) {
                            if (total <= 0) return 0;
                            return d / total * 100;
                        });
                        item.percents = values;
                    });

                    temp = _.map(rawData.legends, function(legend) {
                        var item = { key: legend };
                        var keyIndex = rawData.legends.indexOf(legend);
                        item.values = _.map(xAxisKeys, function(key) {
                            var d = _.find(rawData.data, {key: key});
                            return {
                                x: key,
                                y: (d)
                                    ? d.percents[keyIndex] || 0
                                    : 0,
                                count: (d)
                                    ? d.values[keyIndex] || 0
                                    : 0
                            };
                        });
                        return item;
                    });
                    return temp;
                }
            }

        })

}());