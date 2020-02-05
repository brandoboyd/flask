'use strict';

var dependencies = [
    'chat.directives',
    'chat.services',
    'journey.services',
    'ui.router',
    'ui.bootstrap',
    'ui.slider',
    'ngSanitize',
    'ui.select',
    'gridster'
];

angular.module('chat', dependencies);
angular.module('chat')
.filter('propsFilter', function() {
    return function(items, props) {
        var out = [];

        if (angular.isArray(items)) {
            items.forEach(function(item) {
                var itemMatches = false;

                var keys = Object.keys(props);
                for (var i = 0; i < keys.length; i++) {
                    var prop = keys[i];
                    var text = props[prop].toLowerCase();
                    if (item[prop].toString().toLowerCase().indexOf(text) !== -1) {
                        itemMatches = true;
                        break;
                    }
                }

                if (itemMatches) {
                    out.push(item);
                }
            });
        } else {
            // Let the output be the input untouched
            out = items;
        }

        return out;
    };
});

//var socket = io.connect('ws://localhost:3031/chat/');
