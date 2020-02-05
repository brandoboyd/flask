'use strict';

angular.module('ark-dashboard', ['ark-ui-bootstrap', 'ui.sortable', 'nvd3']);

angular.module('ark-dashboard')
  .directive('dashboard', ['WidgetModel', 'ExpandToTabModel', 'WidgetDefCollection', '$modal', 'DashboardState', '$log', 'DashboardMenuObject', function (WidgetModel, ExpandToTabModel, WidgetDefCollection, $modal, DashboardState, $log, DashboardMenuObject) {
    return {
      restrict: 'A',
      templateUrl: function(element, attr) {
        return attr.templateUrl ? attr.templateUrl : 'src/dashboard/template/dashboard.html';
      },
      scope: true,

      controller: ['$scope', '$attrs', function (scope, attrs) {

        // default options
        var defaults = {
          stringifyStorage: true,
          hideWidgetSettings: false,
          hideWidgetClose: false,
          hideWidgetName: true,
          settingsModalOptions: {
            templateUrl: 'src/dashboard/template/rename-template.html',
            controller: 'renameModalCtrl'
          }
        };

        // from dashboard="options"
        scope.options = scope.$eval(attrs.dashboard);

        // Deep options
        scope.options.settingsModalOptions = scope.options.settingsModalOptions || {};
        _.each(['settingsModalOptions'], function(key) {
          // Ensure it exists on scope.options
          scope.options[key] = scope.options[key] || {};
          // Set defaults
          _.defaults(scope.options[key], defaults[key]);
        });

        // Shallow options
        _.defaults(scope.options, defaults);

        var sortableDefaults = {
          stop: function () {
            scope.saveDashboard();
          },
          handle: '.widget-header'
        };
        scope.sortableOptions = angular.extend({}, sortableDefaults, scope.options.sortableOptions || {});


      }],
      link: function (scope) {
        scope.widgetList = new DashboardMenuObject(scope.options.customWidgetDropdownMenu, scope.options.customWidgetDropdownActions);

        scope.defaultWidgetActions = [
            {
              'renameWidget' : function(widget) {
                scope.openWidgetSettings(widget);
              }
            },
            {
              'clone' : function(widget) {
                scope.clone(widget);
              }
            },
            {
              'removeWidget' : function(widget) {
                scope.removeWidget(widget);
              }
            }
          ];

        // Save default widget config for reset
        scope.defaultWidgets = scope.options.defaultWidgets;

        //scope.widgetDefs = scope.options.widgetDefinitions;
        scope.widgetDefs = new WidgetDefCollection(scope.options.widgetDefinitions);
        var count = 1;

        // Instantiate new instance of dashboard state
        scope.dashboardState = new DashboardState(
          scope.options.storage,
          scope.options.storageId,
          scope.options.storageHash,
          scope.widgetDefs,
          scope.options.stringifyStorage
        );

        scope.gridsterOpts = {
          columns: 6, // the width of the grid, in columns
          pushing: true, // whether to push other items out of the way on move or resize
          floating: true, // whether to automatically float items up so they stack (you can temporarily disable if you are adding unsorted items with ng-repeat)
          swapping: false, // whether or not to have items of the same size switch places instead of pushing down if they are the same size
          width: 'auto', // can be an integer or 'auto'. 'auto' scales gridster to be the full width of its containing element
          colWidth: 200, // can be an integer or 'auto'.  'auto' uses the pixel width of the element divided by 'columns'
          rowHeight: 200, // can be an integer or 'match'.  Match uses the colWidth, giving you square widgets.
          margins: [0, 0], // the pixel distance between each widget
          outerMargin: true, // whether margins apply to outer edges of the grid
          isMobile: true, // stacks the grid items if true
          mobileBreakPoint: 767, // if the screen is not wider that this, remove the grid layout and stack the items
          mobileModeEnabled: true, // whether or not to toggle mobile mode when screen width is less than mobileBreakPoint
          minColumns: 1, // the minimum columns the grid must have
          minRows: 1, // the minimum height of the grid, in rows
          maxRows: 100,
          defaultSizeX: 2, // the default width of a gridster item, if not specifed
          defaultSizeY: 2, // the default height of a gridster item, if not specified
          minSizeX: 1, // minimum column width of an item
          maxSizeX: null, // maximum column width of an item
          minSizeY: 1, // minumum row height of an item
          maxSizeY: null, // maximum row height of an item
          resizable: {
            enabled: true,
            handles: ['n', 'e', 's', 'w', 'ne', 'se', 'sw', 'nw'],
            stop: function (el, ui, widget) {
              scope.$emit('RESIZED', {
                resolution: {
                  width: $(ui[0].children[0].lastElementChild).width(),
                  height: $(ui[0].children[0].lastElementChild).height()
                },
                widget: widget
              });
              scope.resize();

              // Trigger 'resize' event of widget content manually
              var $elem = $(ui[0].children[0].lastElementChild).children();
              $elem.trigger($.Event('resize'));
            }
          },
          draggable: {
            enabled: true, // whether dragging items is supported
            handle: '.widget-anchor',
            stop: function () {
              scope.drag();
            }
          }
        };

        /**
         * Resize widget and save sizes
         * @param  {Object} widget The widget instance object (not a definition object)
         */
        scope.resize = function() {
          scope.saveDashboard(true);
        };

        /**
         * Grag widget and save sizes
         * @param  {Object} widget The widget instance object (not a definition object)
         */
        scope.drag = function() {
          scope.saveDashboard(true);
        };

        /**
         * Instantiates a new widget on the dashboard
         * @param {Object} widgetToInstantiate The definition object of the widget to be instantiated
         */
        scope.addWidget = function (widgetToInstantiate, doNotSave) {
          var defaultWidgetDefinition = scope.widgetDefs.getByName(widgetToInstantiate.name);
          if (!defaultWidgetDefinition) {
            throw 'Widget ' + widgetToInstantiate.name + ' is not found.';
          }
          // Determine the title for the new widget
          var title;
          if (widgetToInstantiate.title) {
            title = widgetToInstantiate.title;
          } else if (defaultWidgetDefinition.title) {
            title = defaultWidgetDefinition.title;
          } else {
            title = 'Widget ' + count++;
          }

         // Determine the sizes for the new widget
          var sizeX;
          var sizeY;
          if(widgetToInstantiate.sizeX) {
            sizeX = widgetToInstantiate.sizeX;
          }
          if(widgetToInstantiate.sizeY) {
            sizeY = widgetToInstantiate.sizeY;
          }

         // Determine the row and column positions for the new widget
          var row;
          var col;
          if(widgetToInstantiate.row !== undefined) {
            row = widgetToInstantiate.row;
          }
          if(widgetToInstantiate.col) {
            col = widgetToInstantiate.col;
          } else {
            col = 0;
          }

          // Deep extend a new object for instantiation
          widgetToInstantiate = angular.extend(widgetToInstantiate, defaultWidgetDefinition);

          var chartOptions = widgetToInstantiate.chartOptions;
          var chartData = widgetToInstantiate.chartData;

          // Instantiation
          var widget = new WidgetModel(widgetToInstantiate, {
            title: title,
            sizeX:sizeX,
            sizeY:sizeY,
            row: row,
            col: col,
            chartOptions: chartOptions,
            chartData: chartData
          });

          scope.widgets.push(widget);
          if (!doNotSave) {
            scope.saveDashboard();
          }

          return widget;
        };

        /**
         * Removes a widget instance from the dashboard
         * @param  {Object} widget The widget instance object (not a definition object)
         */
        scope.removeWidget = function (widget) {
          scope.deleteWidget(widget.attrs.id).then(function() {
            scope.widgets.splice(_.indexOf(scope.widgets, widget), 1);
            scope.saveDashboard(true);
          });
        };

        /**
         * Expands current widget to new tab full size
         * @param  {Object} widget The widget instance object (not a definition object)
         */
        scope.expandToTab = function (widget) {

          var newL = scope.$parent.$parent.createNewLayout(true);

          var title = widget.title;
          var data = widget.chartData;
          var options = widget.chartOptions;

          // // Instantiation
          var newWidget = new ExpandToTabModel(widget, {
            title:title,
            chartData: data,
            chartOptions: options,
            sizeX: 6,
            sizeY: 6
          });

          newL.dashboard.defaultWidgets = [newWidget];
          scope.saveDashboard();
        };

        /**
         * Opens a dialog for setting and changing widget properties
         * @param  {Object} widget The widget instance object
         */
        scope.openWidgetSettings = function (widget) {

          // Set up $modal options
          var options = _.defaults(
            { scope: scope },
            widget.settingsModalOptions,
            scope.options.settingsModalOptions);

          // Ensure widget is resolved
          options.resolve = {
            title: function () {
              return widget.title;
            },
            type: function () {
              return 'Widget';
            }
          };
          var oldtitle = widget.title;

          // Create the modal
          var modalInstance = $modal.open(options);

          // Set resolve and reject callbacks for the result promise
          modalInstance.result.then(
            function (result) {
              widget.title = result;
              //AW Persist title change from options editor
              scope.$emit('widgetChanged', widget);
              //Save dashboard
              scope.saveDashboard(true);

              scope.updateWidget(widget);
            },
            function () {
              widget.title = oldtitle;
            }
          );

        };

        /**
         * Remove all widget instances from dashboard
         */
        scope.clear = function (doNotSave) {
          scope.widgets = [];
          if (doNotSave === true) {
            return;
          }
          scope.saveDashboard(true);
        };

        /**
         * Clone current widget
         * @param  {Object} widget The widget instance object
         */
        scope.clone = function (widget) {

          var title = widget.title;
          var sizeX;
          var sizeY;

          if(widget.sizeX) {
            sizeX = widget.sizeX;
          }
          if(widget.sizeY) {
            sizeY = widget.sizeY;
          }

          // Instantiation
          var clonewidget = new WidgetModel(widget, {
            title:title,
            sizeX:sizeX,
            sizeY:sizeY
          });

          scope.widgets.push(clonewidget);
          scope.saveDashboard();

          return clonewidget;
        };

        /**
         * Used for preventing default on click event
         * @param {Object} event     A click event
         * @param {Object} widgetDef A widget definition object
         */
        scope.addWidgetInternal = function (event, widgetDef) {
          event.preventDefault();
          scope.addWidget(widgetDef);
        };

        /**
         * Uses dashboardState service to save state
         */
        scope.saveDashboard = function (force) {
          if (!scope.options.explicitSave) {
            scope.updateSizeAndPosition(scope.selectedLayout.id, scope.widgets);
            scope.dashboardState.save(scope.widgets);
          } else {
            if (!angular.isNumber(scope.options.unsavedChangeCount)) {
              scope.options.unsavedChangeCount = 0;
            }
            if (force) {
              scope.options.unsavedChangeCount = 0;
              scope.dashboardState.save(scope.widgets);

            } else {
              ++scope.options.unsavedChangeCount;
            }
          }
        };

        /**
         * Wraps saveDashboard for external use.
         */
        scope.externalSaveDashboard = function() {
          scope.saveDashboard(true);
        };

        /**
         * Clears current dash and instantiates widget definitions
         * @param  {Array} widgets Array of definition objects
         */
        scope.loadWidgets = function (widgets) {
          // AW dashboards are continuously saved today (no "save" button).
          //scope.defaultWidgets = widgets;
          scope.savedWidgetDefs = widgets;
          scope.clear(true);
          _.each(widgets, function (widgetDef) {
            scope.addWidget(widgetDef, true);
          });
        };

        /**
         * Resets widget instances to default config
         * @return {[type]} [description]
         */
        scope.resetWidgetsToDefault = function () {
          scope.loadWidgets(scope.defaultWidgets);
          scope.saveDashboard();
        };

        // Set default widgets array
        var savedWidgetDefs = scope.dashboardState.load();

        // Success handler
        function handleStateLoad(saved) {
          scope.options.unsavedChangeCount = 0;
          if (saved && saved.length) {
            scope.loadWidgets(saved);
          } else if (scope.defaultWidgets) {
            scope.loadWidgets(scope.defaultWidgets);
          } else {
            scope.clear(true);
          }
        }

        angular.element(document).on('click', 'a.nav-tabs-dropdown', function (event) {
          angular.element('.widget-container').removeClass('gridster-item-moving-dropdown-open');
          angular.element(this).closest('.widget-container').addClass('gridster-item-moving-dropdown-open');
          var width = angular.element(window).width();
          var leftOffset = event.pageX;
          if(width - leftOffset < 220 ) {
            angular.element('.nav-tabs-dropdown-menu').addClass('dropdown-menu-pull-right');
            angular.element('.nav-tabs-dropdown-menu').removeClass('dropdown-menu-pull-left');
          } else {
            angular.element('.nav-tabs-dropdown-menu').removeClass('dropdown-menu-pull-right');
            angular.element('.nav-tabs-dropdown-menu').addClass('dropdown-menu-pull-left');
          }
        });

        if (angular.isArray(savedWidgetDefs)) {
          handleStateLoad(savedWidgetDefs);
        } else if (savedWidgetDefs && angular.isObject(savedWidgetDefs) && angular.isFunction(savedWidgetDefs.then)) {
          savedWidgetDefs.then(handleStateLoad, handleStateLoad);
        } else {
          handleStateLoad();
        }

        // expose functionality externally
        // functions are appended to the provided dashboard options
        scope.options.addWidget = scope.addWidget;
        scope.options.loadWidgets = scope.loadWidgets;
        scope.options.saveDashboard = scope.externalSaveDashboard;
        scope.options.removeWidget = scope.removeWidget;
        scope.options.openWidgetSettings = scope.openWidgetSettings;

        // save state
        scope.$on('widgetChanged', function (event) {
          event.stopPropagation();
          scope.saveDashboard();
        });
      }
    };
  }]);

'use strict';

angular.module('ark-dashboard')
  .directive('dashboardLayouts', ['LayoutStorage', '$timeout', '$modal', 'LayoutMenuObject', '$http', 'WidgetDataModel',
    function(LayoutStorage, $timeout, $modal, LayoutMenuObject, $http, WidgetDataModel) {
      return {
        scope: true,
        templateUrl: function(element, attr) {
          return attr.templateUrl ? attr.templateUrl : 'src/dashboard/template/dashboard-layouts.html';
        },
        link: function(scope, element, attrs) {

          scope.widgetLayout = true;

          scope.getLayouts();

          scope.options = scope.$eval(attrs.dashboardLayouts);
          var layoutStorage = new LayoutStorage(scope.options);
          scope.layouts = layoutStorage.layouts;
          scope.layoutList = new LayoutMenuObject(scope.options.customLayoutDropdownMenu, scope.options.customLayoutDropdownActions);

          scope.$on('readyLayouts', function (event, layouts) {
            layouts.forEach(function (dashboard, index) {
              var newLayout = angular.extend(dashboard, {type: 'widget'});
              newLayout.defaultWidgets = dashboard.defaultWidgets || scope.options.defaultWidgets;

              layoutStorage.add(newLayout);
              if (index === 0) {
                scope._makeLayoutActive(newLayout);
              }
              layoutStorage.save();
            });
          });

          scope.defaultLayoutActions = [
            {
              'renameLayout' : function() {
                scope.renameLayout();
              }
            },
            {
              'resetWidgetsToDefault' : function() {
                scope.resetWidgetsToDefault();
              }
            },
            {
              'saveDashboard' : function() {
                scope.options.saveDashboard();
              }
            },
            {
              'removeLayout' : function() {
                scope.removeLayout();
              }
            },
            {
              'shareLayout' : function () {
                scope.shareLayout();
              }
            }
          ];

          scope.createNewLayout = function() {
            scope.buildDashboard();
          };

          scope.createNewWidget = function(layout) {
            scope.buildWidget(layout);
          };

          scope.$on('dashboardBuilt', function (event, dashboard) {
            var newLayout = {
              title: dashboard.title,
              type: 'widget',
              owner: dashboard.owner_name,
              author: dashboard.author_name,
              authorId: dashboard.author,
              ownerId: dashboard.owner,
              accountId: dashboard.account_id,
              type_id: dashboard.type_id,
              isTypeDefault: dashboard.type == 'blank',
              dashboardType: dashboard.type,
              id: dashboard.id,
              filters: dashboard.filters,
              defaultWidgets: dashboard.widgets || scope.options.defaultWidgets,
              shared_to: dashboard.shared_to
            };
            layoutStorage.add(newLayout);
            scope.addNewDashboard(newLayout);
            scope._makeLayoutActive(newLayout);
            layoutStorage.save();
            return newLayout;
          });

          scope.removeLayout = function(curlayout) {
            var layout = curlayout || layoutStorage.getActiveLayout();
            layoutStorage.remove(layout);

            scope.removeDashboard(layout);
            var activeLayout = layoutStorage.getActiveLayout();
            activeLayout && scope._makeLayoutActive(activeLayout);

            layoutStorage.save();
          };

          scope.makeLayoutActive = function(layout) {
            var current = layoutStorage.getActiveLayout();

            if (current && current.dashboard.unsavedChangeCount) {
              var modalInstance = $modal.open({
                templateUrl: 'src/dashboard/template/save-changes-modal.html',
                resolve: {
                  layout: function() {
                    return layout;
                  }
                },
                controller: 'SaveChangesModalCtrl'
              });

              // Set resolve and reject callbacks for the result promise
              modalInstance.result.then(
                function() {
                  scope.options.saveDashboard();
                  scope._makeLayoutActive(layout);
                },
                function() {
                  scope._makeLayoutActive(layout);
                }
              );
            } else {
              scope._makeLayoutActive(layout);
            }

          };

          scope._makeLayoutActive = function(layout) {
            scope.selectDashboard(layout);
            angular.forEach(scope.layouts, function(l) {
              if (l !== layout) {
                l.active = false;
              } else {
                l.active = true;
              }
            });
            layoutStorage.save();
          };

          scope.isActive = function(layout) {
            return !!layout.active;
          };

          scope.renameLayout = function(curlayout) {

            var layout = curlayout || layoutStorage.getActiveLayout();

            var modalInstance = $modal.open({
              templateUrl: 'src/dashboard/template/rename-template.html',
              resolve: {
                title: function() {
                  return layout.title;
                },
                type: function() {
                  return 'Dashboard';
                }
              },
              controller: 'renameModalCtrl'
            });

            var oldtitle = layout.title;

            // Set resolve and reject callbacks for the result promise
            modalInstance.result.then(
              function (result) {
                layout.title = result;

                scope.updateDashboard(layout);

                scope._makeLayoutActive(layout);
                scope.options.saveDashboard();
                scope.addTooptip();
              },
              function() {
                layout.title = oldtitle;
                scope._makeLayoutActive(layout);
              }
            );
          };

          scope.shareLayout = function (curlayout) {
            var layout = curlayout || layoutStorage.getActiveLayout();
            scope.shareDashboard(layout);
          };

          // saves whatever is in the title input as the new title
          scope.saveTitleEdit = function(layout) {
            layout.editingTitle = false;
            layoutStorage.save();
          };

          scope.options.saveLayouts = function() {
            layoutStorage.save(true);
          };
          scope.options.addWidget = function() {
            var layout = layoutStorage.getActiveLayout();
            if (layout) {
              layout.dashboard.addWidget.apply(layout.dashboard, arguments);
            }
          };
          scope.options.loadWidgets = function() {
            var layout = layoutStorage.getActiveLayout();
            if (layout) {
              layout.dashboard.loadWidgets.apply(layout.dashboard, arguments);
            }
          };
          scope.resetWidgetsToDefault = function () {
            var layout = layoutStorage.getActiveLayout();
            layout.dashboard.loadWidgets(layout.defaultWidgets);
            scope.options.saveDashboard();
          };
          scope.options.saveDashboard = function() {
            var layout = layoutStorage.getActiveLayout();
            if (layout) {
              layout.dashboard.saveDashboard.apply(layout.dashboard, arguments);
            }
          };

          scope.addTooptip = function () {
            $timeout(function(){
              var el = element.find('.tabs-title');
              for(var i = 0; i < el.length; i++) {
                if(el[i].offsetWidth < el[i].scrollWidth) {
                  scope.layouts[i].showTooltip = true;
                } else {
                  scope.layouts[i].showTooltip = false;
                }
              }
            });
          };

          var sortableDefaults = {
            stop: function() {
              scope.options.saveLayouts();
            },
            axis: 'x',
            placeholder: 'sortable-placeholder'
          };
          scope.sortableOptions = angular.extend({}, sortableDefaults, scope.options.sortableOptions || {});
        }
      };
    }
  ]);

