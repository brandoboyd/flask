(function () {
  'use strict';

  angular
    .module('slr.services')
    .factory('PopupService', function ($http, $compile) {
      var popupService = {};

      // Get the popup
      popupService.getPopup = function (create) {
        if (!popupService.popupElement && create) {
          popupService.popupElement = $('<div class="modal"></div>');
          popupService.popupElement.appendTo('BODY');
        }

        return popupService.popupElement;
      };

      popupService.compileAndRunPopup = function (popup, scope, options) {
        $compile(popup)(scope);
        popup.modal(options);
      };

      // Is it ok to have the html here? should all this go in the directives? Is there another way
      // get the html out of here?
      popupService.alert = function (title, text, buttonText, alertFunction, scope, options) {
        text = (text) ? text : "Alert";
        buttonText = (buttonText) ? buttonText : "Ok";
        var alertHTML = "<div class=\"modal-dialog\"><div class=\"modal-content\">";
        if (title) {
          alertHTML += "<div class=\"modal-header\"><h1>" + title + "</h1></div>";
        }
        alertHTML += "<div class=\"modal-body\">" + text + "</div>"
          + "<div class=\"modal-footer\">";
        if (alertFunction) {
          alertHTML += "<button class=\"btn btn-default\" ng-click=\"" + alertFunction + "\">" + buttonText + "</button>";
        }
        else {
          alertHTML += "<button class=\"btn btn-default\">" + buttonText + "</button>";
        }
        alertHTML += "</div></div></div>";
        var popup = popupService.getPopup(true);
        popup.html(alertHTML);
        if (!alertFunction) {
          popup.find(".btn").click(function () {
            popupService.close();
          });
        }

        popupService.compileAndRunPopup(popup, scope, options);
      };

      // Is it ok to have the html here? should all this go in the directives? Is there another way
      // get the html out of here?
      popupService.confirm = function (title, actionText, actionButtonText, actionFunction, cancelButtonText, cancelFunction, scope, options) {
        actionText = (actionText) ? actionText : "Are you sure?";
        actionButtonText = (actionButtonText) ? actionButtonText : "Ok";
        cancelButtonText = (cancelButtonText) ? cancelButtonText : "Cancel";

        var popup = popupService.getPopup(true);
        var confirmHTML = "<div class=\"modal-dialog\"><div class=\"modal-content\">";
        if (title) {
          confirmHTML += "<div class=\"modal-header\"><h1>" + title + "</h1></div>";
        }
        confirmHTML += "<div class=\"modal-body\">" + actionText + "</div>"
          + "<div class=\"modal-footer\">";
        if (cancelFunction) {
          confirmHTML += "<button class=\"btn btn-cancel\" ng-click=\"" + cancelFunction + "\">" + cancelButtonText + "</button>";
        }
        else {
          confirmHTML += "<button class=\"btn btn-cancel\">" + cancelButtonText + "</button>";
        }
        if (actionFunction) {
          confirmHTML += "<button class=\"btn btn-primary\" ng-click=\"" + actionFunction + "\">" + actionButtonText + "</button>";
        }
        else {
          confirmHTML += "<button class=\"btn btn-primary\">" + actionButtonText + "</button>";
        }
        confirmHTML += "</div></div></div>";
        popup.html(confirmHTML);
        if (!actionFunction || options.closeAfterAction) {
          popup.find(".btn-primary").click(function () {
            popupService.close();
          });
        }
        if (!cancelFunction) {
          popup.find(".btn-cancel").click(function () {
            popupService.close();
          });
        }
        popupService.compileAndRunPopup(popup, scope, options);

      };

      // Loads the popup
      popupService.load = function (url, scope, options) {
        $http.get(url).success(function (data) {
          var popup = popupService.getPopup(true);
          popup.html(data);
          popupService.compileAndRunPopup(popup, scope, options);
        });
      };

      popupService.close = function () {
        var popup = popupService.getPopup();
        if (popup) {
          popup.modal('hide');
        }
      };

      return popupService;
    }); 
})();