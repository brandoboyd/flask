(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('AgentsService', AgentsService);

  /** @ngInject */
  function AgentsService($rootScope, $resource, ChannelsService) {
    var agents = [],
      all_agents_selected = true;
    var AgentsService = $resource('/configure/agents/json', {}, {
      fetch: {method: 'GET', isArray: false}
    });

    AgentsService.ON_AGENTS_LOADED = 'on_agents_load';
    AgentsService.ON_AGENTS_CHANGED = 'on_agents_change';

    AgentsService.colors = ['#159d00', '#8eb000',
      '#bfb800', '#bf9200',
      '#bf6c00', '#0a67cf',
      '#0acbcf', '#23d30a',
      '#bfeb0c', '#fff70d',
      '#ffc60d', '#ff960d',
      '#ff5d0d', '#f70c1a',
      '#d60b99', '#7c0acf',
      '#180acf', '#006699',
      '#009999', '#009900',
      '#99cc00', '#cccc00',
      '#cc9900', '#cc6600',
      '#cc3300', '#cc0000',
      '#990066', '#660099',
      '#000099'];

    AgentsService.fetchAgents = function () {
      AgentsService.fetch({channel_id: ChannelsService.getSelectedId()}, function (res) {
        //return all elements set to default value - enabled:true
        //we need colors be assigned and preserved for each agent
        agents = _.map(res.list, function (el, index) {
          var label = el.display_name;
          if (label.indexOf('@') != -1) {
            label = label.substr(0, label.indexOf('@'));
          }
          var i = index == AgentsService.colors.length ? 0 : index;
          return _.defaults(el, {label: label, enabled: false, color: AgentsService.colors[i]})
        });
        $rootScope.$broadcast(AgentsService.ON_AGENTS_LOADED);
      });
    };

    AgentsService.setIsAllSelected = function (all) {
      all_agents_selected = all;
    };
    AgentsService.isAllSelected = function () {
      return all_agents_selected;
    };

    AgentsService.setChangedByIds = function (ids) {
      var changed = _.map(agents, function (el) {
        if (_.indexOf(ids, el.agent_id) != -1) {
          el.enabled = true
        }
        return el
      });
      AgentsService.setChanged(changed);
    };

    AgentsService.setChanged = function (selected) {
      agents = selected;
      $rootScope.$broadcast(AgentsService.ON_AGENTS_CHANGED);
    };
    AgentsService.getAll = function () {
      return agents;
    };
    AgentsService.setAll = function (all) {
      if (all) {
        _.each(agents, function (el) {
          el.enabled = true
        });
      } else {
        _.each(agents, function (el, idx) {
          el.enabled = false
        });
      }
      $rootScope.$broadcast(AgentsService.ON_AGENTS_ALL_CHANGED); // TODO:?
    };

    AgentsService.removeAgent = function (id) {
      var removed = _.find(AgentsService.getAll(), function (el) {
        return el.agent_id === id
      });
      if (removed)
        removed.enabled = false;
      $rootScope.$broadcast(AgentsService.ON_AGENTS_CHANGED);
    };

    AgentsService.getSelected = function () {
      var selected = _.filter(agents, function (el) {
        return el.enabled == true
      });
      return _.pluck(selected, 'agent_id');
    };

    AgentsService.getSelectedTags = function () {
      return _.filter(agents, function (el) {
        return el.enabled == true
      });
    };

    AgentsService.getParams = function () {
      // we return empty list for all agents
      // because there may be some agents that were deleted
      // they are not shown in selection, but posts from them need to be queried
      if (AgentsService.isAllSelected()) {
        return [];
      } else {
        return AgentsService.getSelected();
      }
    };

    AgentsService.getAgentId = function (name) {
      var agent = _.find(agents, function (el) {
        return el.display_name == name
      });
      if (agent != undefined) {
        return agent.agent_id;
      } else {
        return null;
      }

    };

    AgentsService.getLabel = function (agentId) {
      var agent = _.find(AgentsService.getAll(), function (a) {
        return a.agent_id === agentId;
      });
      return agent && agent.label || '';
    };

    AgentsService.setAgents = function (names) {
      _.each(agents, function (agent) {
        agent.enabled = names.indexOf(agent.display_name) > -1;
      });
    };

    return AgentsService;

  }
})();