'use strict';

angular.module('ark-dashboard');

angular.module('ark-dashboard')
  .directive('expandToTab', function () {
    return {
      restrict: 'A',
      templateUrl: function(element, attr) {
        return attr.templateUrl ? attr.templateUrl : 'src/dashboard/template/expand-to-tab.html';
      },
      scope: true,

      controller: ['$scope', '$attrs', function (scope, attrs) {

        // from dashboard="options"
        scope.options = scope.$eval(attrs.expandToTab);

        scope.expand = scope.options.defaultWidgets[0];

      }],
      link: function (scope) {

        scope.gridsterOpts = {
          columns: 6, // the width of the grid, in columns
          pushing: true, // whether to push other items out of the way on move or resize
          floating: true, // whether to automatically float items up so they stack (you can temporarily disable if you are adding unsorted items with ng-repeat)
          swapping: false, // whether or not to have items of the same size switch places instead of pushing down if they are the same size
          width: 'auto', // can be an integer or 'auto'. 'auto' scales gridster to be the full width of its containing element
          colWidth: 'auto', // can be an integer or 'auto'.  'auto' uses the pixel width of the element divided by 'columns'
          rowHeight: 'match', // can be an integer or 'match'.  Match uses the colWidth, giving you square widgets.
          margins: [0, 0], // the pixel distance between each widget
          outerMargin: true, // whether margins apply to outer edges of the grid
          isMobile: true, // stacks the grid items if true
          mobileBreakPoint: 767, // if the screen is not wider that this, remove the grid layout and stack the items
          mobileModeEnabled: false, // whether or not to toggle mobile mode when screen width is less than mobileBreakPoint
          minColumns: 1, // the minimum columns the grid must have
          minRows: 2, // the minimum height of the grid, in rows
          maxRows: 100,
          defaultSizeX: 6, // the default width of a gridster item, if not specifed
          defaultSizeY: 6, // the default height of a gridster item, if not specified
          minSizeX: 6, // minimum column width of an item
          maxSizeX: 6, // maximum column width of an item
          minSizeY: 6, // minumum row height of an item
          maxSizeY: 6, // maximum row height of an item
          resizable: {
            enabled: false
          },
          draggable: {
            enabled: false
          }
        };
      }
    };
  });

'use strict';

angular.module('ark-dashboard')
  .directive('widget', ['$injector', function ($injector) {

    return {

      controller: 'DashboardWidgetCtrl',

      link: function (scope) {

        var widget = scope.widget;
        if (_.isUndefined(widget)) return;
        var dataModelType = widget.dataModelType;

        scope.loading = true;
        if (widget.name == 'add-widget') scope.loading = false;

        // set up data source
        if (dataModelType) {
          var DataModelConstructor; // data model constructor function

          if (angular.isFunction(dataModelType)) {
            DataModelConstructor = dataModelType;
          } else if (angular.isString(dataModelType)) {
            $injector.invoke([dataModelType, function (DataModelType) {
              DataModelConstructor = DataModelType;
            }]);
          } else {
            throw new Error('widget dataModelType should be function or string');
          }

          var ds;
          if (widget.dataModelArgs) {
            ds = new DataModelConstructor(widget.dataModelArgs);
          } else {
            ds = new DataModelConstructor();
          }
          widget.dataModel = ds;
          ds.setup(widget, scope);
          ds.init(function dataLoaded() {scope.loading = false;});
          scope.$on('$destroy', _.bind(ds.destroy,ds));
        }

        // Compile the widget template, emit add event
        scope.compileTemplate();
        scope.$emit('widgetAdded', widget);

      }

    };
  }]);

'use strict';

angular.module('ark-dashboard')
  .factory('DashboardMenuObject', function () {
    function DashboardMenuObject(customList, customActions) {

      var defaultList;
      var defaultActions;
      var widgetList = {};
      widgetList.list = {};
      widgetList.actions = {};

      var menuList = {
        'customWidgetMenuList':[
          {
            'menuLocalizedTitle':'Rename',
            'menuIcon':'icon-24-graph-edit',
            'menuOptionKey':'renameWidget'
          },
          // {
            // 'menuLocalizedTitle':'Clone',
            // 'menuIcon':'icon-clone',
            // 'menuOptionKey':'clone'
          // },
          {
            'menuLocalizedTitle':'Delete',
            'menuIcon':'icon-trash',
            'menuOptionKey':'removeWidget',
            'requireConfirmPopup': true,
            'tooltip': 'Delete this widget',
            'confirmMessage': 'Are you sure to delete this widget?'
          }
        ],

        'customWidgetMenuActions':['renameWidget','clone', 'removeWidget']
      };

      defaultList = menuList.customWidgetMenuList;
      defaultActions = menuList.customWidgetMenuActions;

      var overrideList = customList || {};
      var overrideActions = customActions || {};

      widgetList.list = $.merge($.merge([], defaultList), overrideList);
      widgetList.actions = $.merge($.merge([], defaultActions), overrideActions);

      return widgetList;
    }
    return DashboardMenuObject;
  });

'use strict';

angular.module('ark-dashboard')
  .factory('DashboardState', ['$log', '$q', function ($log, $q) {
    function DashboardState(storage, id, hash, widgetDefinitions, stringify) {
      this.storage = storage;
      this.id = id;
      this.hash = hash;
      this.widgetDefinitions = widgetDefinitions;
      this.stringify = stringify;
    }

    DashboardState.prototype = {
      /**
       * Takes array of widget instance objects, serializes,
       * and saves state.
       *
       * @param  {Array} widgets  scope.widgets from dashboard directive
       * @return {Boolean}        true on success, false on failure
       */
      save: function (widgets) {

        if (!this.storage) {
          return true;
        }

        var serialized = _.map(widgets, function (widget) {
          var widgetObject = {
            title: widget.title,
            name: widget.name,
            style: widget.style,
            size: widget.size,
            sizeX: widget.sizeX,
            sizeY: widget.sizeY,
            col: widget.col,
            row: widget.row,
            dataModelOptions: widget.dataModelOptions,
            storageHash: widget.storageHash,
            attrs: widget.attrs
          };

          return widgetObject;
        });

        var item = { widgets: serialized, hash: this.hash };

        if (this.stringify) {
          item = JSON.stringify(item);
        }

        this.storage.setItem(this.id, item);
        return true;
      },

      /**
       * Loads dashboard state from the storage object.
       * Can handle a synchronous response or a promise.
       *
       * @return {Array|Promise} Array of widget definitions or a promise
       */
      load: function () {

        if (!this.storage) {
          return null;
        }

        var serialized;

        // try loading storage item
        serialized = this.storage.getItem( this.id );

        if (serialized) {
          // check for promise
          if (angular.isObject(serialized) && angular.isFunction(serialized.then)) {
            return this._handleAsyncLoad(serialized);
          }
          // otherwise handle synchronous load
          return this._handleSyncLoad(serialized);
        } else {
          return null;
        }
      },

      _handleSyncLoad: function(serialized) {

        var deserialized, result = [];

        if (!serialized) {
          return null;
        }

        if (this.stringify) {
          try { // to deserialize the string

            deserialized = JSON.parse(serialized);

          } catch (e) {

            // bad JSON, log a warning and return
            $log.warn('Serialized dashboard state was malformed and could not be parsed: ', serialized);
            return null;

          }
        }
        else {
          deserialized = serialized;
        }

        // check hash against current hash
        if (deserialized.hash !== this.hash) {

          $log.info('Serialized dashboard from storage was stale (old hash: ' + deserialized.hash + ', new hash: ' + this.hash + ')');
          this.storage.removeItem(this.id);
          return null;

        }

        // Cache widgets
        var savedWidgetDefs = deserialized.widgets;

        // instantiate widgets from stored data
        for (var i = 0; i < savedWidgetDefs.length; i++) {

          // deserialized object
          var savedWidgetDef = savedWidgetDefs[i];

          // widget definition to use
          var widgetDefinition = this.widgetDefinitions.getByName(savedWidgetDef.name);

          // check for no widget
          if (!widgetDefinition) {
            // no widget definition found, remove and return false
            $log.warn('Widget with name "' + savedWidgetDef.name + '" was not found in given widget definition objects');
            continue;
          }

          // check widget-specific storageHash
          if (widgetDefinition.hasOwnProperty('storageHash') && widgetDefinition.storageHash !== savedWidgetDef.storageHash) {
            // widget definition was found, but storageHash was stale, removing storage
            $log.info('Widget Definition Object with name "' + savedWidgetDef.name + '" was found ' +
              'but the storageHash property on the widget definition is different from that on the ' +
              'serialized widget loaded from storage. hash from storage: "' + savedWidgetDef.storageHash + '"' +
              ', hash from WDO: "' + widgetDefinition.storageHash + '"');
            continue;
          }

          // push instantiated widget to result array
          result.push(savedWidgetDef);
        }

        return result;
      },

      _handleAsyncLoad: function(promise) {
        var self = this;
        var deferred = $q.defer();
        promise.then(
          // success
          function(res) {
            var result = self._handleSyncLoad(res);
            if (result) {
              deferred.resolve(result);
            } else {
              deferred.reject(result);
            }
          },
          // failure
          function(res) {
            deferred.reject(res);
          }
        );

        return deferred.promise;
      }

    };
    return DashboardState;
  }]);
'use strict';

angular.module('ark-dashboard')
  .factory('ExpandToTabModel', function () {

    function ExpandToTabModel(Class, overrides) {
      var defaults = {
          title: 'Expanded Tab',
          name: Class.name,
          attrs: Class.attrs
       };

      overrides = overrides || {};
      angular.extend(this, angular.copy(defaults), overrides);
      this.containerStyle = { width: '100%' }; // default width
      this.contentStyle = {};
      this.updateContainerStyle(this.style);

      if (Class.templateUrl) {
        this.templateUrl = Class.templateUrl;
      } else if (Class.template) {
        this.template = Class.template;
      } else {
        var directive = Class.directive || Class.name;
        this.directive = directive;
      }
    }

    ExpandToTabModel.prototype = {
      updateContainerStyle: function (style) {
        angular.extend(this.containerStyle, style);
      }
    };

    return ExpandToTabModel;
  });
'use strict';

angular.module('ark-dashboard')
  .factory('LayoutMenuObject', function () {
    function LayoutMenuObject(customList, customActions) {

      var defaultList;
      var defaultActions;
      var layoutList = {};
      layoutList.list = {};
      layoutList.actions = {};

      var menuList = {
        'customLayoutMenuList':[
          {
            'menuLocalizedTitle':'Rename',
            'menuIcon':'icon-24-graph-edit',
            'menuOptionKey':'renameLayout'
          },
          //{
          //  'menuLocalizedTitle':'Reset To Default Dashboard',
          //  'menuIcon':'icon-reset',
          //  'menuOptionKey':'resetWidgetsToDefault'
          //},
          //{
          //  'menuLocalizedTitle':'Set as Default Dashboard',
          //  'menuIcon':'icon-agent-status-ready',
          //  'menuOptionKey':'saveDashboard'
          //},
          {
            'menuLocalizedTitle':'Share',
            'menuIcon':'icon-share',
            'menuOptionKey':'shareLayout'
          },
          {
            'menuLocalizedTitle':'Delete',
            'menuIcon':'icon-trash',
            'menuOptionKey':'removeLayout',
            'requireConfirmPopup': true,
            'tooltip': 'Delete this dashboard',
            'confirmMessage': 'Are you sure to delete this dashboard?'
          }

        ],

        'customLayoutMenuActions':['renameLayout','resetWidgetsToDefault','saveDashboard', 'removeLayout', 'shareLayout'],
      };

      defaultList = menuList.customLayoutMenuList;
      defaultActions = menuList.customLayoutMenuActions;

      var overrideList = customList || {};
      var overrideActions = customActions || {};

      layoutList.list = $.merge($.merge([], defaultList), overrideList);
      layoutList.actions = $.merge($.merge([], defaultActions), overrideActions);

      return layoutList;
    }
    return LayoutMenuObject;
  });

'use strict';

angular.module('ark-dashboard')
  .factory('LayoutStorage', function() {

    var noopStorage = {
      setItem: function() {

      },
      getItem: function() {

      },
      removeItem: function() {

      }
    };


    function LayoutStorage(options) {

      var defaults = {
        storage: noopStorage,
        storageHash: '',
        stringifyStorage: true
      };

      angular.extend(defaults, options);
      angular.extend(options, defaults);

      this.id = options.storageId;
      this.storage = options.storage;
      this.storageHash = options.storageHash;
      this.stringifyStorage = options.stringifyStorage;
      this.widgetDefinitions = options.widgetDefinitions;
      this.defaultLayouts = options.defaultLayouts;
      this.lockDefaultLayouts = options.lockDefaultLayouts;
      this.widgetButtons = options.widgetButtons;
      this.customWidgetDropdownMenu = options.customWidgetDropdownMenu;
      this.customWidgetDropdownActions = options.customWidgetDropdownActions;
      this.customLayoutDropdownMenu = options.customLayoutDropdownMenu;
      this.customLayoutDropdownActions = options.customLayoutDropdownActions;
      this.explicitSave = options.explicitSave;
      this.defaultWidgets = options.defaultWidgets;
      this.settingsModalOptions = options.settingsModalOptions;
      this.options = options;
      this.options.unsavedChangeCount = 0;

      this.layouts = [];
      this.states = {};
      this.load();
      this._ensureActiveLayout();
    }

    LayoutStorage.prototype = {

      add: function(layouts) {
        if (!angular.isArray(layouts)) {
          layouts = [layouts];
        }
        var self = this;
        angular.forEach(layouts, function(layout) {
          layout.dashboard = layout.dashboard || {};
          layout.dashboard.storage = self;
          layout.dashboard.storageId = layout.id = self._getLayoutId.call(self,layout);
          layout.dashboard.widgetDefinitions = self.widgetDefinitions;
          layout.dashboard.stringifyStorage = false;
          layout.dashboard.defaultWidgets = layout.defaultWidgets || self.defaultWidgets;
          layout.dashboard.widgetButtons = self.widgetButtons;
          layout.dashboard.explicitSave = self.explicitSave;
          layout.dashboard.settingsModalOptions = self.settingsModalOptions;
          layout.dashboard.customWidgetDropdownMenu = self.customWidgetDropdownMenu;
          layout.dashboard.customWidgetDropdownActions = self.customWidgetDropdownActions;
          self.layouts.push(layout);
        });
      },

      remove: function(layout) {
        var index = this.layouts.indexOf(layout);
        if (index >= 0) {
          this.layouts.splice(index, 1);
          delete this.states[layout.id];

          // check for active
          if (layout.active && this.layouts.length) {
            var nextActive = index > 0 ? index - 1 : 0;
            this.layouts[nextActive].active = true;
          }
        }
      },

      save: function() {

        var state = {
          layouts: this._serializeLayouts(),
          states: this.states,
          storageHash: this.storageHash
        };

        if (this.stringifyStorage) {
          state = JSON.stringify(state);
        }

        this.storage.setItem(this.id, state);
        this.options.unsavedChangeCount = 0;
      },

      load: function() {

        var serialized = this.storage.getItem(this.id);

        this.clear();

        if (serialized) {
          // check for promise
          if (angular.isObject(serialized) && angular.isFunction(serialized.then)) {
            this._handleAsyncLoad(serialized);
          } else {
            this._handleSyncLoad(serialized);
          }
        } else {
          this._addDefaultLayouts();
        }
      },

      clear: function() {
        this.layouts = [];
        this.states = {};
      },

      setItem: function(id, value) {
        this.states[id] = value;
        this.save();
      },

      getItem: function(id) {
        return this.states[id];
      },

      removeItem: function(id) {
        delete this.states[id];
        this.save();
      },

      getActiveLayout: function() {
        var len = this.layouts.length;
        for (var i = 0; i < len; i++) {
          var layout = this.layouts[i];
          if (layout.active) {
            return layout;
          }
        }
        return false;
      },

      _addDefaultLayouts: function() {
        var self = this;
        var defaults = this.lockDefaultLayouts ? { locked: true } : {};
        angular.forEach(this.defaultLayouts, function(layout) {
          self.add(angular.extend(_.clone(defaults), layout));
        });
      },

      _serializeLayouts: function() {
        var result = [];
        angular.forEach(this.layouts, function(l) {
          result.push({
            title: l.title,
            id: l.id,
            active: l.active,
            locked: l.locked,
            type: l.type,
            defaultWidgets: l.dashboard.defaultWidgets
          });
        });
        return result;
      },

      _handleSyncLoad: function(serialized) {

        var deserialized;

        if (this.stringifyStorage) {
          try {

            deserialized = JSON.parse(serialized);

          } catch (e) {
            this._addDefaultLayouts();
            return;
          }
        } else {

          deserialized = serialized;

        }

        if (this.storageHash !== deserialized.storageHash) {
          this._addDefaultLayouts();
          return;
        }
        this.states = deserialized.states;
        this.add(deserialized.layouts);
      },

      _handleAsyncLoad: function(promise) {
        var self = this;
        promise.then(
          angular.bind(self, this._handleSyncLoad),
          angular.bind(self, this._addDefaultLayouts)
        );
      },

      _ensureActiveLayout: function() {
        for (var i = 0; i < this.layouts.length; i++) {
          var layout = this.layouts[i];
          if (layout.active) {
            return;
          }
        }
        if (this.layouts[0]) {
          this.layouts[0].active = true;
        }
      },

      _getLayoutId: function(layout) {
        if (layout.id) {
          return layout.id;
        }
        var max = 0;
        for (var i = 0; i < this.layouts.length; i++) {
          var id = this.layouts[i].id;
          max = Math.max(max, id * 1);
        }
        return max + 1;
      }

    };
    return LayoutStorage;
  });

