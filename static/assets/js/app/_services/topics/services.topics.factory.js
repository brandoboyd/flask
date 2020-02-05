(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory("TopicsCloud", TopicsCloud)
    .factory("Topics", Topics)
    .factory("MyTopics", MyTopics)
    .factory('TopicCloudMixin', TopicCloudMixin);

  /** @ngInject */
  function TopicsCloud(Topics) {
    var TopicsCloud = {
      getTopicSize: function (count, type) {
        var fontMin = 12,
          fontMax = 40;
        var size = count == Topics.count.min ? fontMin
          : (count / Topics.count.max) * (fontMax - fontMin) + fontMin;
        var sizelog = count == Topics.count.min ? fontMin
          : (Math.log(count) / Math.log(Topics.count.max)) * (fontMax - fontMin) + fontMin;
        var styles = {log: {'font-size': sizelog + 'px'}, linear: {'font-size': size + 'px'}};
        return styles;
      }
    };
    return TopicsCloud;
  }

  /** @ngInject */
  function Topics($http, $filter, MyTopics) {
    var url = '/hot-topics/json';
    var Topics = {
      count: {
        min: null,
        max: null
      },
      search: function (term, params) {
        var punks = [];
        var promise = $http({
          method: 'POST',
          url: url,
          data: params
        }).then(function (res) {
          punks = res.data.list;
          if (term.topic_count > 0) {
            // append topics list with parent topic as leaf
            var leaf = {
              topic: term.topic,
              enabled: false,
              term_count: term.topic_count,
              topic_count: term.topic_count
            };
            punks.push(leaf);
          }
          return MyTopics.testSelection(_.map(punks, function (el) {
            el.level = term.level + 1;
            el.parent = term.parent;
            return el
          }));

        });
        return promise;
      },
      fetch: function (params, limit) {
        var promise = $http({
          method: 'POST',
          url: url,
          data: params
        }).then(function (res) {
          var data = limit ? $filter('limitTo')(res.data.list, limit) : res.data.list;
          var topics = MyTopics.testSelection(_.map(data, function (el) {
            el.level = 0;
            el.parent = el.topic;
            return el
          }));
          //store max,min counts
          Topics.count.max = _.max(topics, function (topic) {
            return topic.term_count
          })['term_count'];
          Topics.count.min = _.min(topics, function (topic) {
            return topic.term_count
          })['term_count'];
          return topics;
        });
        return promise;
      }
    };
    return Topics
  }

  /** @ngInject */
  function MyTopics($rootScope, $resource) {
    var MyTopics = $resource('topics/json', {}, {
      fetch_count: {method: 'POST', isArray: false}
    });

    MyTopics.ON_TOPICS_CHANGE = 'on_topics_change';

    var my_topics = [];
    var selectedTopicsLookup = {};
    var updateLookup = function () {
      selectedTopicsLookup = {};
      angular.forEach(my_topics, function (val) {
        selectedTopicsLookup[topicHash(val)] = true;
      });
    };

    var get_topic_type = function (el) {
      if (el.hasOwnProperty('term_count')) {
        return (el.term_count === el.topic_count ? "leaf" : "node");
      } else if (el.hasOwnProperty('topic_type')) {
        return el.topic_type;
      }
    };

    var topicHash = function (item) {
      return item.topic + ':' + get_topic_type(item);
    };

    var hasTerm = function (item) {
      return selectedTopicsLookup.hasOwnProperty(topicHash(item));
    };

    var topicsChanged = function () {
      updateLookup();
      $rootScope.$broadcast(MyTopics.ON_TOPICS_CHANGE);
    };

    MyTopics.purge = function () {
      my_topics = [];
      topicsChanged();
      return my_topics;
    };

    MyTopics.populate = function (items) {
      MyTopics.purge();
      angular.forEach(items, function (item) {
        my_topics.push(item);
      });

      topicsChanged();

      return my_topics;
    };

    MyTopics.add = function (item) {
      if (angular.isArray(item)) {
        var topics = [];
        _.each(item, function (el) {
          topics.push({
            'topic': el.topic,
            'topic_type': get_topic_type(el),
            'parent': el.parent,
            'level': el.level
          })
        })
        my_topics = topics;
      } else {
        if (hasTerm(item)) {
          //SystemAlert.info("You have this term in your selected topics.");
          MyTopics.remove(item);
        } else {
          var topic = {
            'topic': item.topic,
            'topic_type': get_topic_type(item),
            'parent': item.parent,
            'level': item.level
          };
          var same_parent = _.filter(my_topics, function (el) {
            return el.parent == item.parent && el.level != item.level;
          });
          if (same_parent.length > 0) {
            _.each(same_parent, function (el) {
              MyTopics.remove(el, true);
            })
          }
          my_topics.push(topic);
        }
      }
      topicsChanged();
    };

    MyTopics.remove = function (item, silent) {

      my_topics = _.filter(my_topics, function (val) {
        return topicHash(val) != topicHash(item);
      });
      if (!silent) {
        topicsChanged();
      }
    };

    MyTopics.getSelected = function () {
      return MyTopics.getList();
    };

    MyTopics.testSelection = function (list) {
      updateLookup();
      var new_list = _.map(list, function (item) {
        item.enabled = hasTerm(item);
        return item;
      });
      return new_list;
    };

    MyTopics.getList = function () {
      return my_topics;
    };

    MyTopics.findTopic = function (topic, list) {
      var hash = angular.isObject(topic) ? topicHash(topic) : topicHash({topic: topic, topic_type: 'leaf'});
      var found = _.find(list, function (item) {
        return topicHash(item) === hash;
      });

      if (!angular.isObject(topic) && found === undefined) {
        hash = angular.isObject(topic) ? topicHash(topic) : topicHash({topic: topic, topic_type: 'node'});
        found = _.find(list, function (item) {
          return topicHash(item) === hash;
        });
      }

      return found;
    };

    MyTopics.setTopics = function (topics) {
      if (topics.indexOf('all') >= 0) {
        my_topics = [];
      } else {
        my_topics = _.map(topics, function (topic) {
          var topicObj = MyTopics.findTopic(topic, my_topics);
          if (topicObj === undefined) {
            console.log("Topic (" + topic + ") to be set as selected in facet was not found.");
          }
          return topicObj;
        });
      }
      topicsChanged();
      return my_topics;
    };

    return MyTopics;

  }

  /** @ngInject */
  function TopicCloudMixin() {
    var scopeMixin = {
      _topic_mixin_state: {
        cloud_type: 'none'
      },

      changeCloudView: function (cloud_type) {
        this._topic_mixin_state.cloud_type = cloud_type;
        this.loadTopics();
      },

      getCloudType: function () {
        return this._topic_mixin_state.cloud_type;
      }
    };
    return scopeMixin;
  }
})();