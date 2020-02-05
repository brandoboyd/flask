'use strict';

var dependencies = [
    'chat.directives',
    'chat.services',
    'journey.services',
    'ui.router',
    'ui.bootstrap'
];

angular.module('journey', dependencies)
    .config(function ($stateProvider, $urlRouterProvider, $locationProvider) {

        $urlRouterProvider.otherwise('/journey/agents');
        $urlRouterProvider.when('/journey', '/journey/agents');
        //$locationProvider.hashPrefix('!');
        $locationProvider.html5Mode(true);

        $stateProvider
            .state('demo', {
                abstract: true,
                url: '/journey',
                template: '<ui-view/>'
            })
            .state('demo.agents', {
                url: '/agents',
                templateUrl: '/static/chat/public/templates/journey/agents/list.html',
                controller: 'AgentListCtrl'
            })
            .state('demo.customers', {
                url: '/customers',
                templateUrl: '/static/chat/public/templates/journey/customers/list.html',
                controller: 'CustomersListCtrl'
            })
            .state('demo.stats', {
                url: '/statistics',
                templateUrl: '/static/chat/public/templates/journey/stats/index.html',
                controller: 'StatsCtrl'
            })
            .state('demo.predictors', {
                url: '/predictors',
                templateUrl: '/static/chat/public/templates/journey/predictors/list.html',
                controller: 'PredictorsListCtrl'
            })


    });

//var socket = io.connect('ws://localhost:3031/chat/');