'use strict';

angular.module('ark-dashboard')
  .factory('WidgetDataModel', function () {
    function WidgetDataModel() {
    }

    WidgetDataModel.prototype = {
      setup: function (widget, scope) {
        this.dataAttrName = widget.dataAttrName;
        this.dataModelOptions = widget.dataModelOptions;
        this.widgetScope = scope;
      },

      updateScope: function (data) {
        this.widgetScope.widgetData = data;
      },

      init: function () {
        // to be overridden by subclasses
      },

      destroy: function () {
        // to be overridden by subclasses
      }
    };

    return WidgetDataModel;
  });
'use strict';

angular.module('ark-dashboard')
  .factory('WidgetDefCollection', function () {
    function WidgetDefCollection(widgetDefs) {
      this.push.apply(this, widgetDefs);

      // build (name -> widget definition) map for widget lookup by name
      var map = {};
      _.each(widgetDefs, function (widgetDef) {
        map[widgetDef.name] = widgetDef;
      });
      this.map = map;
    }

    WidgetDefCollection.prototype = Object.create(Array.prototype);

    WidgetDefCollection.prototype.getByName = function (name) {
      return this.map[name];
    };

    return WidgetDefCollection;
  });
'use strict';

angular.module('ark-dashboard')
  .factory('WidgetModel', ['$log', function ($log) {
    // constructor for widget model instances
    function WidgetModel(Class, overrides) {
      var defaults = {
          title: 'Widget',
          name: Class.name,
          attrs: Class.attrs,
          dataAttrName: Class.dataAttrName,
          dataModelType: Class.dataModelType,
          dataModelArgs: Class.dataModelArgs, // used in data model constructor, not serialized
          //AW Need deep copy of options to support widget options editing
          dataModelOptions: Class.dataModelOptions,
          settingsModalOptions: Class.settingsModalOptions,
          onSettingsClose: Class.onSettingsClose,
          onSettingsDismiss: Class.onSettingsDismiss,
          style: Class.style || {},
          size: Class.size || {},
          enableVerticalResize: (Class.enableVerticalResize === false) ? false : true
        };

      overrides = overrides || {};
      angular.extend(this, angular.copy(defaults), overrides);
      this.containerStyle = { width: '33%' }; // default width
      this.contentStyle = {};
      this.updateContainerStyle(this.style);

      if (Class.templateUrl) {
        this.templateUrl = Class.templateUrl;
      } else if (Class.template) {
        this.template = Class.template;
      } else {
        var directive = Class.directive || Class.name;
        this.directive = directive;
      }

      if (this.size && _.has(this.size, 'height')) {
        this.setHeight(this.size.height);
      }

      if (this.style && _.has(this.style, 'width')) { //TODO deprecate style attribute
        this.setWidth(this.style.width);
      }

      if (this.size && _.has(this.size, 'width')) {
        this.setWidth(this.size.width);
      }
    }

    WidgetModel.prototype = {
      // sets the width (and widthUnits)
      setWidth: function (width, units) {
        width = width.toString();
        units = units || width.replace(/^[-\.\d]+/, '') || '%';

        this.widthUnits = units;
        width = parseFloat(width);

        if (width < 0 || isNaN(width)) {
          $log.warn('malhar-angular-dashboard: setWidth was called when width was ' + width);
          return false;
        }

        if (units === '%') {
          width = Math.min(100, width);
          width = Math.max(0, width);
        }

        this.containerStyle.width = width + '' + units;

        this.updateSize(this.containerStyle);

        return true;
      },

      setHeight: function (height) {
        this.contentStyle.height = height;
        this.updateSize(this.contentStyle);
      },

      setStyle: function (style) {
        this.style = style;
        this.updateContainerStyle(style);
      },

      updateSize: function (size) {
        angular.extend(this.size, size);
      },

      getWidget: function () {
        return this;
      },

      updateContainerStyle: function (style) {
        angular.extend(this.containerStyle, style);
      }
    };

    return WidgetModel;
  }]);
'use strict';

angular.module('ark-dashboard')
  .controller('DashboardWidgetCtrl', ['$scope', '$element', '$compile', function($scope, $element, $compile) {

      $scope.status = {
        isopen: false
      };

      // Fills "container" with compiled view
      $scope.makeTemplateString = function() {

        var widget = $scope.widget;

        // First, build template string
        var templateString = '';

        if (widget.templateUrl) {

          // Use ng-include for templateUrl
          templateString = '<div ng-include="\'' + widget.templateUrl + '\'"></div>';

        } else if (widget.template) {

          // Direct string template
          templateString = widget.template;

        } else {

          // Assume attribute directive
          templateString = '<div ' + widget.directive;

          // Check if data attribute was specified
          if (widget.dataAttrName) {
            widget.attrs = widget.attrs || {};
            widget.attrs[widget.dataAttrName] = 'widgetData';
          }

          // Check for specified attributes
          if (widget.attrs) {

            // First check directive name attr
            if (widget.attrs[widget.directive]) {
              templateString += '="' + widget.attrs[widget.directive] + '"';
            }

            // Add attributes
            _.each(widget.attrs, function(value, attr) {

              // make sure we aren't reusing directive attr
              if (attr !== widget.directive) {
                templateString += ' ' + attr + '="' + value + '"';
              }

            });
          }
          templateString += '></div>';
        }
        return templateString;
      };

      // saves whatever is in the title input as the new title
      $scope.saveTitleEdit = function(widget) {
        widget.editingTitle = false;
        $scope.$emit('widgetChanged', widget);
      };

      $scope.compileTemplate = function() {
        //var container = $scope.findWidgetContainer($element);
        var container = $element; // Not sure why it finds '.widget-content' again. Use the element itself.
        if (!container.parents('.widget-content').length) { //Exclude not in case of '.widget-content' placeholder
          return;
        }
        var templateString = $scope.makeTemplateString();
        var widgetElement = angular.element(templateString);

        container.empty();
        container.append(widgetElement);
        $compile(widgetElement)($scope);
      };

      $scope.findWidgetContainer = function(element) {
        // widget placeholder is the first (and only) child of .widget-content
        return element.find('.widget-content');
      };
    }
  ]);
'use strict';

angular.module('ark-dashboard')
  .controller('renameModalCtrl', ['$scope', '$modalInstance', 'title', 'type', function ($scope, $modalInstance, title, type) {

    // set up result object
    $scope.title = title || {};
    if(type === 'Dashboard') {
      $scope.type = 'Dashboard';
    } else if (type  === 'Widget') {
      $scope.type = 'Widget';
    }

    $scope.ok = function () {
      $modalInstance.close($scope.title);
    };

    $scope.cancel = function () {
      $modalInstance.dismiss();
    };
  }]);

'use strict';

angular.module('ark-dashboard')
  .controller('SaveChangesModalCtrl', ['$scope', '$modalInstance', 'layout', function ($scope, $modalInstance, layout) {

    // add layout to scope
    $scope.layout = layout;

    $scope.ok = function () {
      $modalInstance.close();
    };

    $scope.cancel = function () {
      $modalInstance.dismiss();
    };
  }]);
