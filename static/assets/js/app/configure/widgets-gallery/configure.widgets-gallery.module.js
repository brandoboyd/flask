(function () {
  'use strict';

  angular
    .module('slr.configure')
    .config(function ($routeProvider) {
      $routeProvider
        .when('/gallery', {
          templateUrl: '/partials/widget_gallery/list',
          controller: 'GalleriesCtrl',
          name: 'gallery'
        })
        .when('/gallery/:id', {
          templateUrl: '/partials/widget_gallery/widget_model_list',
          controller: 'WidgetsGalleryCtrl',
          name: 'gallery'
        })
        .when('/gallery/:gallery_id/widget_model/:id?', {
          templateUrl: '/partials/widget_gallery/widget_model_edit',
          controller: 'WidgetModelCRUDCtrl',
          name: 'widget_models'
        })
    })
})();