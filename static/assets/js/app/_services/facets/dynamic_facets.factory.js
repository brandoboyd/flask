(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('DynamicFacetsService', DynamicFacetsService);

  /**@ngInject */
  function DynamicFacetsService($http, $q) {

    var facets = {};

    var factory = {
      getFacetsBySection: getFacetsBySection,
      dynamic_facets: facets
    };

    return factory;
    /////////////////////////////////////

    /*
    /facet-filters/customer
    /facet-filters/agent
    /facet-filters/journey/<journey-type-name>
    */

    function getFacetsBySection(section, id, params) {

      if (typeof params === 'undefined') {
        params = {}
      }

      //for some entities we first need to pass type_id(name) to load facets
      var type_id = _.isUndefined(id) ? '' : '/' + id;

      var url = '/facet-filters/' + section + type_id;

      var promise = $http({
        method: 'GET',
        url: url,
        params: params
      }).then(processFacet);

      return promise;
      ///////////////

      function processFacet(res) {
        //if (!res.data) return;
        var dynamic = {
          facets: [],
          metrics: [{type: 'count', value: 'count', active: true, label: 'count'}],
          group_by : [],
          sankey_group_by : [{type: 'All', value: null, active: true}]
        };

        _.each(['filters', 'group_by', 'metrics'], function (key) {
          _.each(res.data[key], function (item) {
            if (key == 'filters') {
              if(item.values && item.values.length > 0) {
                dynamic.facets.push(
                  {
                    id: item.name,
                    all: true,
                    visible: false,
                    description: item.name + ":" + item.type + ":" + item.cardinality,
                    list: _.map(item.values, function (val) {
                      return {
                        display_name: val || 'N/A',
                        enabled: false
                      };
                    })
                  }
                );
              }

            } else if(key == 'metrics') {
              dynamic.metrics.push(
                {type: item, value: item, active: false, label: item}
              )
            } else if(key == 'group_by') {
              dynamic.group_by.push(
                {type: item, value: item, active: false}
              );
              dynamic.sankey_group_by.push(
                {type: item, value: item, active: false}
              )
            }
          });
        });

        dynamic.group_by.push({type: 'all', value: null, active: false});

        return(dynamic);
        //predictorFacets[res.data.id] = facet;
      }

    }





  }
})();