(function(angular) {

  'use strict';

  angular.module('gridster', [])

  .constant('gridsterConfig', {
    columns: 6, // number of columns in the grid
    pushing: true, // whether to push other items out of the way
    floating: true, // whether to automatically float items up so they stack
    swapping: false, // whether or not to have items switch places instead of push down if they are the same size
    width: 'auto', // width of the grid. "auto" will expand the grid to its parent container
    colWidth: 'auto', // width of grid columns. "auto" will divide the width of the grid evenly among the columns
    rowHeight: 'match', // height of grid rows. 'match' will make it the same as the column width, a numeric value will be interpreted as pixels, '/2' is half the column width, '*5' is five times the column width, etc.
    margins: [10, 10], // margins in between grid items
    outerMargin: true,
    isMobile: false, // toggle mobile view
    mobileBreakPoint: 600, // width threshold to toggle mobile mode
    mobileModeEnabled: true, // whether or not to toggle mobile mode when screen width is less than mobileBreakPoint
    minColumns: 1, // minimum amount of columns the grid can scale down to
    minRows: 1, // minimum amount of rows to show if the grid is empty
    maxRows: 100, // maximum amount of rows in the grid
    defaultSizeX: 2, // default width of an item in columns
    defaultSizeY: 1, // default height of an item in rows
    minSizeX: 1, // minimum column width of an item
    maxSizeX: null, // maximum column width of an item
    minSizeY: 1, // minumum row height of an item
    maxSizeY: null, // maximum row height of an item
    saveGridItemCalculatedHeightInMobile: false, // grid item height in mobile display. true- to use the calculated height by sizeY given
    resizable: { // options to pass to resizable handler
      enabled: true,
      handles: ['s', 'e', 'n', 'w', 'se', 'ne', 'sw', 'nw']
    },
    draggable: { // options to pass to draggable handler
      enabled: true,
      scrollSensitivity: 20, // Distance in pixels from the edge of the viewport after which the viewport should scroll, relative to pointer
      scrollSpeed: 15 // Speed at which the window should scroll once the mouse pointer gets within scrollSensitivity distance
    }
  })

  .controller('GridsterCtrl', ['gridsterConfig', '$timeout',
    function(gridsterConfig, $timeout) {

      var gridster = this;

      /**
       * Create options from gridsterConfig constant
       */
      angular.extend(this, gridsterConfig);

      this.resizable = angular.extend({}, gridsterConfig.resizable || {});
      this.draggable = angular.extend({}, gridsterConfig.draggable || {});

      var flag = false;
      this.layoutChanged = function() {
        if (flag) {
          return;
        }
        flag = true;
        $timeout(function() {
          flag = false;
          if (gridster.loaded) {
            gridster.floatItemsUp();
          }
          gridster.updateHeight(gridster.movingItem ? gridster.movingItem.sizeY : 0);
        });
      };

      /**
       * A positional array of the items in the grid
       */
      this.grid = [];

      /**
       * Clean up after yourself
       */
      this.destroy = function() {
        if (this.grid) {
          this.grid.length = 0;
          this.grid = null;
        }
      };

      /**
       * Overrides default options
       *
       * @param {object} options The options to override
       */
      this.setOptions = function(options) {
        if (!options) {
          return;
        }

        options = angular.extend({}, options);

        // all this to avoid using jQuery...
        if (options.draggable) {
          angular.extend(this.draggable, options.draggable);
          delete(options.draggable);
        }
        if (options.resizable) {
          angular.extend(this.resizable, options.resizable);
          delete(options.resizable);
        }

        angular.extend(this, options);

        if (!this.margins || this.margins.length !== 2) {
          this.margins = [0, 0];
        } else {
          for (var x = 0, l = this.margins.length; x < l; ++x) {
            this.margins[x] = parseInt(this.margins[x], 10);
            if (isNaN(this.margins[x])) {
              this.margins[x] = 0;
            }
          }
        }
      };

      /**
       * Check if item can occupy a specified position in the grid
       *
       * @param {object} item The item in question
       * @param {number} row The row index
       * @param {number} column The column index
       * @returns {boolean} True if if item fits
       */
      this.canItemOccupy = function(item, row, column) {
        return row > -1 && column > -1 && item.sizeX + column <= this.columns && item.sizeY + row <= this.maxRows;
      };

      /**
       * Set the item in the first suitable position
       *
       * @param {object} item The item to insert
       */
      this.autoSetItemPosition = function(item) {
        // walk through each row and column looking for a place it will fit
        for (var rowIndex = 0; rowIndex < this.maxRows; ++rowIndex) {
          for (var colIndex = 0; colIndex < this.columns; ++colIndex) {
            // only insert if position is not already taken and it can fit
            var items = this.getItems(rowIndex, colIndex, item.sizeX, item.sizeY, item);
            if (items.length === 0 && this.canItemOccupy(item, rowIndex, colIndex)) {
              this.putItem(item, rowIndex, colIndex);
              return;
            }
          }
        }
        // throw new Error('Unable to place item!');
        console.log('Unable to place item!');
      };

      /**
       * Gets items at a specific coordinate
       *
       * @param {number} row
       * @param {number} column
       * @param {number} sizeX
       * @param {number} sizeY
       * @param {array} excludeItems An array of items to exclude from selection
       * @returns {array} Items that match the criteria
       */
      this.getItems = function(row, column, sizeX, sizeY, excludeItems) {
        var items = [];
        if (!sizeX || !sizeY) {
          sizeX = sizeY = 1;
        }
        if (excludeItems && !(excludeItems instanceof Array)) {
          excludeItems = [excludeItems];
        }
        for (var h = 0; h < sizeY; ++h) {
          for (var w = 0; w < sizeX; ++w) {
            var item = this.getItem(row + h, column + w, excludeItems);
            if (item && (!excludeItems || excludeItems.indexOf(item) === -1) && items.indexOf(item) === -1) {
              items.push(item);
            }
          }
        }
        return items;
      };

      this.getBoundingBox = function(items) {

        if (items.length === 0) {
          return null;
        }
        if (items.length === 1) {
          return {
            row: items[0].row,
            col: items[0].col,
            sizeY: items[0].sizeY,
            sizeX: items[0].sizeX
          };
        }

        var maxRow = 0;
        var maxCol = 0;
        var minRow = 9999;
        var minCol = 9999;

        for (var i = 0, l = items.length; i < l; ++i) {
          var item = items[i];
          minRow = Math.min(item.row, minRow);
          minCol = Math.min(item.col, minCol);
          maxRow = Math.max(item.row + item.sizeY, maxRow);
          maxCol = Math.max(item.col + item.sizeX, maxCol);
        }

        return {
          row: minRow,
          col: minCol,
          sizeY: maxRow - minRow,
          sizeX: maxCol - minCol
        };
      };


      /**
       * Removes an item from the grid
       *
       * @param {object} item
       */
      this.removeItem = function(item) {
        for (var rowIndex = 0, l = this.grid.length; rowIndex < l; ++rowIndex) {
          var columns = this.grid[rowIndex];
          if (!columns) {
            continue;
          }
          var index = columns.indexOf(item);
          if (index !== -1) {
            columns[index] = null;
            break;
          }
        }
        this.layoutChanged();
      };

      /**
       * Returns the item at a specified coordinate
       *
       * @param {number} row
       * @param {number} column
       * @param {array} excludeitems Items to exclude from selection
       * @returns {object} The matched item or null
       */
      this.getItem = function(row, column, excludeItems) {
        if (excludeItems && !(excludeItems instanceof Array)) {
          excludeItems = [excludeItems];
        }
        var sizeY = 1;
        while (row > -1) {
          var sizeX = 1,
            col = column;
          while (col > -1) {
            var items = this.grid[row];
            if (items) {
              var item = items[col];
              if (item && (!excludeItems || excludeItems.indexOf(item) === -1) && item.sizeX >= sizeX && item.sizeY >= sizeY) {
                return item;
              }
            }
            ++sizeX;
            --col;
          }
          --row;
          ++sizeY;
        }
        return null;
      };

      /**
       * Insert an array of items into the grid
       *
       * @param {array} items An array of items to insert
       */
      this.putItems = function(items) {
        for (var i = 0, l = items.length; i < l; ++i) {
          this.putItem(items[i]);
        }
      };

      /**
       * Insert a single item into the grid
       *
       * @param {object} item The item to insert
       * @param {number} row (Optional) Specifies the items row index
       * @param {number} column (Optional) Specifies the items column index
       * @param {array} ignoreItems
       */
      this.putItem = function(item, row, column, ignoreItems) {
        if (typeof row === 'undefined' || row === null) {
          row = item.row;
          column = item.col;
          if (typeof row === 'undefined' || row === null) {
            this.autoSetItemPosition(item);
            return;
          }
        }
        if (!this.canItemOccupy(item, row, column)) {
          column = Math.min(this.columns - item.sizeX, Math.max(0, column));
          row = Math.min(this.maxRows - item.sizeY, Math.max(0, row));
        }

        if (item.oldRow !== null && typeof item.oldRow !== 'undefined') {
          var samePosition = item.oldRow === row && item.oldColumn === column;
          var inGrid = this.grid[row] && this.grid[row][column] === item;
          if (samePosition && inGrid) {
            item.row = row;
            item.col = column;
            return;
          } else {
            // remove from old position
            var oldRow = this.grid[item.oldRow];
            if (oldRow && oldRow[item.oldColumn] === item) {
              delete oldRow[item.oldColumn];
            }
          }
        }

        item.oldRow = item.row = row;
        item.oldColumn = item.col = column;

        this.moveOverlappingItems(item, ignoreItems);

        if (!this.grid[row]) {
          this.grid[row] = [];
        }
        this.grid[row][column] = item;

        if (this.movingItem === item) {
          this.floatItemUp(item);
        }
        this.layoutChanged();
      };

      /**
       * Trade row and column if item1 with item2
       *
       * @param {object} item1
       * @param {object} item2
       */
      this.swapItems = function(item1, item2) {
        this.grid[item1.row][item1.col] = item2;
        this.grid[item2.row][item2.col] = item1;

        var item1Row = item1.row;
        var item1Col = item1.col;
        item1.row = item2.row;
        item1.col = item2.col;
        item2.row = item1Row;
        item2.col = item1Col;
      };

      /**
       * Prevents items from being overlapped
       *
       * @param {object} item The item that should remain
       * @param {array} ignoreItems
       */
      this.moveOverlappingItems = function(item, ignoreItems) {
        if (ignoreItems) {
          if (ignoreItems.indexOf(item) === -1) {
            ignoreItems = ignoreItems.slice(0);
            ignoreItems.push(item);
          }
        } else {
          ignoreItems = [item];
        }
        var overlappingItems = this.getItems(
          item.row,
          item.col,
          item.sizeX,
          item.sizeY,
          ignoreItems
        );
        this.moveItemsDown(overlappingItems, item.row + item.sizeY, ignoreItems);
      };

      /**
       * Moves an array of items to a specified row
       *
       * @param {array} items The items to move
       * @param {number} newRow The target row
       * @param {array} ignoreItems
       */
      this.moveItemsDown = function(items, newRow, ignoreItems) {
        if (!items || items.length === 0) {
          return;
        }
        items.sort(function(a, b) {
          return a.row - b.row;
        });
        ignoreItems = ignoreItems ? ignoreItems.slice(0) : [];
        var topRows = {},
          item, i, l;
        // calculate the top rows in each column
        for (i = 0, l = items.length; i < l; ++i) {
          item = items[i];
          var topRow = topRows[item.col];
          if (typeof topRow === 'undefined' || item.row < topRow) {
            topRows[item.col] = item.row;
          }
        }
        // move each item down from the top row in its column to the row
        for (i = 0, l = items.length; i < l; ++i) {
          item = items[i];
          var rowsToMove = newRow - topRows[item.col];
          this.moveItemDown(item, item.row + rowsToMove, ignoreItems);
          ignoreItems.push(item);
        }
      };

      this.moveItemDown = function(item, newRow, ignoreItems) {
        if (item.row >= newRow) {
          return;
        }
        while (item.row < newRow) {
          ++item.row;
          this.moveOverlappingItems(item, ignoreItems);
        }
        this.putItem(item, item.row, item.col, ignoreItems);
      };

      /**
       * Moves all items up as much as possible
       */
      this.floatItemsUp = function() {
        if (this.floating === false) {
          return;
        }
        if (this.grid) {
          for (var rowIndex = 0, l = this.grid.length; rowIndex < l; ++rowIndex) {
            var columns = this.grid[rowIndex];
            if (!columns) {
              continue;
            }
            for (var colIndex = 0, len = columns.length; colIndex < len; ++colIndex) {
              var item = columns[colIndex];
              if (item) {
                this.floatItemUp(item);
              }
            }
          }
        }
      };

      /**
       * Float an item up to the most suitable row
       *
       * @param {object} item The item to move
       */
      this.floatItemUp = function(item) {
        if (this.floating === false) {
          return;
        }
        var colIndex = item.col,
          sizeY = item.sizeY,
          sizeX = item.sizeX,
          bestRow = null,
          bestColumn = null,
          rowIndex = item.row - 1;

        while (rowIndex > -1) {
          var items = this.getItems(rowIndex, colIndex, sizeX, sizeY, item);
          if (items.length !== 0) {
            break;
          }
          bestRow = rowIndex;
          bestColumn = colIndex;
          --rowIndex;
        }
        if (bestRow !== null) {
          this.putItem(item, bestRow, bestColumn);
        }
      };

      /**
       * Update gridsters height
       *
       * @param {number} plus (Optional) Additional height to add
       */
      this.updateHeight = function(plus) {
        if (this.grid) {
          var maxHeight = this.minRows;
          plus = plus || 0;

          for (var rowIndex = this.grid.length; rowIndex >= 0; --rowIndex) {
            var columns = this.grid[rowIndex];
            if (!columns) {
              continue;
            }
            for (var colIndex = 0, len = columns.length; colIndex < len; ++colIndex) {
              if (columns[colIndex]) {
                maxHeight = Math.max(maxHeight, rowIndex + plus + columns[colIndex].sizeY);
              }
            }
          }
          this.gridHeight = this.maxRows - maxHeight > 0 ? Math.min(this.maxRows, maxHeight) : Math.max(this.maxRows, maxHeight);
        }
      };

      /**
       * Returns the number of rows that will fit in given amount of pixels
       *
       * @param {number} pixels
       * @param {boolean} ceilOrFloor (Optional) Determines rounding method
       */
      this.pixelsToRows = function(pixels, ceilOrFloor) {
        if (ceilOrFloor === true) {
          return Math.ceil(pixels / this.curRowHeight);
        } else if (ceilOrFloor === false) {
          return Math.floor(pixels / this.curRowHeight);
        }

        return Math.round(pixels / this.curRowHeight);
      };

      /**
       * Returns the number of columns that will fit in a given amount of pixels
       *
       * @param {number} pixels
       * @param {boolean} ceilOrFloor (Optional) Determines rounding method
       * @returns {number} The number of columns
       */
      this.pixelsToColumns = function(pixels, ceilOrFloor) {
        if (ceilOrFloor === true) {
          return Math.ceil(pixels / this.curColWidth);
        } else if (ceilOrFloor === false) {
          return Math.floor(pixels / this.curColWidth);
        }

        return Math.round(pixels / this.curColWidth);
      };

      // unified input handling
      // adopted from a msdn blogs sample
      this.unifiedInput = function(target, startEvent, moveEvent, endEvent) {
        var lastXYById = {};

        //  Opera doesn't have Object.keys so we use this wrapper
        var numberOfKeys = function(theObject) {
          if (Object.keys) {
            return Object.keys(theObject).length;
          }

          var n = 0,
            key;
          for (key in theObject) {
            ++n;
          }

          return n;
        };

        //  this calculates the delta needed to convert pageX/Y to offsetX/Y because offsetX/Y don't exist in the TouchEvent object or in Firefox's MouseEvent object
        var computeDocumentToElementDelta = function(theElement) {
          var elementLeft = 0;
          var elementTop = 0;
          var oldIEUserAgent = navigator.userAgent.match(/\bMSIE\b/);

          for (var offsetElement = theElement; offsetElement !== null; offsetElement = offsetElement.offsetParent) {
            //  the following is a major hack for versions of IE less than 8 to avoid an apparent problem on the IEBlog with double-counting the offsets
            //  this may not be a general solution to IE7's problem with offsetLeft/offsetParent
            if (oldIEUserAgent &&
              (!document.documentMode || document.documentMode < 8) &&
              offsetElement.currentStyle.position === 'relative' && offsetElement.offsetParent && offsetElement.offsetParent.currentStyle.position === 'relative' && offsetElement.offsetLeft === offsetElement.offsetParent.offsetLeft) {
              // add only the top
              elementTop += offsetElement.offsetTop;
            } else {
              elementLeft += offsetElement.offsetLeft;
              elementTop += offsetElement.offsetTop;
            }
          }

          return {
            x: elementLeft,
            y: elementTop
          };
        };

        //  cache the delta from the document to our event target (reinitialized each mousedown/MSPointerDown/touchstart)
        var documentToTargetDelta = computeDocumentToElementDelta(target);

        //  common event handler for the mouse/pointer/touch models and their down/start, move, up/end, and cancel events
        var doEvent = function(theEvtObj) {

          if (theEvtObj.type === 'mousemove' && numberOfKeys(lastXYById) === 0) {
            return;
          }

          var prevent = true;

          var pointerList = theEvtObj.changedTouches ? theEvtObj.changedTouches : [theEvtObj];
          for (var i = 0; i < pointerList.length; ++i) {
            var pointerObj = pointerList[i];
            var pointerId = (typeof pointerObj.identifier !== 'undefined') ? pointerObj.identifier : (typeof pointerObj.pointerId !== 'undefined') ? pointerObj.pointerId : 1;

            //  use the pageX/Y coordinates to compute target-relative coordinates when we have them (in ie < 9, we need to do a little work to put them there)
            if (typeof pointerObj.pageX === 'undefined') {
              //  initialize assuming our source element is our target
              pointerObj.pageX = pointerObj.offsetX + documentToTargetDelta.x;
              pointerObj.pageY = pointerObj.offsetY + documentToTargetDelta.y;

              if (pointerObj.srcElement.offsetParent === target && document.documentMode && document.documentMode === 8 && pointerObj.type === 'mousedown') {
                //  source element is a child piece of VML, we're in IE8, and we've not called setCapture yet - add the origin of the source element
                pointerObj.pageX += pointerObj.srcElement.offsetLeft;
                pointerObj.pageY += pointerObj.srcElement.offsetTop;
              } else if (pointerObj.srcElement !== target && !document.documentMode || document.documentMode < 8) {
                //  source element isn't the target (most likely it's a child piece of VML) and we're in a version of IE before IE8 -
                //  the offsetX/Y values are unpredictable so use the clientX/Y values and adjust by the scroll offsets of its parents
                //  to get the document-relative coordinates (the same as pageX/Y)
                var sx = -2,
                  sy = -2; // adjust for old IE's 2-pixel border
                for (var scrollElement = pointerObj.srcElement; scrollElement !== null; scrollElement = scrollElement.parentNode) {
                  sx += scrollElement.scrollLeft ? scrollElement.scrollLeft : 0;
                  sy += scrollElement.scrollTop ? scrollElement.scrollTop : 0;
                }

                pointerObj.pageX = pointerObj.clientX + sx;
                pointerObj.pageY = pointerObj.clientY + sy;
              }
            }


            var pageX = pointerObj.pageX;
            var pageY = pointerObj.pageY;

            if (theEvtObj.type.match(/(start|down)$/i)) {
              //  clause for processing MSPointerDown, touchstart, and mousedown

              //  refresh the document-to-target delta on start in case the target has moved relative to document
              documentToTargetDelta = computeDocumentToElementDelta(target);

              //  protect against failing to get an up or end on this pointerId
              if (lastXYById[pointerId]) {
                if (endEvent) {
                  endEvent({
                    target: theEvtObj.target,
                    which: theEvtObj.which,
                    pointerId: pointerId,
                    pageX: pageX,
                    pageY: pageY
                  });
                }

                delete lastXYById[pointerId];
              }

              if (startEvent) {
                if (prevent) {
                  prevent = startEvent({
                    target: theEvtObj.target,
                    which: theEvtObj.which,
                    pointerId: pointerId,
                    pageX: pageX,
                    pageY: pageY
                  });
                }
              }

              //  init last page positions for this pointer
              lastXYById[pointerId] = {
                x: pageX,
                y: pageY
              };

              // IE pointer model
              if (target.msSetPointerCapture) {
                target.msSetPointerCapture(pointerId);
              } else if (theEvtObj.type === 'mousedown' && numberOfKeys(lastXYById) === 1) {
                if (useSetReleaseCapture) {
                  target.setCapture(true);
                } else {
                  document.addEventListener('mousemove', doEvent, false);
                  document.addEventListener('mouseup', doEvent, false);
                }
              }
            } else if (theEvtObj.type.match(/move$/i)) {
              //  clause handles mousemove, MSPointerMove, and touchmove

              if (lastXYById[pointerId] && !(lastXYById[pointerId].x === pageX && lastXYById[pointerId].y === pageY)) {
                //  only extend if the pointer is down and it's not the same as the last point

                if (moveEvent && prevent) {
                  prevent = moveEvent({
                    target: theEvtObj.target,
                    which: theEvtObj.which,
                    pointerId: pointerId,
                    pageX: pageX,
                    pageY: pageY
                  });
                }

                //  update last page positions for this pointer
                lastXYById[pointerId].x = pageX;
                lastXYById[pointerId].y = pageY;
              }
            } else if (lastXYById[pointerId] && theEvtObj.type.match(/(up|end|cancel)$/i)) {
              //  clause handles up/end/cancel

              if (endEvent && prevent) {
                prevent = endEvent({
                  target: theEvtObj.target,
                  which: theEvtObj.which,
                  pointerId: pointerId,
                  pageX: pageX,
                  pageY: pageY
                });
              }

              //  delete last page positions for this pointer
              delete lastXYById[pointerId];

              //  in the Microsoft pointer model, release the capture for this pointer
              //  in the mouse model, release the capture or remove document-level event handlers if there are no down points
              //  nothing is required for the iOS touch model because capture is implied on touchstart
              if (target.msReleasePointerCapture) {
                target.msReleasePointerCapture(pointerId);
              } else if (theEvtObj.type === 'mouseup' && numberOfKeys(lastXYById) === 0) {
                if (useSetReleaseCapture) {
                  target.releaseCapture();
                } else {
                  document.removeEventListener('mousemove', doEvent, false);
                  document.removeEventListener('mouseup', doEvent, false);
                }
              }
            }
          }

          if (prevent) {
            if (theEvtObj.preventDefault) {
              theEvtObj.preventDefault();
            }

            if (theEvtObj.preventManipulation) {
              theEvtObj.preventManipulation();
            }

            if (theEvtObj.preventMouseEvent) {
              theEvtObj.preventMouseEvent();
            }
          }
        };

        var useSetReleaseCapture = false;
        // saving the settings for contentZooming and touchaction before activation
        var contentZooming, msTouchAction;

        this.enable = function() {

          if (window.navigator.msPointerEnabled) {
            //  Microsoft pointer model
            target.addEventListener('MSPointerDown', doEvent, false);
            target.addEventListener('MSPointerMove', doEvent, false);
            target.addEventListener('MSPointerUp', doEvent, false);
            target.addEventListener('MSPointerCancel', doEvent, false);

            //  css way to prevent panning in our target area
            if (typeof target.style.msContentZooming !== 'undefined') {
              contentZooming = target.style.msContentZooming;
              target.style.msContentZooming = 'none';
            }

            //  new in Windows Consumer Preview: css way to prevent all built-in touch actions on our target
            //  without this, you cannot touch draw on the element because IE will intercept the touch events
            if (typeof target.style.msTouchAction !== 'undefined') {
              msTouchAction = target.style.msTouchAction;
              target.style.msTouchAction = 'none';
            }
          } else if (target.addEventListener) {
            //  iOS touch model
            target.addEventListener('touchstart', doEvent, false);
            target.addEventListener('touchmove', doEvent, false);
            target.addEventListener('touchend', doEvent, false);
            target.addEventListener('touchcancel', doEvent, false);

            //  mouse model
            target.addEventListener('mousedown', doEvent, false);

            //  mouse model with capture
            //  rejecting gecko because, unlike ie, firefox does not send events to target when the mouse is outside target
            if (target.setCapture && !window.navigator.userAgent.match(/\bGecko\b/)) {
              useSetReleaseCapture = true;

              target.addEventListener('mousemove', doEvent, false);
              target.addEventListener('mouseup', doEvent, false);
            }
          } else if (target.attachEvent && target.setCapture) {
            //  legacy IE mode - mouse with capture
            useSetReleaseCapture = true;
            target.attachEvent('onmousedown', function() {
              doEvent(window.event);
              window.event.returnValue = false;
              return false;
            });
            target.attachEvent('onmousemove', function() {
              doEvent(window.event);
              window.event.returnValue = false;
              return false;
            });
            target.attachEvent('onmouseup', function() {
              doEvent(window.event);
              window.event.returnValue = false;
              return false;
            });
          }
        };

        this.disable = function() {
          if (window.navigator.msPointerEnabled) {
            //  Microsoft pointer model
            target.removeEventListener('MSPointerDown', doEvent, false);
            target.removeEventListener('MSPointerMove', doEvent, false);
            target.removeEventListener('MSPointerUp', doEvent, false);
            target.removeEventListener('MSPointerCancel', doEvent, false);

            //  reset zooming to saved value
            if (contentZooming) {
              target.style.msContentZooming = contentZooming;
            }

            // reset touch action setting
            if (msTouchAction) {
              target.style.msTouchAction = msTouchAction;
            }
          } else if (target.removeEventListener) {
            //  iOS touch model
            target.removeEventListener('touchstart', doEvent, false);
            target.removeEventListener('touchmove', doEvent, false);
            target.removeEventListener('touchend', doEvent, false);
            target.removeEventListener('touchcancel', doEvent, false);

            //  mouse model
            target.removeEventListener('mousedown', doEvent, false);

            //  mouse model with capture
            //  rejecting gecko because, unlike ie, firefox does not send events to target when the mouse is outside target
            if (target.setCapture && !window.navigator.userAgent.match(/\bGecko\b/)) {
              useSetReleaseCapture = true;

              target.removeEventListener('mousemove', doEvent, false);
              target.removeEventListener('mouseup', doEvent, false);
            }
          } else if (target.detachEvent && target.setCapture) {
            //  legacy IE mode - mouse with capture
            useSetReleaseCapture = true;
            target.detachEvent('onmousedown');
            target.detachEvent('onmousemove');
            target.detachEvent('onmouseup');
          }
        };

        return this;
      };

    }
  ])

  /**
   * The gridster directive
   *
   * @param {object} $parse
   * @param {object} $timeout
   */
  .directive('gridster', ['$timeout', '$rootScope', '$window',
    function($timeout, $rootScope, $window) {
      return {
        restrict: 'EAC',
        // without transclude, some child items may lose their parent scope
        transclude: true,
        replace: true,
        template: '<div ng-class="gridsterClass()"><div ng-style="previewStyle()" class="gridster-item gridster-preview-holder"></div><div class="gridster-content" ng-transclude></div></div>',
        controller: 'GridsterCtrl',
        controllerAs: 'gridster',
        scope: {
          config: '=?gridster'
        },
        compile: function() {

          return function(scope, $elem, attrs, gridster) {
            gridster.loaded = false;

            scope.gridsterClass = function() {
              return {
                gridster: true,
                'gridster-desktop': !gridster.isMobile,
                'gridster-mobile': gridster.isMobile,
                'gridster-loaded': gridster.loaded
              };
            };

            /**
             * @returns {Object} style object for preview element
             */
            scope.previewStyle = function() {
              if (!gridster.movingItem) {
                return {
                  display: 'none'
                };
              }

              return {
                display: 'block',
                height: (gridster.movingItem.sizeY * gridster.curRowHeight - gridster.margins[0]) + 'px',
                width: (gridster.movingItem.sizeX * gridster.curColWidth - gridster.margins[1]) + 'px',
                top: (gridster.movingItem.row * gridster.curRowHeight + (gridster.outerMargin ? gridster.margins[0] : 0)) + 'px',
                left: (gridster.movingItem.col * gridster.curColWidth + (gridster.outerMargin ? gridster.margins[1] : 0)) + 'px'
              };
            };

            var refresh = function() {
              gridster.setOptions(scope.config);

              // resolve "auto" & "match" values
              if (gridster.width === 'auto') {
                gridster.curWidth = $elem[0].offsetWidth || parseInt($elem.css('width'), 10);
              } else {
                gridster.curWidth = gridster.width;
              }

              if (gridster.colWidth === 'auto') {
                gridster.curColWidth = (gridster.curWidth + (gridster.outerMargin ? -gridster.margins[1] : gridster.margins[1])) / gridster.columns;
              } else {
                gridster.curColWidth = gridster.colWidth;
                // Calculate the number of columns based on the current gridster container width and custom-specified column width
                gridster.columns = parseInt(gridster.curWidth / gridster.colWidth, 10);
              }

              gridster.curRowHeight = gridster.rowHeight;
              if (typeof gridster.rowHeight === 'string') {
                if (gridster.rowHeight === 'match') {
                  gridster.curRowHeight = Math.round(gridster.curColWidth);
                } else if (gridster.rowHeight.indexOf('*') !== -1) {
                  gridster.curRowHeight = Math.round(gridster.curColWidth * gridster.rowHeight.replace('*', '').replace(' ', ''));
                } else if (gridster.rowHeight.indexOf('/') !== -1) {
                  gridster.curRowHeight = Math.round(gridster.curColWidth / gridster.rowHeight.replace('/', '').replace(' ', ''));
                }
              }

              gridster.isMobile = gridster.mobileModeEnabled && gridster.curWidth <= gridster.mobileBreakPoint;

              // loop through all items and reset their CSS
              for (var rowIndex = 0, l = gridster.grid.length; rowIndex < l; ++rowIndex) {
                var columns = gridster.grid[rowIndex];
                if (!columns) {
                  continue;
                }

                for (var colIndex = 0, len = columns.length; colIndex < len; ++colIndex) {
                  if (columns[colIndex]) {
                    var item = columns[colIndex];
                    gridster.autoSetItemPosition(item);
                    // item.setElementPosition();
                    // item.setElementSizeY();
                    // item.setElementSizeX();
                  }
                }
              }

              updateHeight();
            };

            // update grid items on config changes
            scope.$watch('config', refresh, true);

            scope.$watch('config.draggable', function() {
              $rootScope.$broadcast('gridster-draggable-changed');
            }, true);

            scope.$watch('config.resizable', function() {
              $rootScope.$broadcast('gridster-resizable-changed');
            }, true);

            var updateHeight = function() {
              $elem.css('height', (gridster.gridHeight * gridster.curRowHeight) + (gridster.outerMargin ? gridster.margins[0] : -gridster.margins[0]) + 'px');
            };

            scope.$watch('gridster.gridHeight', updateHeight);

            scope.$watch('gridster.movingItem', function() {
              gridster.updateHeight(gridster.movingItem ? gridster.movingItem.sizeY : 0);
            });

            var prevWidth = $elem[0].offsetWidth || parseInt($elem.css('width'), 10);

            function resize() {
              var width = $elem[0].offsetWidth || parseInt($elem.css('width'), 10);

              if (!width || width === prevWidth || gridster.movingItem) {
                return;
              }
              prevWidth = width;

              if (gridster.loaded) {
                $elem.removeClass('gridster-loaded');
              }

              refresh();

              if (gridster.loaded) {
                $elem.addClass('gridster-loaded');
              }

              scope.$parent.$broadcast('gridster-resized', [width, $elem.offsetHeight]);
            }

            // track element width changes any way we can
            function onResize() {
              resize();
              $timeout(function() {
                scope.$apply();
              });
            }
            if (typeof $elem.resize === 'function') {
              $elem.resize(onResize);
            }
            var $win = angular.element($window);
            $win.on('resize', onResize);

            scope.$watch(function() {
              return $elem[0].offsetWidth || parseInt($elem.css('width'), 10);
            }, resize);

            // be sure to cleanup
            scope.$on('$destroy', function() {
              gridster.destroy();
              $win.off('resize', onResize);
            });

            // allow a little time to place items before floating up
            $timeout(function() {
              scope.$watch('gridster.floating', function() {
                gridster.floatItemsUp();
              });
              gridster.loaded = true;
            }, 100);
          };
        }
      };
    }
  ])

  .controller('GridsterItemCtrl', function() {
    this.$element = null;
    this.gridster = null;
    this.row = null;
    this.col = null;
    this.sizeX = null;
    this.sizeY = null;
    this.minSizeX = 0;
    this.minSizeY = 0;
    this.maxSizeX = null;
    this.maxSizeY = null;

    this.init = function($element, gridster) {
      this.$element = $element;
      this.gridster = gridster;
      this.sizeX = gridster.defaultSizeX;
      this.sizeY = gridster.defaultSizeY;
    };

    this.destroy = function() {
      this.gridster = null;
      this.$element = null;
    };

    /**
     * Returns the items most important attributes
     */
    this.toJSON = function() {
      return {
        row: this.row,
        col: this.col,
        sizeY: this.sizeY,
        sizeX: this.sizeX
      };
    };

    this.isMoving = function() {
      return this.gridster.movingItem === this;
    };

    /**
     * Set the items position
     *
     * @param {number} row
     * @param {number} column
     */
    this.setPosition = function(row, column) {
      this.gridster.putItem(this, row, column);

      if (!this.isMoving()) {
        this.setElementPosition();
      }
    };

    /**
     * Sets a specified size property
     *
     * @param {string} key Can be either "x" or "y"
     * @param {number} value The size amount
     */
    this.setSize = function(key, value, preventMove) {
      key = key.toUpperCase();
      var camelCase = 'size' + key,
        titleCase = 'Size' + key;
      if (value === '') {
        return;
      }
      value = parseInt(value, 10);
      if (isNaN(value) || value === 0) {
        value = this.gridster['default' + titleCase];
      }
      var max = key === 'X' ? this.gridster.columns : this.gridster.maxRows;
      if (this['max' + titleCase]) {
        max = Math.min(this['max' + titleCase], max);
      }
      if (this.gridster['max' + titleCase]) {
        max = Math.min(this.gridster['max' + titleCase], max);
      }
      if (key === 'X' && this.cols) {
        max -= this.cols;
      } else if (key === 'Y' && this.rows) {
        max -= this.rows;
      }

      var min = 0;
      if (this['min' + titleCase]) {
        min = Math.max(this['min' + titleCase], min);
      }
      if (this.gridster['min' + titleCase]) {
        min = Math.max(this.gridster['min' + titleCase], min);
      }

      value = Math.max(Math.min(value, max), min);

      var changed = (this[camelCase] !== value || (this['old' + titleCase] && this['old' + titleCase] !== value));
      this['old' + titleCase] = this[camelCase] = value;

      if (!this.isMoving()) {
        this['setElement' + titleCase]();
      }
      if (!preventMove && changed) {
        this.gridster.moveOverlappingItems(this);
        this.gridster.layoutChanged();
      }

      return changed;
    };

    /**
     * Sets the items sizeY property
     *
     * @param {number} rows
     */
    this.setSizeY = function(rows, preventMove) {
      return this.setSize('Y', rows, preventMove);
    };

    /**
     * Sets the items sizeX property
     *
     * @param {number} rows
     */
    this.setSizeX = function(columns, preventMove) {
      return this.setSize('X', columns, preventMove);
    };

    /**
     * Sets an elements position on the page
     *
     * @param {number} row
     * @param {number} column
     */
    this.setElementPosition = function() {
      if (this.gridster.isMobile) {
        this.$element.css({
          marginLeft: this.gridster.margins[0] + 'px',
          marginRight: this.gridster.margins[0] + 'px',
          marginTop: this.gridster.margins[1] + 'px',
          marginBottom: this.gridster.margins[1] + 'px',
          top: '',
          left: ''
        });
      } else {
        this.$element.css({
          margin: 0,
          top: (this.row * this.gridster.curRowHeight + (this.gridster.outerMargin ? this.gridster.margins[0] : 0)) + 'px',
          left: (this.col * this.gridster.curColWidth + (this.gridster.outerMargin ? this.gridster.margins[1] : 0)) + 'px'
        });
      }
    };

    /**
     * Sets an elements height
     */
    this.setElementSizeY = function() {
      if (this.gridster.isMobile && !this.gridster.saveGridItemCalculatedHeightInMobile) {
        this.$element.css('height', '');
      } else {
        this.$element.css('height', (this.sizeY * this.gridster.curRowHeight - this.gridster.margins[0]) + 'px');
      }
    };

    /**
     * Sets an elements width
     */
    this.setElementSizeX = function() {
      if (this.gridster.isMobile) {
        this.$element.css('width', '');
      } else {
        this.$element.css('width', (this.sizeX * this.gridster.curColWidth - this.gridster.margins[1]) + 'px');
      }
    };

    /**
     * Gets an element's width
     */
    this.getElementSizeX = function() {
      return (this.sizeX * this.gridster.curColWidth - this.gridster.margins[1]);
    };

    /**
     * Gets an element's height
     */
    this.getElementSizeY = function() {
      return (this.sizeY * this.gridster.curRowHeight - this.gridster.margins[0]);
    };

  })

  .factory('GridsterDraggable', ['$document', '$timeout', '$window',
    function($document, $timeout, $window) {
      function GridsterDraggable($el, scope, gridster, item, itemOptions) {

        var elmX, elmY, elmW, elmH,

          mouseX = 0,
          mouseY = 0,
          lastMouseX = 0,
          lastMouseY = 0,
          mOffX = 0,
          mOffY = 0,

          minTop = 0,
          maxTop = 9999,
          minLeft = 0,
          realdocument = $document[0];

        var originalCol, originalRow;
        var inputTags = ['select', 'input', 'textarea', 'button'];

        function mouseDown(e) {
          if (inputTags.indexOf(e.target.nodeName.toLowerCase()) !== -1) {
            return false;
          }

          // exit, if a resize handle was hit
          if (angular.element(e.target).hasClass('gridster-item-resizable-handler')) {
            return false;
          }

          // exit, if the target has it's own click event
          if (angular.element(e.target).attr('onclick') || angular.element(e.target).attr('ng-click')) {
            return false;
          }

          switch (e.which) {
          case 1:
            // left mouse button
            break;
          case 2:
          case 3:
            // right or middle mouse button
            return;
          }

          lastMouseX = e.pageX;
          lastMouseY = e.pageY;

          elmX = parseInt($el.css('left'), 10);
          elmY = parseInt($el.css('top'), 10);
          elmW = $el[0].offsetWidth;
          elmH = $el[0].offsetHeight;

          originalCol = item.col;
          originalRow = item.row;

          dragStart(e);

          return true;
        }

        function mouseMove(e) {
          if (!$el.hasClass('gridster-item-moving') || $el.hasClass('gridster-item-resizing')) {
            return false;
          }

          var maxLeft = gridster.curWidth - 1;

          // Get the current mouse position.
          mouseX = e.pageX;
          mouseY = e.pageY;

          // Get the deltas
          var diffX = mouseX - lastMouseX + mOffX;
          var diffY = mouseY - lastMouseY + mOffY;
          mOffX = mOffY = 0;

          // Update last processed mouse positions.
          lastMouseX = mouseX;
          lastMouseY = mouseY;

          var dX = diffX,
            dY = diffY;
          if (elmX + dX < minLeft) {
            diffX = minLeft - elmX;
            mOffX = dX - diffX;
          } else if (elmX + elmW + dX > maxLeft) {
            diffX = maxLeft - elmX - elmW;
            mOffX = dX - diffX;
          }

          if (elmY + dY < minTop) {
            diffY = minTop - elmY;
            mOffY = dY - diffY;
          } else if (elmY + elmH + dY > maxTop) {
            diffY = maxTop - elmY - elmH;
            mOffY = dY - diffY;
          }
          elmX += diffX;
          elmY += diffY;

          // set new position
          $el.css({
            'top': elmY + 'px',
            'left': elmX + 'px'
          });

          drag(e);

          return true;
        }

        function mouseUp(e) {
          if (!$el.hasClass('gridster-item-moving') || $el.hasClass('gridster-item-resizing')) {
            return false;
          }

          mOffX = mOffY = 0;

          dragStop(e);

          return true;
        }

        function dragStart(event) {
          $el.addClass('gridster-item-moving');
          gridster.movingItem = item;

          gridster.updateHeight(item.sizeY);
          scope.$apply(function() {
            if (gridster.draggable && gridster.draggable.start) {
              gridster.draggable.start(event, $el, itemOptions);
            }
          });
        }

        function drag(event) {
          var oldRow = item.row,
            oldCol = item.col,
            hasCallback = gridster.draggable && gridster.draggable.drag,
            scrollSensitivity = gridster.draggable.scrollSensitivity,
            scrollSpeed = gridster.draggable.scrollSpeed;

          var row = gridster.pixelsToRows(elmY);
          var col = gridster.pixelsToColumns(elmX);

          var itemsInTheWay = gridster.getItems(row, col, item.sizeX, item.sizeY, item);
          var hasItemsInTheWay = itemsInTheWay.length !== 0;

          if (gridster.swapping === true && hasItemsInTheWay) {
            var boundingBoxItem = gridster.getBoundingBox(itemsInTheWay);
            var sameSize = boundingBoxItem.sizeX === item.sizeX && boundingBoxItem.sizeY === item.sizeY;
            var sameRow = boundingBoxItem.row === row;
            var sameCol = boundingBoxItem.col === col;
            var samePosition = sameRow && sameCol;
            var inline = sameRow || sameCol;

            if (sameSize && itemsInTheWay.length === 1) {
              if (samePosition) {
                gridster.swapItems(item, itemsInTheWay[0]);
              } else if (inline) {
                return;
              }
            } else if (boundingBoxItem.sizeX <= item.sizeX && boundingBoxItem.sizeY <= item.sizeY && inline) {
              var emptyRow = item.row <= row ? item.row : row + item.sizeY;
              var emptyCol = item.col <= col ? item.col : col + item.sizeX;
              var rowOffset = emptyRow - boundingBoxItem.row;
              var colOffset = emptyCol - boundingBoxItem.col;

              for (var i = 0, l = itemsInTheWay.length; i < l; ++i) {
                var itemInTheWay = itemsInTheWay[i];

                var itemsInFreeSpace = gridster.getItems(
                  itemInTheWay.row + rowOffset,
                  itemInTheWay.col + colOffset,
                  itemInTheWay.sizeX,
                  itemInTheWay.sizeY,
                  item
                );

                if (itemsInFreeSpace.length === 0) {
                  gridster.putItem(itemInTheWay, itemInTheWay.row + rowOffset, itemInTheWay.col + colOffset);
                }
              }
            }
          }

          if (gridster.pushing !== false || !hasItemsInTheWay) {
            item.row = row;
            item.col = col;
          }

          if (event.pageY - realdocument.body.scrollTop < scrollSensitivity) {
            realdocument.body.scrollTop = realdocument.body.scrollTop - scrollSpeed;
          } else if ($window.innerHeight - (event.pageY - realdocument.body.scrollTop) < scrollSensitivity) {
            realdocument.body.scrollTop = realdocument.body.scrollTop + scrollSpeed;
          }

          if (event.pageX - realdocument.body.scrollLeft < scrollSensitivity) {
            realdocument.body.scrollLeft = realdocument.body.scrollLeft - scrollSpeed;
          } else if ($window.innerWidth - (event.pageX - realdocument.body.scrollLeft) < scrollSensitivity) {
            realdocument.body.scrollLeft = realdocument.body.scrollLeft + scrollSpeed;
          }

          if (hasCallback || oldRow !== item.row || oldCol !== item.col) {
            scope.$apply(function() {
              if (hasCallback) {
                gridster.draggable.drag(event, $el, itemOptions);
              }
            });
          }
        }

        function dragStop(event) {
          $el.removeClass('gridster-item-moving');
          var row = gridster.pixelsToRows(elmY);
          var col = gridster.pixelsToColumns(elmX);
          if (gridster.pushing !== false || gridster.getItems(row, col, item.sizeX, item.sizeY, item).length === 0) {
            item.row = row;
            item.col = col;
          }
          gridster.movingItem = null;
          item.setPosition(item.row, item.col);

          scope.$apply(function() {
            if (gridster.draggable && gridster.draggable.stop) {
              gridster.draggable.stop(event, $el, itemOptions);
            }
          });
        }

        var enabled = false;
        var $dragHandle = null;
        var unifiedInput;

        this.enable = function() {
          var self = this;
          // disable and timeout required for some template rendering
          $timeout(function() {
            self.disable();

            if (gridster.draggable && gridster.draggable.handle) {
              $dragHandle = angular.element($el[0].querySelector(gridster.draggable.handle));
              if ($dragHandle.length === 0) {
                // fall back to element if handle not found...
                $dragHandle = $el;
              }
            } else {
              $dragHandle = $el;
            }

            unifiedInput = new gridster.unifiedInput($dragHandle[0], mouseDown, mouseMove, mouseUp);
            unifiedInput.enable();

            enabled = true;
          });
        };

        this.disable = function() {
          if (!enabled) {
            return;
          }

          unifiedInput.disable();
          unifiedInput = undefined;
          enabled = false;
        };

        this.toggle = function(enabled) {
          if (enabled) {
            this.enable();
          } else {
            this.disable();
          }
        };

        this.destroy = function() {
          this.disable();
        };
      }

      return GridsterDraggable;
    }
  ])

  .factory('GridsterResizable', [
    function() {
      function GridsterResizable($el, scope, gridster, item, itemOptions) {

        function ResizeHandle(handleClass) {

          var hClass = handleClass;

          var elmX, elmY, elmW, elmH,

            mouseX = 0,
            mouseY = 0,
            lastMouseX = 0,
            lastMouseY = 0,
            mOffX = 0,
            mOffY = 0,

            minTop = 0,
            maxTop = 9999,
            minLeft = 0;

          var getMinHeight = function() {
            return gridster.curRowHeight - gridster.margins[0];
          };
          var getMinWidth = function() {
            return gridster.curColWidth - gridster.margins[1];
          };

          var originalWidth, originalHeight;
          var savedDraggable;

          function mouseDown(e) {
            switch (e.which) {
            case 1:
              // left mouse button
              break;
            case 2:
            case 3:
              // right or middle mouse button
              return;
            }

            // save the draggable setting to restore after resize
            savedDraggable = gridster.draggable.enabled;
            if (savedDraggable) {
              gridster.draggable.enabled = false;
              scope.$broadcast('gridster-draggable-changed');
            }

            // Get the current mouse position.
            lastMouseX = e.pageX;
            lastMouseY = e.pageY;

            // Record current widget dimensions
            elmX = parseInt($el.css('left'), 10);
            elmY = parseInt($el.css('top'), 10);
            elmW = $el[0].offsetWidth;
            elmH = $el[0].offsetHeight;

            originalWidth = item.sizeX;
            originalHeight = item.sizeY;

            resizeStart(e);

            return true;
          }

          function resizeStart(e) {
            $el.addClass('gridster-item-moving');
            $el.addClass('gridster-item-resizing');

            gridster.movingItem = item;

            item.setElementSizeX();
            item.setElementSizeY();
            item.setElementPosition();
            gridster.updateHeight(1);

            scope.$apply(function() {
              // callback
              if (gridster.resizable && gridster.resizable.start) {
                gridster.resizable.start(e, $el, itemOptions); // options is the item model
              }
            });
          }

          function mouseMove(e) {
            scope.$broadcast('gridster-draggable-item-resizing');
            var maxLeft = gridster.curWidth - 1;

            // Get the current mouse position.
            mouseX = e.pageX;
            mouseY = e.pageY;

            // Get the deltas
            var diffX = mouseX - lastMouseX + mOffX;
            var diffY = mouseY - lastMouseY + mOffY;
            mOffX = mOffY = 0;

            // Update last processed mouse positions.
            lastMouseX = mouseX;
            lastMouseY = mouseY;

            var dY = diffY,
              dX = diffX;

            if (hClass.indexOf('n') >= 0) {
              if (elmH - dY < getMinHeight()) {
                diffY = elmH - getMinHeight();
                mOffY = dY - diffY;
              } else if (elmY + dY < minTop) {
                diffY = minTop - elmY;
                mOffY = dY - diffY;
              }
              elmY += diffY;
              elmH -= diffY;
            }
            if (hClass.indexOf('s') >= 0) {
              if (elmH + dY < getMinHeight()) {
                diffY = getMinHeight() - elmH;
                mOffY = dY - diffY;
              } else if (elmY + elmH + dY > maxTop) {
                diffY = maxTop - elmY - elmH;
                mOffY = dY - diffY;
              }
              elmH += diffY;
            }
            if (hClass.indexOf('w') >= 0) {
              if (elmW - dX < getMinWidth()) {
                diffX = elmW - getMinWidth();
                mOffX = dX - diffX;
              } else if (elmX + dX < minLeft) {
                diffX = minLeft - elmX;
                mOffX = dX - diffX;
              }
              elmX += diffX;
              elmW -= diffX;
            }
            if (hClass.indexOf('e') >= 0) {
              if (elmW + dX < getMinWidth()) {
                diffX = getMinWidth() - elmW;
                mOffX = dX - diffX;
              } else if (elmX + elmW + dX > maxLeft) {
                diffX = maxLeft - elmX - elmW;
                mOffX = dX - diffX;
              }
              elmW += diffX;
            }

            // set new position
            $el.css({
              'top': elmY + 'px',
              'left': elmX + 'px',
              'width': elmW + 'px',
              'height': elmH + 'px'
            });

            resize(e);

            return true;
          }

          function mouseUp(e) {
            // restore draggable setting to its original state
            if (gridster.draggable.enabled !== savedDraggable) {
              gridster.draggable.enabled = savedDraggable;
              scope.$broadcast('gridster-draggable-changed');
            }

            mOffX = mOffY = 0;

            resizeStop(e);

            return true;
          }

          function resize(e) {
            var oldRow = item.row,
              oldCol = item.col,
              oldSizeX = item.sizeX,
              oldSizeY = item.sizeY,
              hasCallback = gridster.resizable && gridster.resizable.resize;

            var col = item.col;
            // only change column if grabbing left edge
            if (['w', 'nw', 'sw'].indexOf(handleClass) !== -1) {
              col = gridster.pixelsToColumns(elmX, false);
            }

            var row = item.row;
            // only change row if grabbing top edge
            if (['n', 'ne', 'nw'].indexOf(handleClass) !== -1) {
              row = gridster.pixelsToRows(elmY, false);
            }

            var sizeX = item.sizeX;
            // only change row if grabbing left or right edge
            if (['n', 's'].indexOf(handleClass) === -1) {
              sizeX = gridster.pixelsToColumns(elmW, true);
            }

            var sizeY = item.sizeY;
            // only change row if grabbing top or bottom edge
            if (['e', 'w'].indexOf(handleClass) === -1) {
              sizeY = gridster.pixelsToRows(elmH, true);
            }

            if (gridster.pushing !== false || gridster.getItems(row, col, sizeX, sizeY, item).length === 0) {
              item.row = row;
              item.col = col;
              item.sizeX = sizeX;
              item.sizeY = sizeY;
            }
            var isChanged = item.row !== oldRow || item.col !== oldCol || item.sizeX !== oldSizeX || item.sizeY !== oldSizeY;

            if (hasCallback || isChanged) {
              scope.$apply(function() {
                if (hasCallback) {
                  gridster.resizable.resize(e, $el, itemOptions); // options is the item model
                }
              });
            }
          }

          function resizeStop(e) {
            $el.removeClass('gridster-item-moving');
            $el.removeClass('gridster-item-resizing');

            gridster.movingItem = null;

            item.setPosition(item.row, item.col);
            item.setSizeY(item.sizeY);
            item.setSizeX(item.sizeX);

            scope.$apply(function() {
              if (gridster.resizable && gridster.resizable.stop) {
                gridster.resizable.stop(e, $el, itemOptions); // options is the item model
              }
            });
          }

          var $dragHandle = null;
          var unifiedInput;

          this.enable = function() {
            if (!$dragHandle) {
              $dragHandle = angular.element('<div class="gridster-item-resizable-handler handle-' + hClass + '"></div>');
              $el.append($dragHandle);
            }

            unifiedInput = new gridster.unifiedInput($dragHandle[0], mouseDown, mouseMove, mouseUp);
            unifiedInput.enable();
          };

          this.disable = function() {
            if ($dragHandle) {
              $dragHandle.remove();
              $dragHandle = null;
            }

            unifiedInput.disable();
            unifiedInput = undefined;
          };

          this.destroy = function() {
            this.disable();
          };
        }

        var handles = [];
        var handlesOpts = gridster.resizable.handles;
        if (typeof handlesOpts === 'string') {
          handlesOpts = gridster.resizable.handles.split(',');
        }
        var enabled = false;

        for (var c = 0, l = handlesOpts.length; c < l; c++) {
          handles.push(new ResizeHandle(handlesOpts[c]));
        }

        this.enable = function() {
          if (enabled) {
            return;
          }
          for (var c = 0, l = handles.length; c < l; c++) {
            handles[c].enable();
          }
          enabled = true;
        };

        this.disable = function() {
          if (!enabled) {
            return;
          }
          for (var c = 0, l = handles.length; c < l; c++) {
            handles[c].disable();
          }
          enabled = false;
        };

        this.toggle = function(enabled) {
          if (enabled) {
            this.enable();
          } else {
            this.disable();
          }
        };

        this.destroy = function() {
          for (var c = 0, l = handles.length; c < l; c++) {
            handles[c].destroy();
          }
        };
      }
      return GridsterResizable;
    }
  ])

  /**
   * GridsterItem directive
   */
  .directive('gridsterItem', ['$parse', 'GridsterDraggable', 'GridsterResizable',
    function($parse, GridsterDraggable, GridsterResizable) {
      return {
        restrict: 'EA',
        controller: 'GridsterItemCtrl',
        require: ['^gridster', 'gridsterItem'],
        link: function(scope, $el, attrs, controllers) {
          var optionsKey = attrs.gridsterItem,
            options;

          var gridster = controllers[0],
            item = controllers[1];

          // bind the item's position properties
          if (optionsKey) {
            var $optionsGetter = $parse(optionsKey);
            options = $optionsGetter(scope) || {};
            if (!options && $optionsGetter.assign) {
              options = {
                row: item.row,
                col: item.col,
                sizeX: item.sizeX,
                sizeY: item.sizeY,
                minSizeX: 0,
                minSizeY: 0,
                maxSizeX: null,
                maxSizeY: null
              };
              $optionsGetter.assign(scope, options);
            }
          } else {
            options = attrs;
          }

          item.init($el, gridster);

          $el.addClass('gridster-item');

          var aspects = ['minSizeX', 'maxSizeX', 'minSizeY', 'maxSizeY', 'sizeX', 'sizeY', 'row', 'col'],
            $getters = {};

          var aspectFn = function(aspect) {
            var key;
            if (typeof options[aspect] === 'string') {
              key = options[aspect];
            } else if (typeof options[aspect.toLowerCase()] === 'string') {
              key = options[aspect.toLowerCase()];
            } else if (optionsKey) {
              key = $parse(optionsKey + '.' + aspect);
            } else {
              return;
            }
            $getters[aspect] = $parse(key);

            // when the value changes externally, update the internal item object
            scope.$watch(key, function(newVal) {
              newVal = parseInt(newVal, 10);
              if (!isNaN(newVal)) {
                item[aspect] = newVal;
              }
            });

            // initial set
            var val = $getters[aspect](scope);
            if (typeof val === 'number') {
              item[aspect] = val;
            }
          };

          for (var i = 0, l = aspects.length; i < l; ++i) {
            aspectFn(aspects[i]);
          }

          scope.$broadcast('gridster-item-initialized', [item.sizeY, item.sizeX, item.getElementSizeY(), item.getElementSizeX()]);

          function positionChanged() {
            // call setPosition so the element and gridster controller are updated
            item.setPosition(item.row, item.col);

            // when internal item position changes, update externally bound values
            if ($getters.row && $getters.row.assign) {
              $getters.row.assign(scope, item.row);
            }
            if ($getters.col && $getters.col.assign) {
              $getters.col.assign(scope, item.col);
            }
          }
          scope.$watch(function() {
            return item.row + ',' + item.col;
          }, positionChanged);

          function sizeChanged() {
            var changedX = item.setSizeX(item.sizeX, true);
            if (changedX && $getters.sizeX && $getters.sizeX.assign) {
              $getters.sizeX.assign(scope, item.sizeX);
            }
            var changedY = item.setSizeY(item.sizeY, true);
            if (changedY && $getters.sizeY && $getters.sizeY.assign) {
              $getters.sizeY.assign(scope, item.sizeY);
            }

            if (changedX || changedY) {
              item.gridster.moveOverlappingItems(item);
              gridster.layoutChanged();
            }
          }
          scope.$watch(function() {
            return item.sizeY + ',' + item.sizeX + '|' + item.minSizeX + ',' + item.maxSizeX + ',' + item.minSizeY + ',' + item.maxSizeY;
          }, sizeChanged);

          var draggable = new GridsterDraggable($el, scope, gridster, item, options);
          var resizable = new GridsterResizable($el, scope, gridster, item, options);

          scope.$on('gridster-draggable-changed', function() {
            draggable.toggle(!gridster.isMobile && gridster.draggable && gridster.draggable.enabled);
          });
          scope.$on('gridster-resizable-changed', function() {
            resizable.toggle(!gridster.isMobile && gridster.resizable && gridster.resizable.enabled);
          });
          scope.$on('gridster-resized', function() {
            resizable.toggle(!gridster.isMobile && gridster.resizable && gridster.resizable.enabled);
          });
          scope.$watch(function() {
            return gridster.isMobile;
          }, function() {
            resizable.toggle(!gridster.isMobile && gridster.resizable && gridster.resizable.enabled);
            draggable.toggle(!gridster.isMobile && gridster.draggable && gridster.draggable.enabled);
          });

          function whichTransitionEvent() {
            var el = document.createElement('div');
            var transitions = {
              'transition': 'transitionend',
              'OTransition': 'oTransitionEnd',
              'MozTransition': 'transitionend',
              'WebkitTransition': 'webkitTransitionEnd'
            };
            for (var t in transitions) {
              if (el.style[t] !== undefined) {
                return transitions[t];
              }
            }
          }

          $el.on(whichTransitionEvent(), function() {
            scope.$apply(function() {
              scope.$broadcast('gridster-item-transition-end');
            });
          });

          return scope.$on('$destroy', function() {
            try {
              resizable.destroy();
              draggable.destroy();
            } catch (e) {}

            try {
              gridster.removeItem(item);
            } catch (e) {}

            try {
              item.destroy();
            } catch (e) {}
          });
        }
      };
    }
  ])

  ;

})(angular);

