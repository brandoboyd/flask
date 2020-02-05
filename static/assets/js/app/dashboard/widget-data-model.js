(function () {
    'use strict';

    angular.module('dashboard')

        .factory('SeriesDataModel', function ($http, WidgetDataModel, FilterService, WidgetDataParser) {
            function SeriesDataModel() { }

            SeriesDataModel.prototype = Object.create(WidgetDataModel.prototype);

            SeriesDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);

                //var params = this.dataModelOptions ? this.dataModelOptions.params : {};
                var wAttrs = this.widgetScope.widget.attrs;
                var range_alias = wAttrs.extra_settings.range_alias;
                var params    = _.extend({}, wAttrs.settings);
                var date_range  = FilterService.getDateRangeByAlias(range_alias);

                var old_from = wAttrs.settings.from;
                var old_to   = wAttrs.settings.to;

                //amend settings
                params.from = date_range ? date_range.from.toString("MM/dd/yyyy") : old_from;
                params.to   = date_range ? date_range.to.toString("MM/dd/yyyy")   : old_to;

                $http.post(wAttrs.extra_settings.request_url, params).success(function(d) {
                    var chart = {settings  : wAttrs.settings, widget_id : wAttrs.id, extra_settings : wAttrs.extra_settings };
                    // d.data for new journey endoints
                    chart.data = WidgetDataParser.parse(d.list || d.data, wAttrs.extra_settings);
                    WidgetDataModel.prototype.updateScope.call(chartModel, chart);
                    callback();
                }.bind(chartModel))
            };

            return SeriesDataModel;
        })

        .factory('TopicsDataModel', function ($http, WidgetDataModel, WidgetDataParser, FilterService, Topics) {
            function TopicsDataModel() {
            }

            TopicsDataModel.prototype = Object.create(WidgetDataModel.prototype);

            TopicsDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);
                var wAttrs = this.widgetScope.widget.attrs;
                WidgetDataModel.prototype.updateScope.call(chartModel, {extra_settings: wAttrs.extra_settings});
                callback();
            };

            return TopicsDataModel;
        })

        .factory('DashboardStorage', function($http, $q, FilterService, WidgetDataParser) {
            var dashboardList = [];
            var dashboards = {};

            function updateList(inputDashboards) {
                dashboardList = [];
                dashboardList = inputDashboards;
            }

            function getDashboardsList() {
                return dashboardList;
            }

            function updateDashboard(dashboard) {
                var dashToUpdate = _.find(dashboardList, {'id': dashboard.id});
                if (dashToUpdate) {
                    fetchData(dashToUpdate);
                }
            }

            function addDashboard(dashboard) {
                dashboardList.push(dashboard);
            }

            function removeDashboard(dashboardId) {
                _.remove(dashboardList, {'id': dashboardId});
            }

            function fetchData(dashboard) {
                var dId = dashboard.id;
                if (!(dashboards[dId] && dashboards[dId].beingFetched == false)) return;

                var currentDashboard = dashboards[dId];
                var params = getBaseFilter(dId);
                var url = '';

                var onSuccess = {
                    dataFetched : function (response, widgetType, widgets, postParams) {
                        currentDashboard.allData[widgetType] = WidgetDataParser.parseJourneyDashboardData(response.data[widgetType], widgetType);
                        if (widgets.length) {
                            _.each(widgets, function(widget) {
                                if (widget.callback) {
                                    widget.callback.call(null, currentDashboard.allData, widget.id, crossFilter);
                                }
                            });
                        }
                        if (_.has(response.data, 'is_up_to_date') && response.data.is_up_to_date === false) {
                            postParams['force_recompute'] = true;
                            return $http.post(url, postParams).then(
                              function(resp) {
                                  onSuccess.dataFetched(resp.data, widgetType, widgets, postParams)
                              }
                            );
                        }
                    }
                };

                if (dashboard.dashboardType == 'nps') {
                    url = '/nps/json';
                    currentDashboard.beingFetched = true;
                    delete params.range_alias;

                    $http
                        .post(url, params)
                        .success(function (resp) {
                            currentDashboard.beingFetched = false;
                            var departments = ['Customer Care', 'Services', 'Marketing', 'Sales', 'IT', 'Quality Assurance', 'Licenses', 'Operational'],
                                regions = ['APAC', 'EMEA', 'North America'],
                                drivers = ['Product & Quality', 'Value/ROI', 'Implementation', 'Communication', 'Support', 'Services', 'Price', 'Relationship', 'Contract Negotiation'];

                            var getFakeDimensions = function (dm) {
                                return dm[_.random(0, dm.length - 1)]
                            };
                            var fullDateFormat = d3.time.format("%m/%d/%Y");
                            var journeyData = _.map(resp.list, function (item) {
                                return {
                                    'user_name' : item.user_name,
                                    'text' : item.text,
                                    'csat': item.csat,
                                    'nps': item.nps,
                                    'nps_type': item.response_type == 'Default' ? 'Detractor' : item.response_type,
                                    'effort': item.total_effort,
                                    'end': fullDateFormat(new Date(item.created * 1000)),
                                    'department': getFakeDimensions(departments),
                                    'region': getFakeDimensions(regions),
                                    'key_driver': item.key_drivers
                                }
                            });

                            // Keep crossfilter instance global in dashboards
                            currentDashboard.allData = crossfilter(journeyData);

                            _.each(currentDashboard.widgets, function(widget, type) {
                                widget.callback.call(null, currentDashboard.allData);
                            });
                        });

                } else if (dashboard.dashboardType == 'journeys') {
                    var widgetTypes = _.uniq(['journey_volumes_by_journey_type'].concat(_.map(currentDashboard.widgets, 'type')));
                    var crossFilter = getCrossFilter(dashboard.id);

                    url = '/crossfilter/json';
                    currentDashboard.beingFetched = true;

                    if (params['journey_type'] === null) {
                        params['journey_type'] = [];
                    } else {
                        params['journey_type'] = [params['journey_type']]; //Make it array
                    }

                    var promises = _.map(widgetTypes, function(widgetType) {

                        var widgets = _.filter(currentDashboard.widgets, { 'type': widgetType });

                        if (currentDashboard.refreshStates[widgetType]) {
                            var postParams = getFullFilter(dId);
                            postParams['widgets'] = [widgetType];
                            return $http.post(url, postParams)
                                .then(
                                  function(response) {
                                      onSuccess.dataFetched(response.data, widgetType, widgets, postParams);
                                  }, function(error) {
                                      console.log(error);
                                  }
                                );

                        } else {
                            // Do not update 'NPS Trends' widget if it's crossfiltered itself
                            if (widgetType !== 'nps_trends') {
                                _.each(widgets, function(widget) {
                                    if (widget.callback) {
                                        widget.callback.call(null, currentDashboard.allData, widget.id, crossFilter);
                                    }
                                });
                            }
                            return $q.when();
                        }

                    });

                    $q.all(promises).then(function() {
                        currentDashboard.beingFetched = false;
                    });

                }
            };

            function registerWidget(info, cb) {
                var dId = info.dashboardId;
                var wId = info.widgetId;
                if (!_.has(dashboards, dId)) {
                    dashboards[dId] = {
                        allData : {},
                        widgets : [],
                        refreshStates: {},
                        beingFetched: false
                    };
                }

                dashboards[dId].refreshStates[info.widgetType] = true;

                var widget = _.find(dashboards[dId].widgets, { id: wId });
                if (widget) {
                    widget.callback = cb;
                } else {
                    dashboards[dId].widgets.push({
                        id: wId,
                        type: info.widgetType,
                        callback: cb
                    });
                }
            }

            function setCrossFilter(dashboardId, newFilter) {

                if ( !_.has(dashboards[dashboardId], 'crossFilter') ) {
                    dashboards[dashboardId]['crossFilter'] = {
                        journey_type: [ ],
                        journey_tags: [ ],
                        status: [ ],
                        date_subrange: { },
                        nps: [ ],
                    };
                }

                var currentFilter = dashboards[dashboardId].crossFilter;
                var currentItem = currentFilter[newFilter.key];
                var refreshStates = dashboards[dashboardId].refreshStates;

                // Set whether or not to fetch data again for widgets
                _.each(refreshStates, function(bool, widgetType, states) {
                    states[widgetType] = true;
                });
                if (newFilter.key == 'journey_type') {
                    refreshStates['journey_volumes_by_journey_type'] = false;
                    refreshStates['nps_by_journey_type'] = false;
                    refreshStates['status_by_journey_type'] = false;
                }
                // DO NOT REFRESH ITSELF
                refreshStates[newFilter.source] = false;

                if (newFilter.key == 'date_subrange') {
                    angular.copy(newFilter.value, currentItem);
                } else {
                    var pos = currentItem.indexOf(newFilter.value);
                    if (pos > -1) {
                        currentItem.splice(pos, 1);
                    } else {
                        currentItem.push(newFilter.value);
                    }
                }

                var dashboard = _.find(dashboardList, { id: dashboardId });
                fetchData(dashboard);
            }

            function resetCrossFilter(dashboardId, refreshWidgets) {
                if (_.has(dashboards[dashboardId], 'crossFilter')) {
                    dashboards[dashboardId]['crossFilter'] = {
                        journey_type: [],
                        journey_tags: [],
                        status: [],
                        date_subrange: { },
                        nps: [],
                    };
                }
                if (_.has(dashboards[dashboardId], 'refreshStates')) {
                    _.each(dashboards[dashboardId].refreshStates, function(val, key, states) {
                        states[key] = true;
                    });
                }

                var dashboard = _.find(dashboardList, { id: dashboardId });
                if (refreshWidgets && dashboard) {
                    fetchData(dashboard);
                }
            }

            function removeCrossFilter(dashboardId, item) {
                var currentFilter = dashboards[dashboardId].crossFilter;
                var currentItem = currentFilter[item.key];

                if (item.key == 'date_subrange') {
                    angular.copy({ }, currentItem);
                } else {
                    var pos = currentItem.indexOf(item.value);
                    if (pos > -1) {
                        currentItem.splice(pos, 1);
                    }
                }

                var dashboard = _.find(dashboardList, { id: dashboardId });
                fetchData(dashboard);
            }

            function getCrossFilter(dashboardId) {
                if (dashboards[dashboardId]) {
                    return dashboards[dashboardId].crossFilter;
                } else {
                    return null;
                }
            }

            function getBaseFilter(dashboardId) {
                var dashboard = _.find(dashboardList, { id: dashboardId });
                if (dashboard) {
                    var params = {};
                    var filters = dashboard.filters || null;
                    if (filters) {
                        if (filters.facets) {
                            params = angular.copy(filters.facets);
                        }
                        if (filters.period) {
                            var dateRange = FilterService.getDateRangeByAlias(filters.period.alias);
                            params.range_alias = filters.period.alias;
                            params.from = dateFormat(dateRange.from, "yyyy-mm-dd HH:MM:ss", true);
                            params.to = dateFormat(dateRange.to, "yyyy-mm-dd HH:MM:ss", true);
                        }
                    }
                    return params;
                }
                return null;
            }

            function getFullFilter(dashboardId) {
                var baseParams = getBaseFilter(dashboardId);
                var fullParams;
                if (_.has(dashboards[dashboardId], 'crossFilter')) {
                    var crossFilter = dashboards[dashboardId].crossFilter;
                    fullParams = angular.extend({}, baseParams);

                    _.each(crossFilter, function(values, key) {
                        if (key !== 'date_subrange') {
                            if (!_.has(fullParams, key) || !values.length) {
                                return;
                            }
                        } else {
                            if (!_.isEmpty(values)) {
                                fullParams['subrange_from'] = values.from;
                                fullParams['subrange_to'] = values.to;
                            }
                            return;
                        }
                        if (!!fullParams[key].length) {
                            fullParams[key] = _.intersection(fullParams[key], values);
                        } else {
                            fullParams[key] = values;
                        }
                    });
                    return fullParams;
                } else {
                    return baseParams;
                }
            }

            return {
                updateList: updateList,
                update: updateDashboard,
                add: addDashboard,
                remove: removeDashboard,
                registerWidget: registerWidget,
                getStoredData : function(id) { return data[id]},
                getDashboardsList: getDashboardsList,
                setCrossFilter: setCrossFilter,
                getCrossFilter: getCrossFilter,
                resetCrossFilter: resetCrossFilter,
                removeCrossFilter: removeCrossFilter,
                getBaseFilterParams: getBaseFilter,
                getFullFilterParams: getFullFilter
            };
        })

        .factory('NPSDataModel', function (WidgetDataModel, FilterService, DashboardStorage) {
            function NPSDataModel() {}

            NPSDataModel.prototype = Object.create(WidgetDataModel.prototype);

            NPSDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);

                var wAttrs = this.widgetScope.widget.attrs;
                var info = {
                    dashboardId : wAttrs.dashboard_id,
                    widgetId    : wAttrs.id,
                    directive   : ''
                };

                DashboardStorage.registerWidget(info, function(data) {
                    var chart = {
                        settings    : wAttrs.settings,
                        widget_id   : wAttrs.id,
                        data        : data
                    };
                    WidgetDataModel.prototype.updateScope.call(chartModel, chart);
                    callback();
                });
            };

            return NPSDataModel;
        })

        .factory('JourneyDataModel', function (WidgetDataModel, FilterService, DashboardStorage) {
            function JourneyDataModel() {}

            JourneyDataModel.prototype = Object.create(WidgetDataModel.prototype);

            JourneyDataModel.prototype.init = function (callback) {
                var chartModel = this;
                WidgetDataModel.prototype.init.call(this);

                var wAttrs = this.widgetScope.widget.attrs;
                var directive = (wAttrs.settings.directive)? wAttrs.settings.directive.replace(/-/g, '_'): '';
                var info = {
                    dashboardId : wAttrs.dashboard_id,
                    widgetId    : wAttrs.id,
                    widgetType  : directive
               };

                DashboardStorage.registerWidget(info, function(data, widgetId, crossFilter) {

                    if (wAttrs.id !== widgetId) return;

                    var chart = {
                        settings    : wAttrs.settings,
                        widget_id   : wAttrs.id,
                        data        : data[directive],
                        crossFilter : crossFilter
                    };
                    chart.data.now = new Date().getTime();

                    WidgetDataModel.prototype.updateScope.call(chartModel, chart);
                    callback();
                });
            };

            return JourneyDataModel;
        })

}());