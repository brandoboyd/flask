(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('MetadataService', MetadataService);

  /** @ngInject */
  function MetadataService() {
    var MetadataService = {};
    var Apps = {
      'GSA': 'GSA',
      'GSE': 'GSE',
      'PRR': 'Predictive Matching',
      'JA': 'Journey Analytics',
      'NPS': 'NPS'
    };
    var intentions =
      [
        {display: 'asks', label: 'asks', enabled: false, color: '#38854d'},
        {display: 'needs', label: 'needs', enabled: false, color: '#0d89ab'},
        {display: 'likes', label: 'likes', enabled: false, color: '#ff9228'},
        {display: 'problems', label: 'problem', enabled: false, color: '#999999'},
        {display: 'checkins', label: 'checkins', enabled: false, color: '#333333'},
        {display: 'apologies', label: 'apology', enabled: false, color: '#6895d8'},
        {display: 'recommendations', label: 'recommendation', enabled: false, color: '#c26117'},
        {display: 'considerations', label: 'consideration', enabled: false, color: '#dfbc5f'},
        {display: 'discarded', label: 'discarded', enabled: false, color: '#ff0000'},
        {display: 'gratitude', label: 'gratitude', enabled: false, color: '#97b539'},
        {display: 'offers', label: 'offer', enabled: false, color: '#58cecb'},
        {display: 'other', label: 'junk', enabled: false, color: '#f5a7a2'}
      ];

    // TODO: should be merged with metadata above
    var intention_type = [

    ];

    var postStatuses =
      [
        {label: 'actionable', display: 'actionable', enabled: true},
        {label: 'actual', display: 'replied', enabled: true},
        //{ label : 'potential' , display : 'potential',  enabled : true},
        {label: 'rejected', display: 'rejected', enabled: true}
      ];

    var sentiments =
      [
        {label: 'positive', enabled: false, color: '#0DBD39'},
        {label: 'negative', enabled: false, color: '#E0351B'},
        {label: 'neutral', enabled: false, color: '#E0AB1B'}
      ];

    var event_types =
      [
        {label: 'voice', icon: 'icon-phone-voice'},
        {label: 'twitter', icon: 'icon-iw-active-circle-twitter'},
        {label: 'chat', icon: 'icon-chat-multi'},
        {label: 'web', icon: 'icon-cobrowse'},
        {label: 'webclick', icon: 'icon-cobrowse'},
        {label: 'faq', icon: 'icon-help'},
        {label: 'email', icon: 'icon-email'},
        {label: 'facebook', icon: 'icon-iw-active-circle-facebook'},
        {label: 'branch', icon: 'icon-tree-branch'},
        {label: 'nps', icon: 'icon-face-happy'}
      ];

    var defaultPathMetrics =
      [
        {label: 'Common Path', measure: 'max'}
      ];

    var message_types =
      [
        {display: 'Public messages', label: 0, enabled: true},
        {display: 'Direct messages', label: 1, enabled: true}
      ];

    var age_groups =
      [
        {
          display_name: '16 - 25',
          display: '16 - 25', label: '16 - 25', enabled: false
        },
        {
          display_name: '26 - 35',
          display: '26 - 35', label: '26 - 35', enabled: false
        },
        {
          display_name: '36 - 45',
          display: '36 - 45', label: '36 - 45', enabled: false
        },
        {
          display_name: '46 -',
          display: '46+', label: '46 -', enabled: false
        }
      ];

    var customer_statuses =
      [
        {
          display_name: 'NEW',
          display: 'NEW', label: 'NEW', enabled: false
        },
        {
          display_name: 'REGULAR',
          display: 'REGULAR', label: 'REGULAR', enabled: false
        },
        {
          display_name: 'IMPORTANT',
          display: 'IMPORTANT', label: 'IMPORTANT', enabled: false
        },
        {
          display_name: 'VIP',
          display: 'VIP', label: 'VIP', enabled: false
        }
      ];

    var agent_occupancy =
      [
        {display: '0% - 10%', label: '0% - 10%', enabled: false},
        {display: '11% - 30%', label: '11% - 30%', enabled: false},
        {display: '31% - 50%', label: '31% - 50%', enabled: false},
        {display: '51% - 100%', label: '51% - 100%', enabled: false}
      ];

    var nps = [
      {value: 'n/a', display_name: 'N/A'},
      {value: 'promoter', display_name: 'Promoters'},
      {value: 'passive', display_name: 'Passives'},
      {value: 'detractor', display_name: 'Detractors'}
    ];

    var journey_status = [
      {display_name: 'finished'},
      {display_name: 'abandoned'},
      {display_name: 'ongoing'}
    ];

    var languages = [];

    var plot_filters = [
      {type: 'sentiment', enabled: false},
      {type: 'topic', enabled: false},
      {type: 'intention', enabled: false},
      {type: 'status', enabled: false},
      {type: 'agent', enabled: false},
      {type: 'time', enabled: false},
      {type: 'segment', enabled: false},
      {type: 'industry', enabled: false},
      {type: 'Status', enabled: false},
      {type: 'location', enabled: false},
      {type: 'gender', enabled: false},
      {type: 'Mean Error', enabled: false},
      {type: 'Mean Latency', enabled: false},
      {type: 'Mean Reward', enabled: false}
    ];

    var CSVSeparators = [
      { value: '\t', text: 'TAB' },
      { value: ',', text: 'COMMA' },
    ];

    var dateFileTypes = [
      { value: 'json', text: 'JSON', extension: '.json' },
      { value: 'csv', text: 'CSV', extension: '.csv' },
    ];

    var schemaFieldTypes = [

      { value: 'boolean', id: 'boolean', text: 'Boolean' },
      { value: 'integer', id: 'integer', text: 'Numeric' }, //TODO? actual value is still 'integer'
      { value: 'list',    id: 'list', text: 'List' },
      { value: 'string',  id: 'string', text: 'String' },
      { value: 'timestamp', id: 'timestamp', text: 'Timestamp' },
      { value: 'dict',    id: 'dict', text: 'Dict' }
    ];

    var eventTypeFieldFlags = [
      { value: 'faceted', text: 'Faceted' },
      { value: 'required', text: 'Requried'},
    ];

    MetadataService.getIntentions = function () {
      return intentions;
    };

    MetadataService.getAgeGroups = function () {
      return age_groups;
    };

    MetadataService.getAgentOccupancy = function () {
      return agent_occupancy;
    };

    MetadataService.getCustomerStatuses = function () {
      return customer_statuses;
    };

    MetadataService.getJourneyStatus = function () {
      return journey_status;
    };

    MetadataService.getLanguages = function () {
      return languages;
    };

    MetadataService.getMessageTypes = function () {
      return message_types;
    };

    MetadataService.getNPS = function () {
      return nps;
    };

    MetadataService.getPlotFilters = function () {
      return plot_filters;
    };

    MetadataService.getPostStatuses = function () {
      return postStatuses;
    };

    MetadataService.getSentiments = function () {
      return sentiments;
    };
    
    MetadataService.getApps = function () {
      return Apps;      
    };

    MetadataService.getSchemaFieldTypes = function () {
      return schemaFieldTypes;
    };

    MetadataService.getBeautifiedStatus = function(entity, type) {
      if (!entity) {
        return 'N/A';
      }

      var entity_type = type && type == 'channel' ? 'Channels' : 'Schema';

      switch (entity.sync_status) {
        case 'IMPORTING':
          return (entity.load_progress < 100)
            ? 'Loading data...'
            : 'Appending data...';
          break;
        case 'SYNCING':
          return 'Applying schema...';
        case 'SYNCED':
          return 'Schema applied';
        case 'OUT_OF_SYNC':
          return entity_type + ' out of synchronization';
        case 'IN_SYNC':
          return entity_type + ' synchronized';
        default:
          return 'N/A';  
      }
    };

    MetadataService.getEventTypes = function () {
      return event_types;
    };

    MetadataService.getCSVSeparators = function() {
      return CSVSeparators;
    };

    MetadataService.getDataFileTypes = function() {
      return dateFileTypes;
    };
    
    MetadataService.getEventTypeIcon = function (eventtype) {
      var icon = 'icon-iw-active-circle-question';
      var found = _.find(event_types, {label: eventtype.toLowerCase()});
      if (found) {
        icon = found.icon;
      }
      return icon;
    };

    MetadataService.getEventTypes = function () {
      return event_types;
    };

    MetadataService.getEventTypeFieldFlags = function () {
      return eventTypeFieldFlags;
    };

    MetadataService.getDefaultPathMetrics = function () {
      return defaultPathMetrics;
    };

    MetadataService.getIntentionClass = function (intention_type) {
      var className;
      switch(intention_type) {
        case ('Asks for Something'): className = 'asks'; break;
        case ('States a Need / Want'): className = 'needs'; break;
        case ('States a Problem / Dislikes'): className = 'problem'; break;
        case ('Likes...'): className = 'likes'; break;
        case ('Offer Help'): className = 'offer'; break;
        case ('Checkin'): className = 'checkins'; break;
        case ('Gratitude'): className = 'gratitude'; break;
        case ('Apology'): className = 'apology'; break;
        case ('Recommendation'): className = 'recommendation'; break;
        case ('Junk'): className = 'junk'; break;
        default : className = 'junk';
      }
      return className;
    };

    MetadataService.processDataType = function (d) {
      switch (d.toLowerCase()) {
        case('string'):
          return 'Label'; break;
        case('integer'):case('double'):case('timestamp'):
          return 'Numeric'; break;
        case('boolean'):
          return 'Boolean'; break;
        default:
          return 'Numeric'; break;
      }
    };


    return MetadataService;
  }
})();