'use strict';

angular.module('ark-dashboard')
   .directive('dropdownMenu', function () {
    return {
      restrict: 'A',
      templateUrl: function() {
        return 'src/dashboard/components/dropdown-menu/dropdown-menu.html';
      },
      scope: {
        menu: '=',
        layoutActions: '=',
        defaultLayoutActions: '=',
        widgetActions: '=',
        defaultWidgetActions: '=',
        widgetData: '='
      }
    };
  })
  .controller('dropdownMenuController', ['$scope', function ($scope) {
    $scope.handleMenuOption = function (action) {

      if($scope.layoutActions) {
        for(var i = 0; i < $scope.layoutActions.length; i++) {
          var layoutItem = $scope.layoutActions[i];
          for (var layoutFunc in layoutItem) {
            if(action === layoutFunc) {
              var callLayoutFunc = layoutItem[layoutFunc];
              if(typeof callLayoutFunc === 'function') {
                callLayoutFunc();
              }
            }
          }
          if(typeof layoutItem === 'string' && action === layoutItem) {
            var defaultLayoutItem = $scope.defaultLayoutActions[i];
            var callLayoutFuncDefault = defaultLayoutItem[layoutItem];
            callLayoutFuncDefault();
          }
        }
      }
      if($scope.widgetActions) {
        for(var j = 0; j < $scope.widgetActions.length; j++) {
          var widgetItem = $scope.widgetActions[j];
          for (var widgetFunc in widgetItem) {
            if(action === widgetFunc) {
              var callWidgetFunc = widgetItem[widgetFunc];
              if(typeof callWidgetFunc === 'function') {
                callWidgetFunc($scope.widgetData);
              }
            }
          }
          if(typeof widgetItem === 'string' && action === widgetItem) {
            var defaultWidgetItem = $scope.defaultWidgetActions[j];
            var callWidgetFuncDefault = defaultWidgetItem[widgetItem];
            callWidgetFuncDefault($scope.widgetData);
          }
        }
      }
    };
  }])
  .directive('selectText', ['$timeout', function ($timeout) {
    return {
      scope: {
        trigger: '@focus'
      },
      link: function(scope, element) {
        scope.$watch('trigger', function() {
          $timeout(function() {
            element.select();
          });
        });
      }
    };
  }]);

