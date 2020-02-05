(function () {
    'use strict';

    angular.module('dashboard')
        .factory('FacetFactory', FacetFactory);

function FacetFactory($http, $q, FilterService) {
    var currentPage = '';
    var pages = ['nps', 'journeys', 'agents', 'customers'];
    var fetchDone = false;
    var facets = {
        channels            : {field: 'id',   pages: ['journeys', 'nps']},
        smart_tags          : {field: 'id',             pages: ['nps']},
        segments            : {field: 'display_name',   pages: ['journeys', 'agents', 'customers']},
        journey_types       : {field: 'id',             pages: ['journeys']},
        journey_stages      : {field: 'display_name',   pages: ['journeys']},
        journey_tags        : {field: 'id',             pages: ['journeys']},
        journey_statuses    : {field: 'display_name',   pages: ['journeys']},
        age_groups          : {field: 'display_name',   pages: ['agents', 'customers']},
        industries          : {field: 'display_name',   pages: ['agents', 'customers']},
        customer_statuses   : {field: 'display_name',   pages: ['customers']},
        nps                 : {field: 'value',          pages: ['journeys']}
        //call_intents        : {id: 'intent',        pages: ['customers']}
    };
    var optionsLoaded = false;

    var mappings = {        // Mapping for dashboard attributes and post params
        'nps': {
            'channels': '',
            'smart_tags': ''
        },
        'journeys': {
            'channels'          : '',
            'smart_tags'        : '',
            'segments'          : 'customer_segments',
            'nps'               : '',
            'journey_tags'      : '',
            'journey_types'     : 'journey_type',
            'journey_stages'    : 'stage',
            'journey_statuses'  : 'status'
        },
        'agents': {
            'segments'  : '',
            'industries': '',
            'age_groups': ''
        },
        'customers': {
            'segments': '',
            'industries': '',
            'age_groups': '',
            'customer_statuses': ''
        }
    };

    var reset = function() {
        _.each(facets, function(facet, key) {
            facets[key].visible = facets[key].pages.indexOf(currentPage) > -1;
            //facets[key].all = true;
            facets[key].list = [];
        });
    };

    var fetchChannels = function() {
        if (facets.channels.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.post('/channels_by_type/json', {type: 'inbound', serviced_only : false, parent_names  : true})
            .success(function(resp) {
                var list = resp.list;
                if (currentPage == 'nps') {
                    list = _.filter(list, {'platform': 'VOC'});
                }
                facets.channels.list = _.map(list, function(item) {
                    return {id: item.id, display_name: item.title, enabled: false};
                });
            });
    };

    var fetchSmartTags = function() {
        if (facets.smart_tags.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/smart_tags/json')
            .success(function(resp) {
                facets.smart_tags.list = _.map(resp.list, function(item) {
                    return {id: item.id, display_name: item.title, enabled: false};
                });
            });
    };

    var fetchJourneyTypes = function() {
        if (facets.journey_types.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/journey_types')
            .success(function(resp) {
                facets.journey_types.list = _.map(resp.data, function(item) {
                    return {id: item.id, display_name: item.display_name, enabled: false};
                });
            });
    };

    var fetchJourneyStages = function(journeyTypeId) {
        if (facets.journey_stages.pages.indexOf(currentPage) == -1 ) return $q.when();
        if(!journeyTypeId) return $q.when();
        return $http.get('/journey_types/{jid}/stages'.replace('{jid}', journeyTypeId))
            .success(function(resp) {
                facets.journey_stages.list.length = 0;
                facets.journey_stages.list = _.map(resp.data, function(item) {
                    return {id: item.id, display_name: item.display_name, enabled: false};
                });
            });
    };

    var fetchJourneyTags = function(journeyTypeId) {
        if (facets.journey_tags.pages.indexOf(currentPage) == -1 ) return $q.when();
        var url = '/journey_tags';
        if (journeyTypeId) url += '?journey_type_id=' + journeyTypeId;
        return $http.get(url)
            .success(function(resp) {
                facets.journey_tags.list.length = 0;
                facets.journey_tags.list = _.map(resp.data, function(item) {
                    return {
                        id : item.id,
                        display_name : item.display_name,
                        enabled : false,
                        jtId : item.journey_type_id
                    };
                });
            });
    };

    var fetchSegments = function() {
        if (facets.segments.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/customer_segments')
            .success(function(resp) {
                var items = resp.list;
                facets.segments.list.length = 0;
                facets.segments.list.push({
                    display_name: 'N/A'
                });
                facets.segments.list = _.map(resp.list, function(item) {
                    return {'display_name': item.display_name, enabled: false};
                });
            });
    };

    var fetchIndustries = function() {
        if (facets.industries.pages.indexOf(currentPage) == -1 ) return $q.when();
        return $http.get('/customer_industries/json')
            .success(function(resp) {
                facets.industries.list.length = 0;
                _.each(resp.list, function(item) {
                    if (item) facets.industries.list.push({'display_name': item, enabled: false});
                });
            });
    };

    var fetchJourneyStatus = function() {
        if (facets.journey_statuses.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.journey_statuses.list = FilterService.getJourneyStatus();
        return $q.when();
    };

    var fetchNPS = function() {
        if (facets.nps.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.nps.list = FilterService.getNPSOptions();
        return $q.when();
    };

    var fetchAgeGroups = function() {
        if (facets.age_groups.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.age_groups.list = FilterService.getAgeGroups();
        return $q.when();
    };

    var fetchCustomerStatuses = function() {
        if (facets.customer_statuses.pages.indexOf(currentPage) == -1 ) return $q.when();
        facets.customer_statuses.list = FilterService.getCustomerStatuses();
        return $q.when();
    };

    var setJourneyType = function(journeyTypeId) {
        return $q.all([
            fetchJourneyTags(journeyTypeId),
            //fetchJourneyStages(journeyTypeId)
        ]).then(function() {
            facets.journey_tags.visible = (journeyTypeId != null || journeyTypeId != undefined);
            //facets.journey_stages.visible = (journeyTypeId != null || journeyTypeId != undefined);
        });
    };

    function fetchFacetOptions(filters) {
        fetchDone = false;
        reset();
        var deferred = $q.defer();

        $q.all([
            fetchChannels(),
            fetchSmartTags(),
            fetchJourneyTypes(),
            fetchJourneyStatus(),
            //fetchJourneyTags(),
            //fetchJourneyStages(),
            fetchIndustries(),
            fetchSegments(),
            fetchNPS(),
            fetchAgeGroups(),
            fetchCustomerStatuses()
        ])
        .then(function(resp) {
            //var facetsToLoad = {'journey_type': null};
            //if (filters.facets) {
            //    facetsToLoad = filters.facets;
            //    if (facetsToLoad.journey_type) {
            //        facets['journey_types'].selected = facetsToLoad.journey_type;
            //    }
            //}
            //$q.all([
            //    fetchJourneyTags(facetsToLoad.journey_type),
            //    fetchJourneyStages(facetsToLoad.journey_type)
            //]).then(function() {
                fetchDone = true;
                deferred.resolve(filters.facets);
            //})
        });

        return deferred.promise;
    }

    function getFacetParams() {
        var mapping = mappings[currentPage];
        var filters = {};
        if (mapping) {
            _.each(mapping, function(output, key) {
                if (output == '') output = key;
                if (key == 'journey_types') {
                    filters[output] = (facets.journey_types.selected)? [facets.journey_types.selected] : [];
                    return;
                }
                var field = facets[key]['field'];
                var params = _.pluck(_.filter(facets[key].list, {'enabled': true}), field);
                filters[output] = params.length? params: [];
            });
        }
        return filters;
    }

    function loadFacets(settings) {

        function load() {
            var mapping = mappings[currentPage];

            _.each(mapping, function(output, key) {
                if (output == '') output = key;
                var field = facets[key].field;
                if (output == 'journey_type') {
                    facets[key].all = true;
                    if (!settings.journey_type) {
                        facets[key].selected = null;
                    } else if (!angular.isArray(settings.journey_type)) {
                        facets[key].selected = settings.journey_type;
                    } else {
                        facets[key].selected = settings.journey_type[0];
                    }
                    return;
                }
                _.each(facets[key].list, function(option, index) {
                    _.each(settings[output], function(item) {
                        if (item == option[field]) {
                            facets[key].all = false;
                            facets[key]['list'][index].enabled = true;
                        }
                    });
                });
            });

            optionsLoaded = true;
            return $q.when();
        }

        if (!fetchDone) {
            fetchFacetOptions()
                .then(load);
        } else {
            load();
        }
    }

    return {
        getPage: function() {
            return currentPage;
        },
        fetchAndLoadFacets: function(page, filters) {
            var deferred = $q.defer();
            optionsLoaded = false;
            if (pages.indexOf(page) == -1) {

            } else {
                currentPage = page;
                fetchFacetOptions(filters)
                    .then(loadFacets)
                    .then(function() {
                        deferred.resolve();
                    });
            }
            return deferred.promise;
        },
        getFacets: function() {
            return facets;
        },
        isOptionsLoaded: function() {
            return optionsLoaded;
        },
        getFacetParams: getFacetParams,
        loadFacets: loadFacets,
        setJourneyType: setJourneyType
    }
}

}());