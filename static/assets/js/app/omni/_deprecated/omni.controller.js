function OmniCtrl($scope, $rootScope, $http, $location,
                       FilterService, OmniChannel, CallIntent, Segment, Industry, PlotTypes
                       ) {
    $scope.table = {
        sort: {
            predicate: '',
            reverse: false
        }
    };

    $scope.FilterService = FilterService;
    $scope.facets = {
        age_groups          : { visible : false, all : true },
        customer_statuses   : { visible : false, all : true },
        agent_occupancy     : { visible : false, all : true },
        // list is dynamically populated
        call_intents        : { visible : false, all : true, list : [] },
        segments            : { visible : false, all : true, list : [] },
        channels            : { visible : false, all : true, list : [] },
        industries          : { visible : false, all : true, list : [] },
        journey_types       : { visible : false, all : true, list : [] },
        journey_statuses    : { visible : false, all : true, list : [] }
    };

    $scope.section = {
        _distribution : 'distribution',
        _details      : 'details',

        init : function () {
            // switch to default tab
            this.switchTab(this._distribution);
        },


        isDistribution : function () {
            return this.tab == this._distribution;
        },
        isDetails : function () {
            return this.tab == this._details;
        },

        switchTab : function (tab) {
            console.log("SWITCH TAB", tab);
            this.tab = tab;
            if (tab == this._distribution) {
                $scope.buildPlot();
            }
            else if (tab == this._trends) {
                $scope.buildPlot();
            }
            else if (tab == this._details) {
                $scope.searchDetails();
            }

        }
    };


    var formatDate  = function(date) {
        return dateFormat(date, "yyyy-mm-dd HH:MM:ss", true)
    };

    $scope.$on(FilterService.DATE_RANGE_CHANGED, function() {
        $scope.currentDate = FilterService.getSelectedDateRangeName();
        console.log("DATE CHANGED!", $scope.currentDate);
        var selectedPeriod = FilterService.getDateRangeObj();

        $scope.from = formatDate(selectedPeriod.from);
        $scope.to   = formatDate(selectedPeriod.to);
        updateFacets();
    });



    $scope.toggleFacet = function(facetName) {
        var facet = $scope.facets[facetName];
        facet.visible = !facet.visible;
    };

    $scope.dateRange = FilterService.getDateRange();
    $scope.currentDate = FilterService.getSelectedDateRangeName();

    var getCustomerSearchParams = function (item) {
        var group_by    = PlotTypes.getActiveFilter();
        var plot_by     = PlotTypes.getActiveType();

        var segments    = item && group_by == 'segment'
                            ? [item.series.label] : getSegmentsParams();
        var industries  = item && group_by == 'industry'
                            ? [item.series.label] : getIndustriesParams();
        var locations   = item && group_by == 'location'
                            ? [item.series.label] : null;
        var genders     = item && group_by == 'gender'
                            ? [item.series.label] : null;

        var customer_statuses   = item && group_by == 'Status'
                                    ? [item.series.label] : FilterService.getCustomerStatusesParams();

        var params = {
            agent_id            : OMNI_ID,
            segments            : segments,
            age_groups          : FilterService.getAgeGroupsParams(),
            industries          : industries,
            locations           : locations,
            genders             : genders,
            customer_statuses   : customer_statuses,
            call_intents        : getCallIntentsParams()

        };
        return params;
    };

    var getAgentSearchParams = function (item) {
        var group_by = PlotTypes.getActiveFilter();
        var params = {
            customer_id         : OMNI_ID,
            //from                : $scope.dateRange.from,
            //to                  : $scope.dateRange.to,
            segments            : getSegmentsParams(),
            age_groups          : FilterService.getAgeGroupsParams(),
            industries          : getIndustriesParams(),

            agent_occupancy     : FilterService.getAgentOccupancyParams(),
            locations           : item && group_by == 'location' ? [item.series.label] : null,
            genders             : item && group_by == 'gender' ? [item.series.label] : null
        };
        return params;
    };

    $scope.searchDetails = _.debounce(function () {
        if (OMNI_SECTION == 'customers') {
            OmniChannel.searchCustomers(getCustomerSearchParams());
        }
        else if (OMNI_SECTION == 'agents') {
            OmniChannel.searchAgents(getAgentSearchParams());
        }

    }, 500);


    $scope.buildPlot = _.debounce(function () {


        var params, resource;
        if (OMNI_SECTION == 'customers') {
            params = getCustomerSearchParams();
            resource = OmniChannel.Customer;
        }
        else if (OMNI_SECTION == 'agents') {
            params = getAgentSearchParams();
            resource = OmniChannel.Agent;
        }



        if(OMNI_SECTION !== 'journeys') {
            params['plot_by'] = 'distribution';
            params['group_by'] = PlotTypes.getActiveFilter();

            var plot_type = PlotTypes.getActiveType();

            resource.fetch({}, params, function (res) {
                $scope.buildPlotByType(res.list, plot_type);
            }, function onError() {
                //use it empty data for now
                $scope.buildPlotByType([], type);
            });
        }

    }, 500);


    // FACET FILTERS
    $scope.is_facet_disabled = false;
    $rootScope.$on('onJsonBeingFetched', function() {
        $scope.is_facet_disabled = true;
    });
    $rootScope.$on('onJsonFetched', function() {
        $scope.is_facet_disabled = false;
    });

    var updateFacets = function () {
        $scope.buildPlot();
        $scope.searchDetails();
    };

    /********* AGE_GROUPS *********/
    $scope.age_groups_filter = FilterService.getAgeGroups();

    $scope.$watch('facets.age_groups.all', function (newVal) {
        FilterService.setIsAllAgeGroups(newVal);
        if (newVal) {
            FilterService.setAgeGroups([]);
        }
    });

    $scope.$on(FilterService.AGE_GROUPS_CHANGED, function () {
        var selected = FilterService.getSelectedAgeGroups();
        $scope.selectedAgeGroups = selected;

        if (selected.length > 0 ) {
            FilterService.setIsAllAgeGroups(false);
            $scope.facets.age_groups.all = false;
        } else {
            FilterService.setIsAllAgeGroups(true);
            $scope.facets.age_groups.all = true;
        }
        updateFacets();
    });
    /********* END OF AGE_GROUPS *********/


    /********* CUSTOMER_STATUSES *********/
    $scope.customer_statuses_filter = FilterService.getCustomerStatuses();

    $scope.$watch('facets.customer_statuses.all', function (newVal) {
        FilterService.setIsAllCustomerStatuses(newVal);
        if (newVal) {
            FilterService.setCustomerStatuses([]);
        }
    });

    $scope.$on(FilterService.CUSTOMER_STATUSES_CHANGED, function () {
        var selected = FilterService.getSelectedCustomerStatuses();
        $scope.selectedCustomerStatuses = selected;

        if (selected.length > 0 ) {
            FilterService.setIsAllCustomerStatuses(false);
            $scope.facets.customer_statuses.all = false;
        } else {
            FilterService.setIsAllCustomerStatuses(true);
            $scope.facets.customer_statuses.all = true;
        }
        updateFacets();
    });
    /********* END OF CUSTOMER_STATUSES *********/

    /********* AGENT_OCCUPANCY *********/
    $scope.agent_occupancy_filter = FilterService.getAgentOccupancy();

    $scope.$watch('facets.agent_occupancy.all', function (newVal) {
        FilterService.setIsAllAgentOccupancy(newVal);
        if (newVal) {
            FilterService.setAgentOccupancy([]);
        }
    });

    $scope.$on(FilterService.AGENT_OCCUPANCY_CHANGED, function () {
        var selected = FilterService.getSelectedAgentOccupancy();
        $scope.selectedAgentOccupancy = selected;

        if (selected.length > 0 ) {
            FilterService.setIsAllAgentOccupancy(false);
            $scope.facets.agent_occupancy.all = false;
        } else {
            FilterService.setIsAllAgentOccupancy(true);
            $scope.facets.agent_occupancy.all = true;
        }
        updateFacets();
    });
    /********* END OF AGENT_OCCUPANCY *********/

    /********* CALL_INTENTS *********/
    var getCallIntentsParams = function () {
        var params = $scope.facets.call_intents.list;
        if (!$scope.facets.call_intents.all) {
            params = _.filter(params, function (ci) {
                return ci.enabled;
            });
        }
        return _.pluck(params, 'display_name');
    };

    var loadCallIntents = function () {
        CallIntent.get({}, function (res) {
            var items = res.list;
            $scope.facets.call_intents.list.length = 0;
            Array.prototype.push.apply($scope.facets.call_intents.list, items);
        }, function (err) {
            console.log(err);
        });
    };
    loadCallIntents();

    $scope.$watch('facets.call_intents.all', function (newVal) {
        if (newVal) {
            $scope.selectedCallIntents = [];
            _.each($scope.facets.call_intents.list, function (ci) {
                ci.enabled = false;
            });
            updateFacets();
        }
    });

    var setSelectedCallIntents = function () {
        $scope.selectedCallIntents = _.pluck(
            _.filter($scope.facets.call_intents.list, function (ci) {
                return ci.enabled;
            }), 'display_name'
        );
    };

    $scope.updateCallIntents = function () {
        var selected = getCallIntentsParams();

        if (selected.length > 0 ) {
            setSelectedCallIntents();
            $scope.facets.call_intents.all = false;
        } else {
            $scope.facets.call_intents.all = true;
        }
        updateFacets();
    };

    $scope.removeCallIntent = function (ci_name) {
        _.each($scope.facets.call_intents.list, function (ci) {
            if (ci.display_name == ci_name) {
                ci.enabled = false;
            }
        });
        $scope.updateCallIntents();
    };
    /********* END OF CALL_INTENTS *********/

    /********* SEGMENTS *********/
    var getSegmentsParams = function () {
        var params = $scope.facets.segments.list;
        if (!$scope.facets.segments.all) {
            params = _.filter(params, function (ci) {
                return ci.enabled;
            });
        }
        return _.pluck(params, 'display_name');
    };

    var loadSegments = function () {
        var items = [
            {display_name : 'NEW SEGMENT'},
            {display_name : 'NORMAL SEGMENT'},
            {display_name : 'VIP SEGMENT'}
        ];
        Array.prototype.push.apply($scope.facets.segments.list, items);

    };
    loadSegments();

    $scope.$watch('facets.segments.all', function (newVal) {
        if (newVal) {
            $scope.selectedSegments = [];
            _.each($scope.facets.segments.list, function (ci) {
                ci.enabled = false;
            });
            updateFacets();
        }
    });

    var setSelectedSegments = function () {
        $scope.selectedSegments = _.pluck(
            _.filter($scope.facets.segments.list, function (ci) {
                return ci.enabled;
            }), 'display_name'
        );
    };

    $scope.updateSegments = function () {
        var selected = getSegmentsParams();

        if (selected.length > 0 ) {
            setSelectedSegments();
            $scope.facets.segments.all = false;
        } else {
            $scope.facets.segments.all = true;
        }
        updateFacets();
    };

    $scope.removeSegment = function (ci_name) {
        _.each($scope.facets.segments.list, function (ci) {
            if (ci.display_name == ci_name) {
                ci.enabled = false;
            }
        });
        $scope.updateSegments();
    };
    /********* END OF SEGMENTS *********/

    /********* INDUSTRIES *********/
    var getIndustriesParams = function () {
        var params = $scope.facets.industries.list;
        if (!$scope.facets.industries.all) {
            params = _.filter(params, function (ci) {
                return ci.enabled;
            });
        }
        return _.pluck(params, 'display_name').map(function (name) {
            return name === 'Unknown' ? null : name;
        });
    };

    var loadIndustries = function () {
        Industry.get({}, function (res) {
            var items = res.list;
            $scope.facets.industries.list.length = 0;
            _.each(items, function (item) {
                $scope.facets.industries.list.push({
                    'display_name': item || 'Unknown',
                    'enabled': false,
                });
            });
        }, function (err) {
            console.log(err);
        });
    };
    loadIndustries();

    $scope.$watch('facets.industries.all', function (newVal) {
        if (newVal) {
            $scope.selectedIndustries = [];
            _.each($scope.facets.industries.list, function (ci) {
                ci.enabled = false;
            });
            updateFacets();
        }
    });

    var setSelectedIndustries = function () {
        $scope.selectedIndustries = _.pluck(
            _.filter($scope.facets.industries.list, function (ci) {
                return ci.enabled;
            }), 'display_name'
        );
    };

    $scope.updateIndustries = function () {
        var selected = getIndustriesParams();

        if (selected.length > 0 ) {
            setSelectedIndustries();
            $scope.facets.industries.all = false;
        } else {
            $scope.facets.industries.all = true;
        }
        updateFacets();
    };

    $scope.removeIndustry = function (ci_name) {
        _.each($scope.facets.industries.list, function (ci) {
            if (ci.display_name == ci_name) {
                ci.enabled = false;
            }
        });
        $scope.updateIndustries();
    };
    /********* END OF INDUSTRIES *********/





    /********* JOURNEY STATUSES *********/
    var getJourneyStatusesParams = function () {
        var params = $scope.facets.journey_statuses.list;
        if (!$scope.facets.journey_statuses.all) {
            params = _.filter(params, function (ci) {
                return ci.enabled;
            });
        }
        return _.pluck(params, 'display_name');
    };

    var loadJourneyStatuses = function () {
        var items = [
            {display_name : 'finished'},
            {display_name : 'abandoned'},
            {display_name : 'ongoing'}
        ];
        Array.prototype.push.apply($scope.facets.journey_statuses.list, items);

    };
    loadJourneyStatuses();

    $scope.$watch('facets.journey_statuses.all', function (newVal) {
        if (newVal) {
            $scope.selectedJourneyStatuses = [];
            _.each($scope.facets.journey_statuses.list, function (ci) {
                ci.enabled = false;
            });
            updateFacets();
        }
    });

    var setSelectedJourneyStatuses = function () {
        $scope.selectedJourneyStatuses = _.pluck(
          _.filter($scope.facets.journey_statuses.list, function (ci) {
              return ci.enabled;
          }), 'display_name'
        );
    };

    $scope.updateJourneyStatuses = function () {
        var selected = getJourneyStatusesParams();

        if (selected.length > 0 ) {
            setSelectedJourneyStatuses();
            $scope.facets.journey_statuses.all = false;
        } else {
            $scope.facets.journey_statuses.all = true;
        }
        updateFacets();
    };

    $scope.removeJourneyStatus = function (ci_name) {
        _.each($scope.facets.journey_statuses.list, function (ci) {
            if (ci.display_name == ci_name) {
                ci.enabled = false;
            }
        });
        $scope.updateJourneyStatuses();
    };
    /********* END OF JOURNEY STATUSES *********/







    /********* JOURNEY_TYPES *********/
    var loadJourneysTypes = function () {
        $http.get("/journey_types").success(function (res) {
            var items = res.data;
            console.log("JOURNEY TYPES", res);
            $scope.facets.journey_types.list.length = 0;
            Array.prototype.push.apply($scope.facets.journey_types.list, items);
        })
          .error(function (err) {
            console.log(err);
        });
    };
    loadJourneysTypes();

    $scope.getJourneyType = function(type_id) {
        if($scope.facets.journey_types.list.length > 0) {
            var j = _.find($scope.facets.journey_types.list, function(item) {return item.id == type_id});

            return j.display_name;
        } else {
            return "N/A";
        }
    }


    $scope.facets.journey_types.selected = null;

    $scope.$watch('facets.journey_types.selected', function (newVal) {
        if (newVal) {
            $scope.facets.journey_types.all = false;
            updateFacets();
        }
    });

    $scope.$watch('facets.journey_types.all', function (newVal) {
        if (newVal) {
            $scope.facets.journey_types.selected = null;
            updateFacets();
        }
    });




    $scope.updateJourneyTypes = function (item) {
        console.log(item);
        //$scope.facets.journey_types.selected = item
        updateFacets();
    };



    /********* END OF JOURNEY_TYPES *********/




    $scope.resetAll = function () {
        $scope.facets.age_groups.all = true;
        $scope.facets.customer_statuses.all = true;
        $scope.facets.agent_occupancy.all = true;
        $scope.facets.call_intents.all = true;
        $scope.facets.segments.all = true;
        $scope.facets.industries.all = true;
    };

    // global listeners

    $scope.$on(OmniChannel.ON_CUSTOMERS_FETCHED, function (tab) {
        $scope.customers = OmniChannel.getCustomers();
    });

    $scope.$on(OmniChannel.ON_AGENTS_FETCHED, function (tab) {
        $scope.agents = OmniChannel.getAgents();
    });

    $scope.section.init();

    $scope.getPlotterURL = function () {
        return "/partials/plot/share_plot";
    };



    $scope.buildPlotByType = function (plot_data) {
        $scope.data = plot_data;
    };

    $scope.searchByGraph = function (item) {
        if (OMNI_SECTION == 'customers') {
            OmniChannel.searchCustomers(getCustomerSearchParams(item));
        } else if (OMNI_SECTION == 'agents') {
            OmniChannel.searchAgents(getAgentSearchParams(item));
        }
        $scope.section.tab = $scope.section._details;
    }

    // minimum PlotTypes configurations
    PlotTypes.setPage(OMNI_SECTION);
    PlotTypes.setType('share');

    if (OMNI_SECTION == 'customers') {
        PlotTypes.setFilter('segment');
    }
    else if (OMNI_SECTION == 'agents') {
        PlotTypes.setFilter('location');
    }


    $scope.data = [];
    $scope.isPlotByVisible = true;
    $scope.plot_filters = PlotTypes.getFilters();
    $scope.setFilter = PlotTypes.setFilter;
    $scope.getTrendParams = getCustomerSearchParams;



}