(function() {
  'use strict';

  var CONSTANTS = {
      CONTINUOUS_SCROLLING_TIMEOUT_INTERVAL: 50, // timeout interval for repeatedly moving the tabs container
      // by one increment while the mouse is held down--decrease to
      // make mousedown continous scrolling faster
      SCROLL_OFFSET_FRACTION: 6, // each click moves the container this fraction of the fixed container--decrease
      // to make the tabs scroll farther per click
      DATA_KEY_IS_MOUSEDOWN: 'ismousedown'
    },

    /* *************************************************************
     * scrolling-tabs element directive template
     * *************************************************************/
    // plunk: http://plnkr.co/edit/YhKiIhuAPkpAyacu6tuk
    scrollingTabsTemplate = [
      '<div class="scrtabs-tab-container">',
      ' <div class="scrtabs-tab-scroll-arrow scrtabs-js-tab-scroll-arrow-left"><span class="fonticon  icon-chevron-small-left scr-arrow-left"></span></div>',
      '   <div class="scrtabs-tabs-fixed-container">',
      '     <div class="scrtabs-tabs-movable-container">',
      '       <ul class="nav nav-tabs" role="tablist">',
      '         <li ng-class="{ \'active\': tab[propActive || \'active\'], ',
      '                         \'disabled\': tab[propDisabled || \'disabled\'] }" ',
      '             data-tab="{{tab}}" data-index="{{$index}}" ng-repeat="tab in tabsArr">',
      '           <a ng-href="{{\'#\' + tab[propPaneId || \'paneId\']}}" role="tab"',
      '                data-toggle="{{tab[propDisabled || \'disabled\'] ? \'\' : \'tab\'}}" ',
      '                ng-bind-html="sanitize(tab[propTitle || \'title\']);">',
      '           </a>',
      '         </li>',
      '       </ul>',
      '     </div>',
      ' </div>',
      ' <div class="scrtabs-tab-scroll-arrow scrtabs-js-tab-scroll-arrow-right"><span class="fonticon icon-chevron-small-right scr-arrow-right"></span></div>',
      '</div>'
    ].join(''),


    /* *************************************************************
     * scrolling-tabs-wrapper element directive template
     * *************************************************************/
    // plunk: http://plnkr.co/edit/lWeQxxecKPudK7xlQxS3
    scrollingTabsWrapperTemplate = [
      '<div class="scrtabs-tab-container">',
      ' <div class="scrtabs-tab-scroll-arrow scrtabs-js-tab-scroll-arrow-left"><span class="fonticon icon-chevron-small-left scr-arrow-left"></span></div>',
      '   <div class="scrtabs-tabs-fixed-container">',
      '     <div class="scrtabs-tabs-movable-container" ng-transclude></div>',
      '   </div>',
      ' <div class="scrtabs-tab-scroll-arrow scrtabs-js-tab-scroll-arrow-right"><span class="fonticon icon-chevron-small-right scr-arrow-right"></span></div>',
      '</div>'
    ].join('');


  // smartresize from Paul Irish (debounced window resize)
  (function($, sr) {
    var debounce = function(func, threshold, execAsap) {
      var timeout;

      return function debounced() {
        var obj = this,
          args = arguments;

        function delayed() {
          if (!execAsap) {
            func.apply(obj, args);
          }
          timeout = null;
        }

        if (timeout) {
          clearTimeout(timeout);
        }
        else if (execAsap) {
          func.apply(obj, args);
        }

        timeout = setTimeout(delayed, threshold || 100);
      };
    };
    jQuery.fn[sr] = function(fn) {
      return fn ? this.bind('resize.scrtabs', debounce(fn)) : this.trigger(sr);
    };

  })(jQuery, 'smartresize');



  /* ***********************************************************************************
   * EventHandlers - Class that each instance of ScrollingTabsControl will instantiate
   * **********************************************************************************/
  function EventHandlers(scrollingTabsControl) {
    var evh = this;

    evh.stc = scrollingTabsControl;
  }

  // prototype methods
  (function(p) {
    p.handleClickOnLeftScrollArrow = function() {
      var evh = this,
        stc = evh.stc;

      stc.scrollMovement.incrementScrollLeft();
    };

    p.handleClickOnRightScrollArrow = function() {
      var evh = this,
        stc = evh.stc,
        scrollMovement = stc.scrollMovement;

      scrollMovement.incrementScrollRight(scrollMovement.getMinPos());
    };

    p.handleMousedownOnLeftScrollArrow = function() {
      var evh = this,
        stc = evh.stc;

      stc.scrollMovement.startScrollLeft();
    };

    p.handleMousedownOnRightScrollArrow = function() {
      var evh = this,
        stc = evh.stc;

      stc.scrollMovement.startScrollRight();
    };

    p.handleMouseupOnLeftScrollArrow = function() {
      var evh = this,
        stc = evh.stc;

      stc.scrollMovement.stopScrollLeft();
    };

    p.handleMouseupOnRightScrollArrow = function() {
      var evh = this,
        stc = evh.stc;

      stc.scrollMovement.stopScrollRight();
    };

    p.handleWindowResize = function() {
      var evh = this,
        stc = evh.stc,
        newWinWidth = stc.$win.width();

      if (newWinWidth === stc.winWidth) {
        return false; // false alarm
      }

      stc.winWidth = newWinWidth;
      stc.elementsHandler.refreshAllElementSizes(true); // true -> check for scroll arrows not being necessary anymore
    };

    p.addtab = function() {
      var evh = this,
        stc = evh.stc;
      stc.elementsHandler.setMovableContainerWidth();
      stc.elementsHandler.setScrollArrowVisibility();
      stc.scrollMovement.startScrollRight();
    };

    p.removetab = function() {
      var evh = this,
        stc = evh.stc;
      stc.elementsHandler.setMovableContainerWidth();
      stc.elementsHandler.setScrollArrowVisibility();
      stc.scrollMovement.incrementScrollLeft();
    };

  }(EventHandlers.prototype));



  /* ***********************************************************************************
   * ElementsHandler - Class that each instance of ScrollingTabsControl will instantiate
   * **********************************************************************************/
  function ElementsHandler(scrollingTabsControl) {
    var ehd = this;

    ehd.stc = scrollingTabsControl;
  }

  // prototype methods
  (function(p) {
    p.initElements = function(isWrapperDirective) {
      var ehd = this;

      ehd.setElementReferences();

      if (isWrapperDirective) {
        ehd.moveTabContentOutsideScrollContainer();
      }

      ehd.setEventListeners();
    };

    p.moveTabContentOutsideScrollContainer = function() {
      var ehd = this,
        stc = ehd.stc,
        $tabsContainer = stc.$tabsContainer;

      $tabsContainer.find('.tab-content').appendTo($tabsContainer);
    };

    p.refreshAllElementSizes = function(isPossibleArrowVisibilityChange) {
      var ehd = this,
        stc = ehd.stc,
        smv = stc.scrollMovement,
        scrollArrowsWereVisible = stc.scrollArrowsVisible,
        minPos;

      ehd.setElementWidths();
      ehd.setScrollArrowVisibility();

      if (stc.scrollArrowsVisible) {
        ehd.setFixedContainerWidthForJustVisibleScrollArrows();
      }

      // if this was a window resize, make sure the movable container is positioned
      // correctly because, if it is far to the left and we increased the window width, it's
      // possible that the tabs will be too far left, beyond the min pos.
      if (isPossibleArrowVisibilityChange && (stc.scrollArrowsVisible || scrollArrowsWereVisible)) {
        if (stc.scrollArrowsVisible) {
          // make sure container not too far left
          minPos = smv.getMinPos();
          if (stc.movableContainerLeftPos < minPos) {
            smv.incrementScrollRight(minPos);
          } else {
            smv.scrollToActiveTab(true); // true -> isOnWindowResize
          }
        } else {
          // scroll arrows went away after resize, so position movable container at 0
          stc.movableContainerLeftPos = 0;
          smv.slideMovableContainerToLeftPos();
        }
      }
    };

    p.setElementReferences = function() {
      var ehd = this,
        stc = ehd.stc,
        $tabsContainer = stc.$tabsContainer;

      stc.$fixedContainer = $tabsContainer.find('.scrtabs-tabs-fixed-container');
      stc.$movableContainer = $tabsContainer.find('.scrtabs-tabs-movable-container');
      stc.$tabsUl = $tabsContainer.find('.tabs-item');
      stc.$tabsUlActive = $tabsContainer.find('.nav-tabs');
      stc.$leftScrollArrow = $tabsContainer.find('.scrtabs-js-tab-scroll-arrow-left');
      stc.$rightScrollArrow = $tabsContainer.find('.scrtabs-js-tab-scroll-arrow-right');
      stc.$scrollArrows = stc.$leftScrollArrow.add(stc.$rightScrollArrow);

      stc.$win = jQuery(window);
    };

    p.setElementWidths = function() {
      var ehd = this,
        stc = ehd.stc;

      stc.containerWidth = stc.$tabsContainer.outerWidth();
      stc.winWidth = stc.$win.width();

      stc.scrollArrowsCombinedWidth = stc.$leftScrollArrow.outerWidth() + stc.$rightScrollArrow.outerWidth();

      ehd.setFixedContainerWidth();
      ehd.setMovableContainerWidth();
    };

    p.setEventListeners = function() {
      var ehd = this,
        stc = ehd.stc,
        evh = stc.eventHandlers; // eventHandlers

      stc.$leftScrollArrow.on({
        'mousedown.scrtabs': function(e) {
          evh.handleMousedownOnLeftScrollArrow.call(evh, e);
        },
        'mouseup.scrtabs': function(e) {
          evh.handleMouseupOnLeftScrollArrow.call(evh, e);
        },
        'click.scrtabs': function(e) {
          evh.handleClickOnLeftScrollArrow.call(evh, e);
        }
      });

      stc.$rightScrollArrow.on({
        'mousedown.scrtabs': function(e) {
          evh.handleMousedownOnRightScrollArrow.call(evh, e);
        },
        'mouseup.scrtabs': function(e) {
          evh.handleMouseupOnRightScrollArrow.call(evh, e);
        },
        'click.scrtabs': function(e) {
          evh.handleClickOnRightScrollArrow.call(evh, e);
        }
      });

      stc.$win.smartresize(function(e) {
        evh.handleWindowResize.call(evh, e);
      });

      stc.scope.$watch(
        function () {return angular.element('.tabs-item').length; },
        function (newValue, oldValue) {
          if(newValue > oldValue) {
            evh.addtab.call(evh);
          } else if (oldValue > newValue) {
            evh.removetab.call(evh);
          }
        });

    };

    p.setFixedContainerWidth = function() {
      var ehd = this,
        stc = ehd.stc;

      stc.$fixedContainer.width(stc.fixedContainerWidth = stc.$tabsContainer.outerWidth());
    };

    p.setFixedContainerWidthForJustHiddenScrollArrows = function() {
      var ehd = this,
        stc = ehd.stc;

      stc.$fixedContainer.width(stc.fixedContainerWidth);
    };

    p.setFixedContainerWidthForJustVisibleScrollArrows = function() {
      var ehd = this,
        stc = ehd.stc;

      stc.$fixedContainer.width(stc.fixedContainerWidth - stc.scrollArrowsCombinedWidth);
    };

    p.setMovableContainerWidth = function() {
      var ehd = this,
        stc = ehd.stc;

      stc.movableContainerWidth = 50;

      angular.element('.tabs-item').each(function __getLiWidth() {
        var $li = jQuery(this);

        stc.movableContainerWidth += $li.outerWidth();
      });

      stc.$movableContainer.width(stc.movableContainerWidth += 1);
    };

    p.setScrollArrowVisibility = function() {
      var ehd = this,
        stc = ehd.stc,
        shouldBeVisible = stc.movableContainerWidth > stc.fixedContainerWidth;

      if(shouldBeVisible) {
        angular.element('.tabs-add-button').addClass('fixed-add-button');
      }
      if (shouldBeVisible && !stc.scrollArrowsVisible) {
        stc.$scrollArrows.show();
        stc.scrollArrowsVisible = true;
        ehd.setFixedContainerWidthForJustVisibleScrollArrows();
      } else if (!shouldBeVisible && stc.scrollArrowsVisible) {
        angular.element('.tabs-add-button').removeClass('fixed-add-button');
        stc.scrollMovement.incrementScrollLeft();
        stc.$scrollArrows.hide();
        stc.scrollArrowsVisible = false;
        ehd.setFixedContainerWidthForJustHiddenScrollArrows();
      }
    };

  }(ElementsHandler.prototype));



  /* ***********************************************************************************
   * ScrollMovement - Class that each instance of ScrollingTabsControl will instantiate
   * **********************************************************************************/
  function ScrollMovement(scrollingTabsControl) {
    var smv = this;

    smv.stc = scrollingTabsControl;
  }

  // prototype methods
  (function(p) {

    p.continueScrollLeft = function() {
      var smv = this,
        stc = smv.stc;

      stc.$timeout(function() {
        if (stc.$leftScrollArrow.data(CONSTANTS.DATA_KEY_IS_MOUSEDOWN) && (stc.movableContainerLeftPos < 0)) {
          if (!smv.incrementScrollLeft()) { // scroll limit not reached, so keep scrolling
            smv.continueScrollLeft();
          }
        }
      }, CONSTANTS.CONTINUOUS_SCROLLING_TIMEOUT_INTERVAL);
    };

    p.continueScrollRight = function(minPos) {
      var smv = this,
        stc = smv.stc;

      stc.$timeout(function() {
        if (stc.$rightScrollArrow.data(CONSTANTS.DATA_KEY_IS_MOUSEDOWN) && (stc.movableContainerLeftPos > minPos)) {
          // slide tabs LEFT -> decrease movable container's left position
          // min value is (movableContainerWidth - $tabHeader width)
          if (!smv.incrementScrollRight(minPos)) {
            smv.continueScrollRight(minPos);
          }
        }
      }, CONSTANTS.CONTINUOUS_SCROLLING_TIMEOUT_INTERVAL);
    };

    p.decrementMovableContainerLeftPos = function(minPos) {
      var smv = this,
        stc = smv.stc;

      stc.movableContainerLeftPos -= (stc.fixedContainerWidth / CONSTANTS.SCROLL_OFFSET_FRACTION);
      if (stc.movableContainerLeftPos < minPos) {
        stc.movableContainerLeftPos = minPos;
      }
    };

    p.getMinPos = function() {
      var smv = this,
        stc = smv.stc;

      return stc.scrollArrowsVisible ? (stc.fixedContainerWidth - stc.movableContainerWidth - stc.scrollArrowsCombinedWidth) : 0;
    };

    p.getMovableContainerCssLeftVal = function() {
      var smv = this,
        stc = smv.stc;

      return (stc.movableContainerLeftPos === 0) ? '0' : stc.movableContainerLeftPos + 'px';
    };

    p.incrementScrollLeft = function() {
      var smv = this,
        stc = smv.stc;

      stc.movableContainerLeftPos += (stc.fixedContainerWidth / CONSTANTS.SCROLL_OFFSET_FRACTION);
      if (stc.movableContainerLeftPos > 0) {
        stc.movableContainerLeftPos = 0;
      }

      smv.slideMovableContainerToLeftPos();

      return (stc.movableContainerLeftPos === 0); // indicates scroll limit reached
    };

    p.incrementScrollRight = function(minPos) {
      var smv = this,
        stc = smv.stc;

      smv.decrementMovableContainerLeftPos(minPos);
      smv.slideMovableContainerToLeftPos();

      return (stc.movableContainerLeftPos === minPos);
    };

    p.scrollToActiveTab = function(isOnWindowResize) {
      var smv = this,
        stc = smv.stc,
        $activeTab,
        activeTabWidth,
        activeTabLeftPos,
        rightArrowLeftPos,
        overlap;

      // if the active tab is not fully visible, scroll till it is
      if (!stc.scrollArrowsVisible) {
        return;
      }

      $activeTab = stc.$tabsUlActive.find('li.active');

      if (!$activeTab.length) {
        return;
      }

      activeTabWidth = $activeTab.outerWidth();
      activeTabLeftPos = $activeTab.offset().left;

      rightArrowLeftPos = stc.$rightScrollArrow.offset().left;
      overlap = activeTabLeftPos + activeTabWidth - rightArrowLeftPos;

      if (overlap > 0) {
        stc.movableContainerLeftPos = isOnWindowResize ? (stc.movableContainerLeftPos - overlap) : -overlap;
        smv.slideMovableContainerToLeftPos();
      }
    };

    p.slideMovableContainerToLeftPos = function() {
      var smv = this,
        stc = smv.stc,
        leftVal;

      stc.movableContainerLeftPos = stc.movableContainerLeftPos / 1;
      leftVal = smv.getMovableContainerCssLeftVal();

      stc.$movableContainer.stop().animate({
        left: leftVal
      }, 'slow', function __slideAnimComplete() {
        var newMinPos = smv.getMinPos();

        // if we slid past the min pos--which can happen if you resize the window
        // quickly--move back into position
        if (stc.movableContainerLeftPos < newMinPos) {
          smv.decrementMovableContainerLeftPos(newMinPos);
          stc.$movableContainer.stop().animate({
            left: smv.getMovableContainerCssLeftVal()
          }, 'fast');
        }
      });
    };

    p.startScrollLeft = function() {
      var smv = this,
        stc = smv.stc;

      stc.$leftScrollArrow.data(CONSTANTS.DATA_KEY_IS_MOUSEDOWN, true);
      smv.continueScrollLeft();
    };

    p.startScrollRight = function() {
      var smv = this,
        stc = smv.stc;

      stc.$rightScrollArrow.data(CONSTANTS.DATA_KEY_IS_MOUSEDOWN, true);
      smv.continueScrollRight(smv.getMinPos());
    };

    p.stopScrollLeft = function() {
      var smv = this,
        stc = smv.stc;

      stc.$leftScrollArrow.data(CONSTANTS.DATA_KEY_IS_MOUSEDOWN, false);
    };

    p.stopScrollRight = function() {
      var smv = this,
        stc = smv.stc;

      stc.$rightScrollArrow.data(CONSTANTS.DATA_KEY_IS_MOUSEDOWN, false);
    };

  }(ScrollMovement.prototype));



  /* **********************************************************************
   * ScrollingTabsControl - Class that each directive will instantiate
   * **********************************************************************/
  function ScrollingTabsControl(scope, $tabsContainer, $timeout) {
    var stc = this;

    stc.$tabsContainer = $tabsContainer;
    stc.$timeout = $timeout;
    stc.scope = scope;
    stc.movableContainerLeftPos = 0;
    stc.scrollArrowsVisible = true;

    stc.scrollMovement = new ScrollMovement(stc);
    stc.eventHandlers = new EventHandlers(stc);
    stc.elementsHandler = new ElementsHandler(stc);
  }

  // prototype methods
  (function(p) {
    p.initTabs = function(isWrapperDirective) {
      var stc = this,
        elementsHandler = stc.elementsHandler,
        scrollMovement = stc.scrollMovement;

      stc.$timeout(function __initTabsAfterTimeout() {
        elementsHandler.initElements(isWrapperDirective);
        elementsHandler.refreshAllElementSizes();
        elementsHandler.setScrollArrowVisibility();
        scrollMovement.scrollToActiveTab();
      }, 100);
    };


  }(ScrollingTabsControl.prototype));



  /* ********************************************************
   * scrolling-tabs Directive
   * ********************************************************/

  function scrollingTabsDirective($timeout, $sce) {

    function sanitize(html) {
      return $sce.trustAsHtml(html);
    }


    // ------------ Directive Object ---------------------------
    return {
      restrict: 'E',
      template: scrollingTabsTemplate,
      transclude: false,
      replace: true,
      scope: {
        tabs: '@',
        propPaneId: '@',
        propTitle: '@',
        propActive: '@',
        propDisabled: '@',
        localTabClick: '&tabClick'
      },
      link: function(scope, element) {
        var scrollingTabsControl = new ScrollingTabsControl(scope, element, $timeout);

        scope.tabsArr = scope.$eval(scope.tabs);
        scope.propPaneId = scope.propPaneId || 'paneId';
        scope.propTitle = scope.propTitle || 'title';
        scope.propActive = scope.propActive || 'active';
        scope.propDisabled = scope.propDisabled || 'disabled';
        scope.sanitize = sanitize;

        element.on('click.scrollingTabs', '.nav-tabs > li', function __handleClickOnTab(e) {
          var clickedTabElData = jQuery(this).data();

          scope.localTabClick({
            $event: e,
            $index: clickedTabElData.index,
            tab: clickedTabElData.tab
          });
        });

        scrollingTabsControl.initTabs(false); // false -> not the wrapper directive
      }

    };
  }

  /* ********************************************************
   * scrolling-tabs-wrapper Directive
   * ********************************************************/
  function scrollingTabsWrapperDirective($timeout) {
    // ------------ Directive Object ---------------------------
    return {
      restrict: 'A',
      template: scrollingTabsWrapperTemplate,
      transclude: true,
      replace: true,
      link: function(scope, element) {
        var scrollingTabsControl = new ScrollingTabsControl(scope, element, $timeout);

        scrollingTabsControl.initTabs(true); // true -> wrapper directive
      }
    };

  }

  scrollingTabsDirective.$inject = ['$timeout', '$sce'];
  scrollingTabsWrapperDirective.$inject = ['$timeout'];

  angular.module('ark-dashboard').directive('scrollingTabs', scrollingTabsDirective);
  angular.module('ark-dashboard').directive('scrollingTabsWrapper', scrollingTabsWrapperDirective);

}());

'use strict';

//angular.module('ark-dashboard')
//  .controller('widgetChart', function ($scope) {
//
//    $scope.$on('gridster-draggable-item-resizing', function () {
//      $scope.$$childTail.api.update();
//    });
//
//  });

/* jshint curly:false */
/* jshint sub:true */
/*jshint -W030 */

(function() {

    'use strict';

    angular.module('nvd3', [])

    .directive('nvd3', ['utils', function(utils) {
        return {
            restrict: 'AE',
            scope: {
                data: '=', //chart data, [required]
                options: '=', //chart options, according to nvd3 core api, [required]
                api: '=?', //directive global api, [optional]
                events: '=?', //global events that directive would subscribe to, [optional]
                config: '=?', //global directive configuration, [optional]
                chartType: '='
            },
            link: function(scope, element) {
                var defaultConfig = {
                    extended: false,
                    visible: true,
                    disabled: false,
                    autorefresh: true,
                    refreshDataOnly: false,
                    deepWatchData: true,
                    debounce: 10 // default 10ms, time silence to prevent refresh while multiple options changes at a time
                };

                //basic directive configuration
                scope._config = angular.extend(defaultConfig, scope.config);

                //directive global api
                scope.api = {
                    // Fully refresh directive
                    refresh: function() {
                        scope.api.updateWithOptions(scope.options);
                    },

                    // Update chart layout (for example if container is resized)
                    update: function() {
                        scope.chart.update();
                    },

                    // Update chart with new options
                    updateWithOptions: function(options) {
                        // Clearing
                        scope.api.clearElement();

                        // Exit if options are not yet bound
                        if (angular.isDefined(options) === false) return;

                        // Exit if chart is hidden
                        if (!scope._config.visible) return;

                        // Initialize chart with specific type
                        scope.chart = nv.models[options.chart.type]();

                        // Generate random chart ID
                        scope.chart.id = Math.random().toString(36).substr(2, 15);

                        angular.forEach(scope.chart, function(value, key) {
                            if ([
                                    'options',
                                    '_options',
                                    '_inherited',
                                    '_d3options',
                                    'state',
                                    'id',
                                    'resizeHandler'
                                ].indexOf(key) >= 0);

                            else if (key === 'dispatch') {
                                if (options.chart[key] === undefined || options.chart[key] === null) {
                                    if (scope._config.extended) options.chart[key] = {};
                                }
                                configureEvents(scope.chart[key], options.chart[key]);
                            } else if ([
                                    'lines',
                                    'lines1',
                                    'lines2',
                                    'bars',
                                    'bars1',
                                    'bars2',
                                    'stack1',
                                    'stack2',
                                    'stacked',
                                    'multibar',
                                    'discretebar',
                                    'pie',
                                    'scatter',
                                    'bullet',
                                    'sparkline',
                                    'legend',
                                    'distX',
                                    'distY',
                                    'xAxis',
                                    'x2Axis',
                                    'yAxis',
                                    'yAxis1',
                                    'yAxis2',
                                    'y1Axis',
                                    'y2Axis',
                                    'y3Axis',
                                    'y4Axis',
                                    'interactiveLayer',
                                    'controls'
                                ].indexOf(key) >= 0) {
                                if (options.chart[key] === undefined || options.chart[key] === null) {
                                    if (scope._config.extended) options.chart[key] = {};
                                }
                                configure(scope.chart[key], options.chart[key], options.chart.type);
                            }

                            //TODO: need to fix bug in nvd3
                            else if ((key === 'xTickFormat' || key === 'yTickFormat') && options.chart.type === 'lineWithFocusChart');

                            else if (options.chart[key] === undefined || options.chart[key] === null) {
                                if (scope._config.extended) options.chart[key] = value();
                            } else scope.chart[key](options.chart[key]);
                        });

                        // Update with data
                        scope.api.updateWithData(scope.data);

                        // Configure wrappers
                        if (options['title'] || scope._config.extended) configureWrapper('title');
                        if (options['subtitle'] || scope._config.extended) configureWrapper('subtitle');
                        if (options['caption'] || scope._config.extended) configureWrapper('caption');


                        // Configure styles
                        if (options['styles'] || scope._config.extended) configureStyles();

                        nv.addGraph(function() {
                            // Update the chart when window resizes
                            scope.chart.resizeHandler = nv.utils.windowResize(function() {
                                scope.chart.update();
                            });
                            return scope.chart;
                        }, options.chart['callback']);
                    },

                    // Update chart with new data
                    updateWithData: function(data) {
                        if (data) {
                            scope.options.chart['transitionDuration'] = +scope.options.chart['transitionDuration'] || 250;
                            // remove whole svg element with old data
                            d3.select(element[0]).select('svg').remove();

                            // Select the current element to add <svg> element and to render the chart in
                            d3.select(element[0]).append('svg')
                                .attr('height', scope.options.chart.height)
                                .attr('width', scope.options.chart.width || '100%')
                                .datum(data)
                                .transition().duration(scope.options.chart['transitionDuration'])
                                .call(scope.chart);
                        }
                    },

                    // Fully clear directive element
                    clearElement: function() {
                        element.find('.title').remove();
                        element.find('.subtitle').remove();
                        element.find('.caption').remove();
                        element.empty();
                        if (scope.chart) {
                            // clear window resize event handler
                            if (scope.chart.resizeHandler) scope.chart.resizeHandler.clear();

                            // remove chart from nv.graph list
                            for (var i = 0; i < nv.graphs.length; i++)
                                if (nv.graphs[i].id === scope.chart.id) {
                                    nv.graphs.splice(i, 1);
                                }
                        }
                        scope.chart = null;
                        nv.tooltip.cleanup();
                    },

                    // Get full directive scope
                    getScope: function() {
                        return scope;
                    }
                };

                // Configure the chart model with the passed options
                function configure(chart, options) {
                    if (chart && options) {
                        angular.forEach(chart, function(value, key) {
                            if (key === 'dispatch') {
                                if (options[key] === undefined || options[key] === null) {
                                    if (scope._config.extended) options[key] = {};
                                }
                                configureEvents(value, options[key]);
                            } else if ([
                                    'scatter',
                                    'defined',
                                    'options',
                                    'axis',
                                    'rangeBand',
                                    'rangeBands',
                                    '_options',
                                    '_inherited',
                                    '_d3options',
                                    '_calls'
                                ].indexOf(key) < 0) {
                                if (options[key] === undefined || options[key] === null) {
                                    if (scope._config.extended) options[key] = value();
                                } else chart[key](options[key]);
                            }
                        });
                    }
                }

                // Subscribe to the chart events (contained in 'dispatch')
                // and pass eventHandler functions in the 'options' parameter
                function configureEvents(dispatch, options) {
                    if (dispatch && options) {
                        angular.forEach(dispatch, function(value, key) {
                            if (options[key] === undefined || options[key] === null) {
                                if (scope._config.extended) options[key] = value.on;
                            } else dispatch.on(key + '._', options[key]);
                        });
                    }
                }

                // Configure 'title', 'subtitle', 'caption'.
                // nvd3 has no sufficient models for it yet.
                function configureWrapper(name) {
                    var _ = utils.deepExtend(defaultWrapper(name), scope.options[name] || {});

                    if (scope._config.extended) scope.options[name] = _;

                    var wrapElement = angular.element('<div></div>').html(_['html'] || '')
                        .addClass(name).addClass(_.class)
                        .removeAttr('style')
                        .css(_.css);

                    if (!_['html']) wrapElement.text(_.text);

                    if (_.enable) {
                        if (name === 'title') element.prepend(wrapElement);
                        else if (name === 'subtitle') element.find('.title').after(wrapElement);
                        else if (name === 'caption') element.append(wrapElement);
                    }
                }

                // Add some styles to the whole directive element
                function configureStyles() {
                    var _ = utils.deepExtend(defaultStyles(), scope.options['styles'] || {});

                    if (scope._config.extended) scope.options['styles'] = _;

                    angular.forEach(_.classes, function(value, key) {
                        value ? element.addClass(key) : element.removeClass(key);
                    });

                    element.removeAttr('style').css(_.css);
                }

                // Default values for 'title', 'subtitle', 'caption'
                function defaultWrapper(_) {
                    switch (_) {
                        case 'title':
                            return {
                                enable: false,
                                text: 'Write Your Title',
                                class: 'h4',
                                css: {
                                    width: scope.options.chart.width + 'px',
                                    textAlign: 'center'
                                }
                            };
                        case 'subtitle':
                            return {
                                enable: false,
                                text: 'Write Your Subtitle',
                                css: {
                                    width: scope.options.chart.width + 'px',
                                    textAlign: 'center'
                                }
                            };
                        case 'caption':
                            return {
                                enable: false,
                                text: 'Figure 1. Write Your Caption text.',
                                css: {
                                    width: scope.options.chart.width + 'px',
                                    textAlign: 'center'
                                }
                            };
                    }
                }

                // Default values for styles
                function defaultStyles() {
                    return {
                        classes: {
                            'with-3d-shadow': true,
                            'with-transitions': true,
                            'gallery': false
                        },
                        css: {}
                    };
                }

                /* Event Handling */
                // Watching on options changing
                scope.$watch('options', utils.debounce(function() {
                    if (!scope._config.disabled && scope._config.autorefresh) scope.api.refresh();
                }, scope._config.debounce, true), true);

                // Watching on data changing
                scope.$watch('data', function(newData, oldData) {
                    if (newData !== oldData && scope.chart) {
                        if (!scope._config.disabled && scope._config.autorefresh) {
                            scope._config.refreshDataOnly ? scope.chart.update() : scope.api.refresh(); // if wanted to refresh data only, use chart.update method, otherwise use full refresh.
                        }
                    }
                }, scope._config.deepWatchData);

                // Watching on config changing
                scope.$watch('config', function(newConfig, oldConfig) {
                    if (newConfig !== oldConfig) {
                        scope._config = angular.extend(defaultConfig, newConfig);
                        scope.api.refresh();
                    }
                }, true);

                //subscribe on global events
                angular.forEach(scope.events, function(eventHandler, event) {
                    scope.$on(event, function(e) {
                        return eventHandler(e, scope);
                    });
                });

                // remove completely when directive is destroyed
                element.on('$destroy', function() {
                    scope.api.clearElement();
                });
            }
        };
    }])

    .factory('utils', function() {
        return {
            debounce: function(func, wait, immediate) {
                var timeout;
                return function() {
                    var context = this,
                        args = arguments;
                    var later = function() {
                        timeout = null;
                        if (!immediate) func.apply(context, args);
                    };
                    var callNow = immediate && !timeout;
                    clearTimeout(timeout);
                    timeout = setTimeout(later, wait);
                    if (callNow) func.apply(context, args);
                };
            },
            deepExtend: function(dst) {
                var me = this;
                angular.forEach(arguments, function(obj) {
                    if (obj !== dst) {
                        angular.forEach(obj, function(value, key) {
                            if (dst[key] && dst[key].constructor && dst[key].constructor === Object) {
                                me.deepExtend(dst[key], value);
                            } else {
                                dst[key] = value;
                            }
                        });
                    }
                });
                return dst;
            }
        };
    });
})();

'use strict';

/*angular.module('ark-dashboard')
  .directive('widgetChart', function ($compile, $timeout) {
    return {
      restrict: 'E',
      scope: {
        widget: '='
      },
      link: function (scope, element) {
        // !! We don't need this directive !!
        element.html('<div ' + scope.widget.directive + '></div>'); //Current widget directives are attributes
        scope.loading = true;
        var el = $compile(element.contents())(scope);
        if (el) {
          scope.loading = false;
        }
      }
    };
  });*/

angular.module('ark-dashboard').run(['$templateCache', function($templateCache) {
  'use strict';

$templateCache.put('src/dashboard/template/dashboard-layouts.html',
    "<div scrolling-tabs-wrapper>\n" +
    "  <ul ui-sortable=\"sortableOptions\" ng-model=\"layouts\" class=\"nav nav-tabs layout-tabs\">\n" +
    "    <li ng-repeat=\"layout in layouts\" ng-click=\"makeLayoutActive(layout)\" ng-class=\"{ active: layout.active }\" class=\"tabs-item nav-tabs-layout\">\n" +
    "      <a ng-init=\"addTooptip()\">\n" +
    "          <span ng-if=\"layout.locked\" class=\"tabs-icon fonticon icon-secure\"></span>\n" +
    "          <span ng-if=\"layout.type === 'widget'\" class=\"tabs-icon fonticon icon-dashtab-dash\"></span>\n" +
    "          <span ng-if=\"layout.type === 'expand'\" class=\"tabs-icon fonticon icon-dashtab-xwidget\"></span>\n" +
    "          <span class=\"tabs-title\" ng-if=\"layout.showTooltip\" tooltip-placement=\"bottom\" tooltip=\"{{layout.title}}\" tooltip-popup-delay=\"500\">{{layout.title}}</span>\n" +
    "          <span class=\"tabs-title\" ng-if=\"!layout.showTooltip\">{{layout.title}}</span>\n" +
    "      </a>\n" +
    "      <div class=\"nav-tabs-collapse\">\n" +
    "          <ul class=\"nav\">\n" +
    "              <li class=\"ark-dropdown dropdown\">\n" +
    "                  <a ng-if=\"!layout.active\" ng-click=\"makeLayoutActive(layout)\" class=\"ark-dropdown-toggle nav-tabs-dropdown\"><i class=\"icon-more\"></i></a>\n" +
    "                  <a ng-if=\"layout.active\" href=\"#\" role=\"button\" class=\"ark-dropdown-toggle nav-tabs-dropdown\"><i class=\"icon-more\"></i></a>\n" +
    "                  <ul ng-if=\"layout.active\" class=\"dropdown-menu nav-tabs-dropdown-menu dropdown-menu-pull-left\" role=\"menu\" dropdown-menu menu=\"layoutList.list\" layout-actions=\"layoutList.actions\" default-layout-actions=\"defaultLayoutActions\"></ul>\n" +
    "              </li>\n" +
    "          </ul>\n" +
    "      </div>\n" +
    "    </li>\n" +
    "    <li>\n" +
    "        <a ng-click=\"createNewLayout()\" class=\"tabs-add-button\">\n" +
    "            <span class=\"fonticon icon-add\"></span>\n" +
    "        </a>\n" +
    "    </li>\n" +
    "  </ul>\n" +
    "</div>\n" +
    "<div  ng-repeat=\"layout in layouts | filter:isActive\" >\n" +
    "  <div ng-if=\"layout.type === 'widget'\" dashboard=\"layout.dashboard\" template-url=\"src/dashboard/template/dashboard.html\"></div>\n" +
    "  <div ng-if=\"layout.type === 'expand'\"expand-to-tab=\"layout.dashboard\" template-url=\"src/dashboard/template/expand-to-tab.html\"></div>\n" +
    "</div>\n"
);


$templateCache.put('src/dashboard/template/dashboard.html',
    "<div>\n" +
    "  <!--  gridster layout START -->\n" +
    "  <div gridster=\"gridsterOpts\" class=\"dashboard-widget-area\">\n" +
    "    <ul>\n" +
    "      <li gridster-item=\"widget\" ng-repeat=\"widget in widgets\" ng-style=\"widget.containerStyle\" class=\"widget-container\">\n" +
    "\n" +
    "        <!-- START: Widget Container -->\n" +
    "\n" +
    "        <div class=\"widget\">\n" +
    "          <div class=\"widget-controls\">\n" +
    "            <div class=\"widget-drag-button\">\n" +
    "              <span class=\"fonticon icon-grab widget-anchor\"></span>\n" +
    "            </div>\n" +
    "            <div class=\"nav-tabs-collapse\">\n" +
    "              <ul class=\"nav\">\n" +
    "                <li class=\"ark-dropdown dropdown\">\n" +
    "                  <a role=\"button\" class=\"ark-dropdown-toggle nav-tabs-dropdown\"><i class=\"icon-more\"></i></a>\n" +
    "                  <ul class=\"dropdown-menu nav-tabs-dropdown-menu dropdown-menu-pull-left\"  role=\"menu\" dropdown-menu menu=\"widgetList.list\" widget-actions=\"widgetList.actions\" widget=\"widget\" default-widget-actions=\"defaultWidgetActions\"></ul>\n" +
    "                </li>\n" +
    "              </ul>\n" +
    "            </div>\n" +
    "          </div>\n" +
    "          <div class=\"widget-title\">\n" +
    "              <div class=\"widget-name-text\">{{widget.attrs.description}}</div>\n" +
    "              <div class=\"widget-title-text\" ng-div=\"widget.editingTitle\">{{widget.title}}</label>\n" +
    "              </div>\n" +
    "          </div>\n" +
    "\n" +
    "          <div class=\"widget-content\">\n" +
    "              <div ng-controller=\"widgetChart\" style='height:calc(100% - 40px)' slimscroll=\"{height: \'100%\', width: \'185\'}\">\n" +
    "                  <widget-chart widget='widget' ng-hide=\"loading\"></widget-chart>\n" +
    "                     <div class=\"spinner-container fast-spinner widget-spinner\" ng-show=\"loading\">\n" +
    "                       <div class=\"spin-circle\"></div>\n" +
    "                       <div class=\"spin-inner-circle\"></div>\n" +
    "                     </div>\n" +
    "              </div>\n" +
    "          </div>\n" +
    "        <!-- END: Widget Container -->\n" +
    "      </li>\n" +
    "    </ul>\n" +
    "  </div>\n" +
    "</div>\n"
);


  $templateCache.put('src/dashboard/template/expand-to-tab.html',
    "<div>\r" +
    "\n" +
    "  <!--  gridster layout START -->\r" +
    "\n" +
    "  <div gridster=\"gridsterOpts\" class=\"dashboard-widget-area\">\r" +
    "\n" +
    "    <ul>\r" +
    "\n" +
    "      <li gridster-item=\"expand\" class=\"widget-container\">\r" +
    "\n" +
    "\r" +
    "\n" +
    "        <!-- START: Widget Container -->\r" +
    "\n" +
    "\r" +
    "\n" +
    "        <div class=\"expand\">\r" +
    "\n" +
    "          <div class=\"expand-title\">\r" +
    "\n" +
    "              <div class=\"expand-title-text\">{{expand.title}}</label>\r" +
    "\n" +
    "              </div>\r" +
    "\n" +
    "              <div class=\"expand-icons\">\r" +
    "\n" +
    "                <i class=\"active fonticon icon-24-graph-bar\"></i>\r" +
    "\n" +
    "                <i class=\"fonticon icon-24-graph-line\"></i>\r" +
    "\n" +
    "                <i class=\"fonticon icon-24-graph-stack\"></i>\r" +
    "\n" +
    "                <i class=\"fonticon icon-24-graph-grid\"></i>\r" +
    "\n" +
    "              </div>\r" +
    "\n" +
    "          </div>\r" +
    "\n" +
    "          <div class=\"exapnd-content\">\r" +
    "\n" +
    "            <div class=\"expand-graph\">\r" +
    "\n" +
    "              <nvd3 options=\"expand.chartOptions\" data=\"expand.chartData\"></nvd3>\r" +
    "\n" +
    "            </div>\r" +
    "\n" +
    "            <div class=\"expand-info\">\r" +
    "\n" +
    "              <json-tree json=\"expand.chartOptions\" edit-level=\"high\" collapsed-level=\"2\" ></json-tree>\r" +
    "\n" +
    "            </div>\r" +
    "\n" +
    "          </div>\r" +
    "\n" +
    "\r" +
    "\n" +
    "        <!-- END: Widget Container -->\r" +
    "\n" +
    "\r" +
    "\n" +
    "      </li>\r" +
    "\n" +
    "    </ul>\r" +
    "\n" +
    "  </div>\r" +
    "\n" +
    "</div>\r" +
    "\n"
  );


  $templateCache.put('src/dashboard/template/rename-template.html',
    "<div class=\"modal-header\">\r" +
    "\n" +
    "    <span ng-click=\"cancel()\" class=\"icon-close close modal-dialog-close\"></span>\r" +
    "\n" +
    "  <h1 class=\"modal-header\">Rename {{type}}</h1>\r" +
    "\n" +
    "</div>\r" +
    "\n" +
    "\r" +
    "\n" +
    "<div class=\"modal-body\">\r" +
    "\n" +
    "  <form name=\"form\" role=\"form\" class=\"form-horizontal\">\r" +
    "\n" +
    "    <div class=\"form-group\" ng-class=\"{ 'has-error': !form.title.$valid }\">\r" +
    "\n" +
    "      <div class=\"col-sm-10\">\r" +
    "\n" +
    "        <input type=\"text\" class=\"form-control\" name=\"title\" ui-validate=\"{empty:'$value'}\" ng-model=\"title\" select-text>\r" +
    "        <span class=\"help-block red\" ng-if=\"form.title.$error.empty\">Please enter a name</span>\r" +
    "\n" +
    "      </div>\r" +
    "\n" +
    "    </div>\r" +
    "\n" +
    "  </form>\r" +
    "\n" +
    "</div>\r" +
    "\n" +
    "\r" +
    "\n" +
    "<div class=\"modal-footer\">\r" +
    "\n" +
    "  <button type=\"button\" class=\"btn btn-default\" ng-click=\"cancel()\">Cancel</button>\r" +
    "\n" +
    "  <button type=\"button\" class=\"btn btn-primary\" ng-disabled=\"!form.$valid || title === ''\" ng-click=\"ok()\">Rename</button>\r" +
    "\n" +
    "</div>"
  );


  $templateCache.put('src/dashboard/template/save-changes-modal.html',
    "<div class=\"modal-header\">\n" +
    "\t<button type=\"button\" class=\"close\" data-dismiss=\"modal\" aria-hidden=\"true\" ng-click=\"cancel()\">&times;</button>\n" +
    "  <h3>Unsaved Changes to \"{{layout.title}}\"</h3>\n" +
    "</div>\n" +
    "\n" +
    "<div class=\"modal-body\">\n" +
    "  <p>You have {{layout.dashboard.unsavedChangeCount}} unsaved changes on this dashboard. Would you like to save them?</p>\n" +
    "</div>\n" +
    "\n" +
    "<div class=\"modal-footer\">\n" +
    "  <button type=\"button\" class=\"btn btn-default\" ng-click=\"cancel()\">Don't Save</button>\n" +
    "  <button type=\"button\" class=\"btn btn-primary\" ng-click=\"ok()\">Save</button>\n" +
    "</div>"
  );


  $templateCache.put('src/dashboard/template/widget-default-content.html',
    ""
  );


  $templateCache.put('src/dashboard/components/dropdown-menu/dropdown-menu.html',
    "<li ng-repeat=\"item in menu\" style=\"cursor:pointer;\" role=\"presentation\" ng-controller=\"dropdownMenuController\">\r" +
    "\n" +
    " <a role=\"menuitem\" tabindex=\"-1\" ng-if=\"item.requireConfirmPopup\" tooltip-placement=\"top\" tooltip=\"{{item.tooltip}}\" ng-click=\"handleMenuOption(item.menuOptionKey)\">\r" +
    "\n" +
    "    <i class=\"icon {{item.menuIcon}}\"></i> {{item.menuLocalizedTitle}}\r" +
    "\n" +
    "  </a>\r" +
    "  <a role=\"menuitem\" tabindex=\"-1\" ng-if=\"!item.requireConfirmPopup\" ng-click=\"handleMenuOption(item.menuOptionKey)\">\r" +
    "\n" +
    "    <i class=\"icon {{item.menuIcon}}\"></i> {{item.menuLocalizedTitle}}\r" +
    "\n" +
    "  </a>\r" +
    "\n" +
    "</li>\r" +
    "\n"
  );

}]);
