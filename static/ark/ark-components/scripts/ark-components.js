'use strict';
angular.module('underscore', []).factory('_', function () {
  return window._;  // assumes underscore has already been loaded on the page
});
'use strict';
angular.module('ark-components', [
  'ngCookies',
  'ngSanitize',
  'underscore'
]);
angular.module('ark-components').run([
  '$templateCache',
  function ($templateCache) {
    'use strict';
    $templateCache.put('ark-app-launcher/ark-app-launcher.html', '<nav class="ark-app-launcher navbar navbar-default" role="navigation">\n' + '  <div class="container-fluid">\n' + '    <!-- Brand and toggle get grouped for better mobile display -->\n' + '    <div id="nav_header" class="navbar-header">\n' + '      <a class="navbar-brand" href="#">\n' + '        <span class="fonticon icon-special-g-brandmark"></span>\n' + '        <span>{{ currentAppName }}</span>\n' + '      </a>\n' + '    </div>\n' + '\n' + '    <!-- Collect the nav links, forms, and other content for toggling -->\n' + '    <div class="collapse navbar-collapse">\n' + '      <ul class="nav navbar-nav navbar-right">\n' + '        <!-- User Menu -->\n' + '        <li class="dropdown">\n' + '          <a href data-toggle="dropdown">{{ user.name | truncate:false:25 }}</a>\n' + '          <ul class="dropdown-menu">\n' + '            <li ng-if="aboutApplication">\n' + '              <a href ng-click="aboutApplication()">{{ localization.localizedStrings.ABOUT }} {{ currentAppName }}</a>\n' + '            </li>\n' + '            <li ng-if="aboutApplication" class="divider"></li>\n' + '            <li ng-repeat="item in usermenu" ng-if="!item.disable" ng-class="{divider: item.isDivider}">\n' + '              <a ng-if="!item.isDivider && !item.customAction" ng-href="{{ item.url }}" ng-attr-target="{{ item.target }}">\n' + '                {{ item.name }}\n' + '              </a>\n' + '              <a ng-if="!item.isDivider && item.customAction" href ng-click="customAction(item)">\n' + '                {{ item.name }}\n' + '              </a>\n' + '            </li>\n' + '          </ul>\n' + '        </li>\n' + '        <!-- Localization -->\n' + '        <li class="dropdown" ng-if="localization">\n' + '          <a href class="dropdown-toggle" data-toggle="dropdown">\n' + '            <div ng-class="localizationIcons[currentLanguage.id]"></div>\n' + '            {{ currentLanguage.shortName }}\n' + '          </a>\n' + '          <ul class="dropdown-menu">\n' + '            <li ng-repeat="language in localization.languages">\n' + '              <a href ng-click="changeLanguage(language.id)">\n' + '                <div ng-class="localizationIcons[language.id]"></div>\n' + '                {{ language.localizedName }}\n' + '              </a>\n' + '            </li>\n' + '          </ul>\n' + '        </li>\n' + '        <!-- Help -->\n' + '        <li ng-if="helpmenu">\n' + '          <a ng-href="{{ helpmenu.getUrl() }}" ng-attr-target="{{ helpmenu.target }}">\n' + '            <span ng-if="helpmenu.fonticon" class="fonticon"\n' + '            ng-class="helpmenu.fonticon"\n' + '            ng-attr-title="{{ helpmenu.name }}"></span>\n' + '          </a>\n' + '        </li>\n' + '        <!-- App Launcher -->\n' + '        <li class="app-launcher-dropdown dropdown" ng-if="appLauncherEnable && appGroups">\n' + '          <a href class="dropdown-toggle" data-toggle="dropdown">\n' + '            <span title="App Launcher">\n' + '              <span class="fonticon icon-dialpad"></span>\n' + '            </span>\n' + '          </a>\n' + '          <ul class="dropdown-menu">\n' + '            <li ng-repeat-start="(name, apps) in appGroups" class="title">{{ name }}</li>\n' + '            <li ng-repeat="app in apps">\n' + '              <a href ng-href="{{ app.links[0].url }}" target="_blank">\n' + '                <img ng-src="{{ baseUrlAssets }}{{ app.image32 }}">\n' + '                <span>{{ app.name }}</span>\n' + '              </a>\n' + '            </li>\n' + '            <li ng-repeat-end class="divider"></li>\n' + '            <li ng-if="false">\n' + '              <a href>\n' + '                <span class="fonticon icon-dialpad" style="font-size: 24px"></span>\n' + '                {{ localization.localizedStrings.ALL_APPS }}\n' + '              </a>\n' + '            </li>\n' + '          </ul>\n' + '        </li>\n' + '      </ul>\n' + '    </div><!-- /.navbar-collapse -->\n' + '  </div><!-- /.container-fluid -->\n' + '</nav>\n');
    $templateCache.put('ark-datepicker/ark-datepicker-popup-wrap.html', '<ul class="dropdown-menu ark-datepicker-wrap" ng-style="{display: (isOpen && \'block\') || \'none\', top: position.top+\'px\', left: position.left+\'px\'}">\n' + '  <li ng-transclude></li>\n' + '  <li ng-if="showButtonBar" style="padding:10px 9px 2px">\n' + '    <span class="btn-group">\n' + '      <button type="button" class="btn btn-sm btn-info" ng-click="select(\'today\')">{{ getText(\'current\') }}</button>\n' + '      <button type="button" class="btn btn-sm btn-danger" ng-click="select(null)">{{ getText(\'clear\') }}</button>\n' + '    </span>\n' + '    <button type="button" class="btn btn-sm btn-success pull-right" ng-click="$parent.isOpen = false">{{ getText(\'close\') }}</button>\n' + '  </li>\n' + '</ul>\n');
    $templateCache.put('ark-datepicker/ark-datepicker.html', '<div ng-switch="datepickerMode" class="ark-datepicker">\n' + '  <ark-daypicker ng-switch-when="day"></ark-daypicker>\n' + '  <ark-monthpicker ng-switch-when="month"></ark-monthpicker>\n' + '  <ark-yearpicker ng-switch-when="year"></ark-yearpicker>\n' + '</div>\n');
    $templateCache.put('ark-datepicker/ark-daypicker.html', '<div class="day-view text-center">\n' + '  <div class="month-index">\n' + '    <table>\n' + '      <thead>\n' + '        <tr>\n' + '          <th>\n' + '            <button type="button" class="btn btn-default btn-sm pull-left" ng-click="move(-1)">\n' + '              <i class="fonticon icon-chevron-left"></i>\n' + '            </button>\n' + '          </th>\n' + '          <th colspan="{{ 5 + showWeeks }}">\n' + '            <button type="button" class="btn btn-default btn-sm btn-block" ng-click="toggleMode()">\n' + '              <strong>{{ title }}</strong>\n' + '            </button>\n' + '          </th>\n' + '          <th>\n' + '            <button type="button" class="btn btn-default btn-sm pull-right" ng-click="move(1)">\n' + '              <i class="fonticon icon-chevron-right"></i>\n' + '            </button>\n' + '          </th>\n' + '        </tr>\n' + '      </thead>\n' + '    </table>\n' + '  </div>\n' + '  <div class="day-table">\n' + '    <table>\n' + '      <thead>\n' + '        <tr class="ark-datepicker-labels">\n' + '          <th ng-show="showWeeks" class="text-center"></th>\n' + '          <th ng-repeat="label in labels track by $index" class="text-center day-label">\n' + '            <small>{{ label }}</small>\n' + '          </th>\n' + '        </tr>\n' + '      </thead>\n' + '      <tbody>\n' + '        <tr ng-repeat="row in rows track by $index">\n' + '          <td ng-show="showWeeks" class="text-center">\n' + '            <small><em>{{ weekNumbers[$index] }}</em></small>\n' + '          </td>\n' + '          <td ng-repeat="dt in row track by dt.date" class="text-center">\n' + '            <button type="button" style="width:100%;" class="btn btn-default btn-sm" ng-class="{\'btn-info\': dt.selected}" ng-click="select(dt.date)" ng-disabled="dt.disabled">\n' + '              <span ng-class="{\'text-muted\': dt.secondary, \'text-info\': dt.current}">\n' + '                {{ dt.label }}\n' + '              </span>\n' + '            </button>\n' + '          </td>\n' + '        </tr>\n' + '      </tbody>\n' + '    </table>\n' + '  </div>\n' + '  <div class="ark-timepicker calendar-timepicker" ng-if="timepickerMode">\n' + '    <div class="timepicker-content" ng-show="!timeZoneShow">\n' + '      <div class="col-container first">\n' + '        <div class="icon-iw-circle-no-chevron-up arrow" while-pressed="addHour()"></div>\n' + '        <div class="dropdown open">\n' + '          <input type="text" maxlength="2" ng-model="timeData.hour" ng-click="showHour()" ng-blur="validateHour()">\n' + '          <ul ng-show="showHourList" class="dropdown-menu">\n' + '            <li ng-repeat="list in hourList">\n' + '              <a href ng-mousedown="selectHour(list)" ng-class="{selected: list === hour}">\n' + '              {{ list }}\n' + '              </a>\n' + '            </li>\n' + '          </ul>\n' + '        </div>\n' + '        <div class="icon-iw-circle-no-chevron-down arrow" while-pressed="minusHour()"></div>\n' + '      </div>\n' + '      <div class="col-container column"><b>:</b></div>\n' + '      <div class="col-container">\n' + '        <div class="icon-iw-circle-no-chevron-up arrow" while-pressed="addMinute()"></div>\n' + '        <div class="dropdown open">\n' + '          <input type="text" maxlength="2" ng-model="timeData.minute" ng-click="showMinute()" ng-blur="validateMinute()">\n' + '          <ul ng-show="showMinuteList" class="dropdown-menu">\n' + '            <li ng-repeat="list in minuteList">\n' + '              <a href ng-mousedown="selectMinute(list)" ng-class="{selected: list===minute}">\n' + '              {{ list }}\n' + '              </a>\n' + '            </li>\n' + '          </ul>\n' + '        </div>\n' + '        <div class="icon-iw-circle-no-chevron-down arrow" while-pressed="minusMinute()"></div>\n' + '      </div>\n' + '      <div class="col-container last">\n' + '        <div class="icon-iw-circle-no-chevron-up arrow" ng-click="changeNoon()"></div>\n' + '        <input type="text" maxlength="2" ng-model="timeData.noon" ng-blur="validateNoon()" readonly>\n' + '        <div class="icon-iw-circle-no-chevron-down arrow" ng-click="changeNoon()"></div>\n' + '      </div>\n' + '      <div class="col-container last timepicker-button" ng-if="timezoneMode" ng-click="toggleTimeZone()">\n' + '        <span class="fonticon icon-clock-timezone"></span>\n' + '      </div>\n' + '    </div>\n' + '    <div class="timepicker-content" ng-if="timezoneMode" ng-show="timeZoneShow">\n' + '      <div class="col-container">\n' + '        <div class="icon-iw-circle-no-chevron-up arrow timezone" ng-click="addTimeZone()"></div>\n' + '        <div class="dropdown open">\n' + '          <input type="text" class="timezone" maxlength="9" ng-model="timeData.timeZone" ng-click="showTimeZone()" ng-blur="validateTimeZone()" readonly>\n' + '          <ul ng-show="showTimeZoneList" class="dropdown-menu timezone">\n' + '            <li ng-repeat="list in timeZoneList">\n' + '              <a href ng-mousedown="selectTimeZone(list, $index)" class="timezone" ng-class="{selected: list === timeZone}">\n' + '              {{ list }}\n' + '              </a>\n' + '            </li>\n' + '          </ul>\n' + '        </div>\n' + '        <div class="icon-iw-circle-no-chevron-down arrow timezone" ng-click="minusTimeZone()"></div>\n' + '      </div>\n' + '      <div class="col-container last timepicker-button" ng-click="toggleTimeZone()">\n' + '        <span class="fonticon icon-clock"></span>\n' + '      </div>\n' + '    </div>\n' + '  </div>\n' + '</div>\n');
    $templateCache.put('ark-datepicker/ark-monthpicker.html', '<table>\n' + '  <thead>\n' + '    <tr>\n' + '      <th><button type="button" class="btn btn-default btn-sm pull-left" ng-click="move(-1)"><i class="glyphicon glyphicon-chevron-left"></i></button></th>\n' + '      <th><button type="button" class="btn btn-default btn-sm btn-block" ng-click="toggleMode()"><strong>{{title}}</strong></button></th>\n' + '      <th><button type="button" class="btn btn-default btn-sm pull-right" ng-click="move(1)"><i class="glyphicon glyphicon-chevron-right"></i></button></th>\n' + '    </tr>\n' + '  </thead>\n' + '  <tbody>\n' + '    <tr ng-repeat="row in rows track by $index">\n' + '      <td ng-repeat="dt in row track by dt.date" class="text-center">\n' + '        <button type="button" style="width:100%;" class="btn btn-default" ng-class="{\'btn-info\': dt.selected}" ng-click="select(dt.date)" ng-disabled="dt.disabled"><span ng-class="{\'text-info\': dt.current}">{{dt.label}}</span></button>\n' + '      </td>\n' + '    </tr>\n' + '  </tbody>\n' + '</table>\n');
    $templateCache.put('ark-datepicker/ark-yearpicker.html', '<table>\n' + '  <thead>\n' + '    <tr>\n' + '      <th><button type="button" class="btn btn-default btn-sm pull-left" ng-click="move(-1)"><i class="glyphicon glyphicon-chevron-left"></i></button></th>\n' + '      <th colspan="3"><button type="button" class="btn btn-default btn-sm btn-block" ng-click="toggleMode()"><strong>{{title}}</strong></button></th>\n' + '      <th><button type="button" class="btn btn-default btn-sm pull-right" ng-click="move(1)"><i class="glyphicon glyphicon-chevron-right"></i></button></th>\n' + '    </tr>\n' + '  </thead>\n' + '  <tbody>\n' + '    <tr ng-repeat="row in rows track by $index">\n' + '      <td ng-repeat="dt in row track by dt.date" class="text-center">\n' + '        <button type="button" style="width:100%;" class="btn btn-default" ng-class="{\'btn-info\': dt.selected}" ng-click="select(dt.date)" ng-disabled="dt.disabled"><span ng-class="{\'text-info\': dt.current}">{{dt.label}}</span></button>\n' + '      </td>\n' + '    </tr>\n' + '  </tbody>\n' + '</table>\n');
    $templateCache.put('ark-filter-bar/ark-filter-bar.html', '<div class="ark-filter-bar">\r' + '\n' + '  <div class="input-container">\r' + '\n' + '    <input type="text" ng-model="searchText" class="form-control filter-search-box" placeholder="Search">\r' + '\n' + '    <span class="icon-search search-box-icon"></span>\r' + '\n' + '    <span class="icon-close search-box-cancel" ng-show="hasContent" ng-click="clearInputText()"></span>\r' + '\n' + '    <div class="spinner-container input-spinner" ng-show="isSearching">\r' + '\n' + '      <div class="spin-circle"></div>\r' + '\n' + '      <div class="spin-inner-circle"></div>\r' + '\n' + '    </div>\r' + '\n' + '  </div>\r' + '\n' + '  <div ng-if="displayDropdown" class="dropdown open">\r' + '\n' + '    <ul class="dropdown-menu filter-dropdown" aria-labelledby="filterDropdown">\r' + '\n' + '      <li ng-repeat="item in items" ng-init="breakIndex = item.toLowerCase().indexOf(prevSearchText.toLowerCase())">\r' + '\n' + '        <a class="items-found" ng-click="clickItem(item)">\r' + '\n' + '          {{ item.substring(0, breakIndex) }}<b>{{ item.substring(breakIndex, (breakIndex + prevSearchText.length)) }}</b>{{ item.substring((breakIndex + prevSearchText.length)) }}\r' + '\n' + '        </a>\r' + '\n' + '      </li>\r' + '\n' + '      <li ng-if="items.length === 0">\r' + '\n' + '        <a class="not-found">\r' + '\n' + '          Search for "<b>{{ prevSearchText }}</b>" not found\r' + '\n' + '        </a>\r' + '\n' + '      </li>\r' + '\n' + '    </ul>\r' + '\n' + '  </div>\r' + '\n' + '</div>\r' + '\n');
    $templateCache.put('ark-footer/ark-footer.html', '<footer ng-class="showLargeFooter ? \'ark-footer\' : \'ark-footer-slim\'">\r' + '\n' + '  <!-- Large footer - displayed if @showLargeFooter is true -->\r' + '\n' + '  <div class="large-footer" ng-if="showLargeFooter">\r' + '\n' + '    <div class="rsection">\r' + '\n' + '      <img class="logo-img" ng-src="{{ tenantLogoLink }}" alt="">\r' + '\n' + '      <div class="powered-by">{{ i18n.POWERED_BY }}</div>\r' + '\n' + '      <div class="version" ng-if="appVersion">{{ appVersion }}</div>\r' + '\n' + '    </div>\r' + '\n' + '\r' + '\n' + '    <div class="links" ng-if="showTermsofUse || showPrivacyPolicy">\r' + '\n' + '      <span ng-if="showTermsofUse">\r' + '\n' + '        <a class="terms-of-use" target="_blank" href ng-href="{{ termsAndConditions }}">\r' + '\n' + '          {{ i18n.TERMS_OF_USE }}\r' + '\n' + '        </a>\r' + '\n' + '      </span>\r' + '\n' + '      <span ng-if="showTermsofUse && showPrivacyPolicy"> / </span>\r' + '\n' + '      <span ng-if="showPrivacyPolicy">\r' + '\n' + '        <a class="privacy-policy" target="_blank" href ng-href="{{ privacyPolicy }}">\r' + '\n' + '          {{ i18n.PRIVACY_POLICY }}\r' + '\n' + '        </a>\r' + '\n' + '      </span>\r' + '\n' + '    </div>\r' + '\n' + '    <div class="logo" ng-if="genesysLogoLink && !(showTermsofUse || showPrivacyPolicy)">\r' + '\n' + '      <img ng-src="{{ genesysLogoLink }}" alt="Genesys">\r' + '\n' + '    </div>\r' + '\n' + '    <div class="copyright">&copy; {{ currentYear }} {{ i18n.COPYRIGHT }}</div>\r' + '\n' + '  </div>\r' + '\n' + '\r' + '\n' + '  <!-- Small footer - displayed if @showLargeFooter is false -->\r' + '\n' + '  <ul class="small-footer" ng-if="!showLargeFooter">\r' + '\n' + '    <li class="left">\r' + '\n' + '      <div class="copyright">\r' + '\n' + '        <span class="fonticon icon-special-g-brandmark g-thumb"></span>\r' + '\n' + '        &copy; {{ currentYear }} {{ i18n.COPYRIGHT }}\r' + '\n' + '      </div><!-- left -->\r' + '\n' + '    </li>\r' + '\n' + '    <li class="left" ng-if="showTermsofUse">\r' + '\n' + '      <div class="terms-of-use">\r' + '\n' + '        <a target="_blank" href ng-href="{{ termsAndConditions }}">{{ i18n.TERMS_OF_USE }}</a>\r' + '\n' + '      </div>\r' + '\n' + '    </li>\r' + '\n' + '    <li class="left" ng-if="showPrivacyPolicy">\r' + '\n' + '      <div class="privacy-policy">\r' + '\n' + '        <a target="_blank" href ng-href="{{ privacyPolicy }}">{{ i18n.PRIVACY_POLICY }}</a>\r' + '\n' + '      </div>\r' + '\n' + '    </li>\r' + '\n' + '    <li class="right">\r' + '\n' + '      <div class="logo">\r' + '\n' + '        <img ng-src="{{ tenantLogoLink }}" alt="">\r' + '\n' + '      </div>\r' + '\n' + '    </li>\r' + '\n' + '    <li class="right" ng-if="appVersion">\r' + '\n' + '      <div class="version">Version {{ appVersion }}</div>\r' + '\n' + '    </li>\r' + '\n' + '  </ul>\r' + '\n' + '</footer>\r' + '\n');
    $templateCache.put('ark-login/ark-login.html', '<div class="ark-login">\r' + '\n' + '  <div class="container">\r' + '\n' + '    <div class="branding">\r' + '\n' + '      <img ng-src="{{ genesysLogoLink }}" alt="Genesys Logo" />\r' + '\n' + '    </div>\r' + '\n' + '    <div class="well">\r' + '\n' + '      <form class="form-signin" role="form" ng-show="!isLoading">\r' + '\n' + '        <div class="form-group">\r' + '\n' + '          <h2>{{ formTitle.page }}</h2>\r' + '\n' + '          <div class="ark-login-fields" ng-class="{\'has-error\': errorMessage}">\r' + '\n' + '            <input type="text" ng-model="userNameInput" class="form-control ark-login-username" placeholder="{{ formTitle.username }}"/>\r' + '\n' + '            <input type="password" ng-model="passwordInput" class="form-control ark-login-password" placeholder="{{ formTitle.password }}"/>\r' + '\n' + '          </div>\r' + '\n' + '          <div class="btn-group bootstrap-select login-select" ng-show="showLanguageBar">\r' + '\n' + '            <button ark-select type="button" class="btn btn-default dropdown-toggle selectpicker" ng-model="language" ng-options="item.title for item in languageMenu">\r' + '\n' + '            </button>\r' + '\n' + '          </div>\r' + '\n' + '          <div class="error-container" ng-show="errorMessage">\r' + '\n' + '            <span class="icon-alert-octo"> </span>\r' + '\n' + '            <div class="ark-login-error-messages">{{ errorMessage }}</div>\r' + '\n' + '          </div>\r' + '\n' + '          <div class="ark-login-button">\r' + '\n' + '            <button ng-click="login()" class="btn btn-primary btn-block">\r' + '\n' + '              {{ formTitle.button }}\r' + '\n' + '            </button>\r' + '\n' + '          </div>\r' + '\n' + '          <div class="ark-login-forgot-password" ng-if="showForgotPassword">\r' + '\n' + '            <a href ng-click="forgotPasswordFn()">\r' + '\n' + '              {{ formTitle.forgotPassword }}\r' + '\n' + '            </a>\r' + '\n' + '          </div>\r' + '\n' + '          <div class="remote-message" ng-if="remoteMessageUrl">\r' + '\n' + '            {{ remoteMessage }}\r' + '\n' + '          </div>\r' + '\n' + '        </div>\r' + '\n' + '      </form>\r' + '\n' + '      <div class="loading-container" ng-show="isLoading">\r' + '\n' + '        <h2>{{ formTitle.loading }}</h2>\r' + '\n' + '        <div class="spinner-container">\r' + '\n' + '          <div class="spin-circle"></div>\r' + '\n' + '          <div class="spin-inner-circle"></div>\r' + '\n' + '        </div>\r' + '\n' + '      </div>\r' + '\n' + '    </div><!-- well -->\r' + '\n' + '  </div><!-- container -->\r' + '\n' + '</div><!-- login -->\r' + '\n');
    $templateCache.put('ark-navbar/ark-navbar.html', '<nav class="ark-navbar navbar navbar-default" role="navigation">\n' + '  <div class="container-fluid">\n' + '    <!-- Brand and toggle get grouped for better mobile display -->\n' + '    <div ng-if="navigationJSON.header"\n' + '      ng-attr-id="{{ navigationJSON.header.id }}"\n' + '      class="navbar-header">\n' + '      <a ng-if="navigationJSON.header && navigationJSON.header.route"\n' + '        ng-href="{{ navigationJSON.header.route }}"\n' + '        class="navbar-brand">\n' + '        <span ng-if="navigationJSON.header.fonticon" class="fonticon"\n' + '          ng-class="navigationJSON.header.fonticon"></span>\n' + '        <span>{{ i18n ? i18n[navigationJSON.header.id] : \'\' }}</span>\n' + '      </a>\n' + '      <a ng-if="navigationJSON.header && !navigationJSON.header.route"\n' + '        class="navbar-brand">\n' + '        <span ng-if="navigationJSON.header.fonticon" class="fonticon"\n' + '          ng-class="navigationJSON.header.fonticon"></span>\n' + '        <span>{{ i18n ? i18n[navigationJSON.header.id] : \'\' }}</span>\n' + '      </a>\n' + '    </div>\n' + '    <!-- Collect the nav links, forms, and other content for toggling -->\n' + '    <div class="collapse navbar-collapse">\n' + '      <!-- left -->\n' + '      <ul class="nav navbar-nav">\n' + '        <li ng-repeat="item in navigationJSON.left"\n' + '          ng-attr-id="{{ item.id }}"\n' + '          ng-class="{dropdown: item.children, active: matchRoute(item.route).module}">\n' + '          <a ng-href="{{ !item.children ? item.route : \'#\' }}"\n' + '            ng-class="{\'dropdown-toggle\': item.children}"\n' + '            data-toggle="{{ item.children ? \'dropdown\' : \'\' }}">\n' + '            <span ng-if="!item.fonticon">{{ i18n ? i18n[item.id] : \'\' }} <b ng-if="item.caret == true" class="caret"></b></span>\n' + '            <span ng-if="item.fonticon" ng-attr-title="{{ i18n ? i18n[item.id] : \'\' }}">\n' + '              <span class="fonticon" ng-class="item.fonticon"></span>\n' + '              <b ng-if="item.caret == true" class="caret"></b>\n' + '            </span>\n' + '          </a>\n' + '          <ul ng-if="item.children" class="dropdown-menu">\n' + '              <li ng-repeat="subItem in item.children"\n' + '                ng-attr-id="{{ subItem.id }}"\n' + '                ng-class="{dropdown: subItem.children, divider: subItem.type == \'sub-group\', active: matchRoute(subItem.route).subModule}">\n' + '                <a ng-if="subItem.type == \'sub-item\'"\n' + '                  ng-href="{{ !subItem.children ? subItem.route : \'\' }}"\n' + '                  ng-class="{\'dropdown-toggle dropdown-nested\': subItem.children}"\n' + '                  data-toggle="{{ subItem.children ? \'dropdown\' : \'\' }}">\n' + '                  {{ i18n ? i18n[subItem.id] : \'\' }}</a>\n' + '                <span ng-if="subItem.type == \'sub-group\'">{{ i18n ? i18n[subItem.id] : \'\' }}</span>\n' + '                <ul ng-if="subItem.children" class="dropdown-menu sub-menu">\n' + '                  <li ng-repeat="subSubItem in subItem.children"\n' + '                    ng-attr-id="{{ subSubItem.id }}"\n' + '                    ng-class="{divider: subSubItem.type == \'sub-group\', active: matchRoute(subSubItem.route).subModule}">\n' + '                    <a ng-if="subSubItem.type == \'sub-item\'"\n' + '                      ng-href="{{ subSubItem.route }}">\n' + '                      {{ i18n ? i18n[subSubItem.id] : \'\' }}</a>\n' + '                    <span ng-if="subSubItem.type == \'sub-group\'">{{ i18n ? i18n[subSubItem.id]  : \'\' }}</span>\n' + '                  </li>\n' + '                </ul>\n' + '              </li>\n' + '          </ul>\n' + '        </li>\n' + '      </ul>\n' + '      <!-- right -->\n' + '      <ul class="nav navbar-nav navbar-right">\n' + '        <li ng-repeat="item in navigationJSON.right"\n' + '          ng-attr-id="{{ item.id }}"\n' + '          ng-class="{dropdown: (item.children || item.type === \'search-item\'), active: (matchRoute(item.route).module)}">\n' + '          <a ng-if="item.route && item.type !== \'search-item\'"\n' + '            ng-href="{{ !item.children ? item.route : \'#\' }}"\n' + '            ng-class="{\'dropdown-toggle\': item.children}"\n' + '            data-toggle="{{ item.children ? \'dropdown\' : \'\' }}">\n' + '            <span ng-if="!item.fonticon">{{ i18n ? i18n[item.id] : \'\' }} <b ng-if="item.caret == true" class="caret"></b></span>\n' + '            <span ng-if="item.fonticon"\n' + '              ng-attr-title="{{ i18n ? i18n[item.id] :\'\' }}">\n' + '              <span class="fonticon" ng-class="item.fonticon"></span>\n' + '              <b ng-if="item.caret == true" class="caret"></b>\n' + '            </span>\n' + '          </a>\n' + '          <a ng-if="!item.route && item.type === \'search-item\'"\n' + '            class="dropdown-toggle"\n' + '            data-toggle="dropdown">\n' + '            <span ng-if="!item.fonticon">{{ i18n ? i18n[item.id] : \'\' }} <b ng-if="item.caret == true" class="caret"></b></span>\n' + '            <span ng-if="item.fonticon" ng-attr-title="{{ i18n ? i18n[item.id] : \'\' }}">\n' + '                <span class="fonticon" ng-class="item.fonticon"></span>\n' + '                <b ng-if="item.caret == true" class="caret"></b>\n' + '            </span>\n' + '          </a>\n' + '          <ul ng-if="item.children" class="dropdown-menu">\n' + '            <li ng-repeat="subItem in item.children"\n' + '              ng-attr-id="{{ subItem.id }}"\n' + '              ng-class="{dropdown: subItem.children, divider: subItem.type == \'sub-group\', active: matchRoute(subItem.route).subModule}">\n' + '              <a ng-if="subItem.type == \'sub-item\'"\n' + '                ng-href="{{ !subItem.children ? subItem.route : \'\' }}"\n' + '                ng-class="{\'dropdown-toggle dropdown-nested\': subItem.children}"\n' + '                data-toggle="{{ subItem.children ? \'dropdown\' : \'\' }}">\n' + '                {{ i18n ? i18n[subItem.id] : \'\' }}</a>\n' + '              <span ng-if="subItem.type == \'sub-group\'">{{ i18n ? i18n[subItem.id] : \'\' }}</span>\n' + '              <ul ng-if="subItem.children" class="dropdown-menu sub-menu">\n' + '                  <li ng-repeat="subSubItem in subItem.children"\n' + '                    ng-attr-id="{{ subSubItem.id }}"\n' + '                    ng-class="{divider: subSubItem.type == \'sub-group\', active: matchRoute(subSubItem.route).subModule}">\n' + '                      <a ng-if="subSubItem.type == \'sub-item\'"\n' + '                        ng-href="{{ subSubItem.route }}">\n' + '                        {{ i18n ? i18n[subSubItem.id] : \'\' }}</a>\n' + '                      <span ng-if="subSubItem.type == \'sub-group\'">{{ i18n ? i18n[subSubItem.id] : \'\' }}</span>\n' + '                  </li>\n' + '              </ul>\n' + '            </li>\n' + '          </ul>\n' + '          <ul ng-if="item.type === \'search-item\'" class="dropdown-menu searchbar">\n' + '            <li>\n' + '              <div class="ark-filter-bar">\n' + '                <div class="input-container" stop-close>\n' + '                  <input type="text" ng-model="searchbar.searchText" class="form-control filter-search-box" placeholder="Search">\n' + '                  <span class="icon-search search-box-icon"></span>\n' + '                  <span class="icon-close search-box-cancel" ng-show="hasContent" ng-click="clearInputText()"></span>\n' + '                  <div class="spinner-container input-spinner" ng-show="isSearching">\n' + '                    <div class="spin-circle"></div>\n' + '                    <div class="spin-inner-circle"></div>\n' + '                  </div>\n' + '                </div>\n' + '                <div ng-if="displayDropdown" class="dropdown open">\n' + '                  <ul class="dropdown-menu filter-dropdown search-result" aria-labelledby="filterDropdown">\n' + '                    <li ng-repeat="item in items" ng-init="breakIndex = item.toLowerCase().indexOf(prevSearchText.toLowerCase())">\n' + '                      <a class="items-found" ng-click="clickItem(item)">\n' + '                        {{ item.substring(0, breakIndex) }}<b>{{ item.substring(breakIndex, (breakIndex + prevSearchText.length)) }}</b>{{ item.substring((breakIndex + prevSearchText.length)) }}\n' + '                      </a>\n' + '                    </li>\n' + '                    <li ng-if="items.length === 0">\n' + '                      <a class="not-found">\n' + '                        Search for "<b>{{ prevSearchText }}</b>" not found\n' + '                      </a>\n' + '                    </li>\n' + '                  </ul>\n' + '                </div>\n' + '              </div>\n' + '            </li>\n' + '          </ul>\n' + '        </li>\n' + '      </ul>\n' + '    </div><!-- /.navbar-collapse -->\n' + '  </div><!-- /.container-fluid -->\n' + '</nav>\n');
    $templateCache.put('ark-nested-search/ark-nested-search.html', '<span class="ark-nested-search">\r' + '\n' + '  <span class="searchContainer" style="width: calc(100% - 72px)">\r' + '\n' + '    <span class="fonticon icon-search"></span>\r' + '\n' + '    <input ng-keydown="searchKeyPress($event)" placeholder="Search Items" class="form-control nestedSearchInput" ng-model="search.searchValue">\r' + '\n' + '    <span ng-if="!delayPromise">\r' + '\n' + '      <span ng-if="search.searchValue && searchResults.length" class="searchcount">\r' + '\n' + '        {{ currSearchIndex + 1 }} of {{ searchResults.length }}\r' + '\n' + '      </span>\r' + '\n' + '      <span ng-if="search.searchValue && !searchResults.length" class="searchcount">\r' + '\n' + '        0 results\r' + '\n' + '      </span>\r' + '\n' + '      <span ng-show="search.searchValue && !delayPromise" class="icon-close search-box-cancel close-span ark-fonticon" ng-click="search.searchValue = \'\'">\r' + '\n' + '      </span>\r' + '\n' + '    </span>\r' + '\n' + '    <span ng-if="delayPromise && config.delay" class="searchcount wait">waiting...</span>\r' + '\n' + '  </span>\r' + '\n' + '  <span>\r' + '\n' + '    <button ng-disabled="!searchResults.length" ng-click="switchPrimaryResult(\'next\')" type="button" class="nextResult btn btn-default fonticon icon-iw-circle-no-chevron-down" style="padding: 2px 12px"></button><!--\r' + '\n' + '    --><button ng-disabled="!searchResults.length" ng-click="switchPrimaryResult(\'previous\')" type="button" class="previousResult btn btn-default fonticon icon-iw-circle-no-chevron-up" style="padding: 2px 12px; margin-left:1px;"></button>\r' + '\n' + '  </span>\r' + '\n' + '</span>\r' + '\n');
    $templateCache.put('ark-nested-tree/ark-nested-tree.html', '<div class="ark-nested-tree panel panel-default"\n' + '  ng-class="{ \'no-border\': !showBorder }"\n' + '  filter-treeview="true"\n' + '  tree-id="myTree"\n' + '  tree-model="model"\n' + '  node-id="id"\n' + '  node-label="label"\n' + '  node-children="items"\n' + '  tree-name="{{treeName}}"\n' + '  level-depth="0"\n' + '  node-unselectable="unselectable"\n' + '  node-html-content="htmlContent"\n' + '  max-child-height="maxHeight">\n' + '</div>\n');
    $templateCache.put('ark-select/ark-select.html', '<div class="ark-select-wrapper bootstrap-select dropdown-menu" ng-class="{ scrollable: $matches.length > 10 }">\n' + '  <ul tabindex="-1" class="inner select dropdown-menu selectpicker" ng-show="$isVisible()" role="select" style="display:block;">\n' + '    <li role="presentation" ng-repeat="match in $matches" ng-class="{selected: $isActive($index)}"><!-- ng-class="{active: $isActive($index)}" -->\n' + '      <a style="cursor: default;" role="menuitem" tabindex="-1" id=\'{{ $parentId + "-" + (match.value.name || match.value.id || "select-default-id-"+match.label) }}\' ng-checked="$isActive($index)" ng-click="$select($index, $event)">\n' + '        <span ng-bind="match.label"></span>\n' + '        <i class="{{$iconCheckmark}} pull-right" ng-if="$isMultiple && $isActive($index)"><!-- --></i>\n' + '      </a>\n' + '    </li>\n' + '  </ul>\n' + '</div>\n');
    $templateCache.put('ark-select/tooltip.tpl.html', '<div class="tooltip in" ng-show="title">\n' + '  <div class="tooltip-arrow"></div>\n' + '  <div class="tooltip-inner" ng-bind="title"></div>\n' + '</div>\n');
    $templateCache.put('ark-side-tabs/ark-side-tabs.html', '<div class="side-tabs-container">\r' + '\n' + '  <ul class="nav nav-side-tabs">\r' + '\n' + '    <li ng-repeat="tab in tabs" ng-class="{active: $index === selectedItemIndex}" ng-click="setActive($index)">\r' + '\n' + '      <a href><span class="fonticon {{ tab.icon }}" ng-if="tab.icon"></span>{{ tab.title }}</a>\r' + '\n' + '    </li>\r' + '\n' + '  </ul>\r' + '\n' + '  <div class="tabs-contents" style="width: calc(100% - 140px)">\r' + '\n' + '    <div ng-if="!reload">\r' + '\n' + '      <div ng-include ng-repeat="tab in tabs" src="tab.templateUrl" ng-show="$index === selectedItemIndex"></div>\r' + '\n' + '    </div>\r' + '\n' + '    <div ng-if="reload">\r' + '\n' + '      <div ng-include src="selectedTemplate"></div>\r' + '\n' + '    </div>\r' + '\n' + '  </div>\r' + '\n' + '</div>\r' + '\n');
    $templateCache.put('ark-sidebar/ark-sidebar.html', '<div class="ark-sidebar" ng-hide="!showSidebar">\r' + '\n' + '  <div class="ark-sidebar-container" ng-class="{\'ark-sidebar-shadow\': showShadow}">\r' + '\n' + '    <div ng-include="template"></div>\r' + '\n' + '  </div>\r' + '\n' + '</div>\r' + '\n');
    $templateCache.put('ark-slider/ark-slider.html', '<div class="slider-track" ng-class="{\'slider-active\': isActive}">\n' + '  <span ng-transclude ng-mousedown="setActive()" ng-mouseup="setActive()"></span>\n' + '  <div class="slider-value-container"\n' + '  ng-class="{\'slider-value-container-active\': isActive}" ng-if="!useTooltip">\n' + '    {{inputValue}}<span ng-if="showPercentage">&#37;</span>\n' + '  </div>\n' + '  <div class="slider-fill">\n' + '    <div ng-show="isActive && useTooltip" class="slider-value">\n' + '      {{inputValue}}<span ng-if="showPercentage">&#37;</span>\n' + '      <div class="arrow-bottom"></div>\n' + '    </div>\n' + '    <div class="slider-thumb"></div>\n' + '  </div>\n' + '</div>\n');
    $templateCache.put('ark-tags/ark-tags.html', '<div class="ark-tags">\r' + '\n' + '  <span>\r' + '\n' + '    <span ng-repeat="tag in tagList" ng-click="removeTag(tag)" class="tag animated pulse">\r' + '\n' + '      <span class="tag-label">{{ tag }}</span>\r' + '\n' + '      <a class="tagsinput-remove-link">\r' + '\n' + '        <span class="fonticon icon-close"></span>\r' + '\n' + '      </a>\r' + '\n' + '    </span>\r' + '\n' + '  </span>\r' + '\n' + '  <div class="tagsinput-add-container">\r' + '\n' + '    <div ng-click="addTag()" class="tagsinput-add">\r' + '\n' + '      <span class="fonticon icon-add"></span>\r' + '\n' + '    </div>\r' + '\n' + '    <input ng-model="inputTag" placeholder="Add a Tag" id="tagsinput_tag" value="" style="color: rgb(102, 102, 102);">\r' + '\n' + '  </div>\r' + '\n' + '</div>\r' + '\n');
    $templateCache.put('ark-time-picker/ark-time-picker.html', '<div class="ark-timepicker">\n' + '  <div class="timepicker-header" ng-if="widgetMode">\n' + '    <b>{{ headerLabel }}</b>\n' + '  </div>\n' + '  <div class="timepicker-content">\n' + '    <div class="col-container first">\n' + '      <div class="icon-iw-circle-no-chevron-up arrow" ng-if="widgetMode" while-pressed="addHour()"></div>\n' + '      <div class="dropdown open">\n' + '        <input type="text" maxlength="2" ng-model="hour" ng-click="showHour()" ng-blur="validateHour()">\n' + '        <ul ng-show="showHourList" class="dropdown-menu">\n' + '          <li ng-repeat="list in hourList">\n' + '            <a href ng-mousedown="selectHour(list)" ng-class="{selected: list === hour}">\n' + '              {{ list }}\n' + '            </a>\n' + '          </li>\n' + '        </ul>\n' + '      </div>\n' + '      <div class="icon-iw-circle-no-chevron-down arrow" ng-if="widgetMode" while-pressed="minusHour()"></div>\n' + '    </div>\n' + '\n' + '    <div class="col-container column"><b>:</b></div>\n' + '\n' + '    <div class="col-container">\n' + '      <div class="icon-iw-circle-no-chevron-up arrow" ng-if="widgetMode" while-pressed="addMinute()"></div>\n' + '      <div class="dropdown open">\n' + '        <input type="text" maxlength="2" ng-model="minute" ng-click="showMinute()" ng-blur="validateMinute()">\n' + '        <ul ng-show="showMinuteList" class="dropdown-menu">\n' + '          <li ng-repeat="list in minuteList">\n' + '            <a href ng-mousedown="selectMinute(list)" ng-class="{selected: list===minute}">\n' + '              {{ list }}\n' + '            </a>\n' + '          </li>\n' + '        </ul>\n' + '      </div>\n' + '      <div class="icon-iw-circle-no-chevron-down arrow" ng-if="widgetMode" while-pressed="minusMinute()"></div>\n' + '    </div>\n' + '\n' + '    <div class="col-container last">\n' + '      <div class="icon-iw-circle-no-chevron-up arrow" ng-if="widgetMode" ng-click="changeNoon()"></div>\n' + '      <input type="text" maxlength="2" ng-model="noon" ng-blur="validateNoon()">\n' + '      <div class="icon-iw-circle-no-chevron-down arrow" ng-if="widgetMode" ng-click="changeNoon()"></div>\n' + '    </div>\n' + '\n' + '    <div class="col-container last" ng-if="timezoneMode">\n' + '      <div class="icon-iw-circle-no-chevron-up arrow timezone" ng-if="widgetMode" ng-click="addTimeZone()"></div>\n' + '      <div class="dropdown open">\n' + '        <input type="text" class="timezone" maxlength="9" ng-model="timeZone" ng-click="showTimeZone()" ng-blur="validateTimeZone()" readonly>\n' + '        <ul ng-show="showTimeZoneList" class="dropdown-menu timezone">\n' + '          <li ng-repeat="list in timeZoneList">\n' + '            <a href ng-mousedown="selectTimeZone(list, $index)" class="timezone" ng-class="{selected: list === timeZone}">\n' + '              {{ list }}\n' + '            </a>\n' + '          </li>\n' + '        </ul>\n' + '      </div>\n' + '      <div class="icon-iw-circle-no-chevron-down arrow timezone" ng-if="widgetMode" ng-click="minusTimeZone()"></div>\n' + '    </div>\n' + '  </div>\n' + '</div>\n');
    $templateCache.put('ark-toolbar/ark-toolbar.html', '<div class="ark-toolbar {{options.toolbarContainer}} {{options.theme}}-theme" style="{{options.toolbarStyle}}">\n' + '  <ul class="lefttoolbar ark-toolbar-buttons {{options.leftButtonContainer}}">\n' + '    <li ng-repeat="button in options.lefttoolbar"\n' + '      ng-click="button.click($event, button)"\n' + '      ng-href="{{button.href}}"\n' + '      ng-class="{\'non-clickable\': button.nonClickable, \'spacer\' : button.spacer}"\n' + '      id="{{button.id}}"\n' + '      class="{{button.class}}">\n' + '      <span\n' + '        class="{{button.icon}} {{button.buttonStyleClass}} ark-fonticon"\n' + '        data-toggle="tooltip"\n' + '        data-placement="bottom"\n' + '        title="{{button.tooltipTitle}}"\n' + '        ng-if="button.icon"></span>\n' + '      <span\n' + '        class="icon-title"\n' + '        title="{{button.tooltipTitle}}"\n' + '        ng-if="button.title">\n' + '        {{ button.title }}\n' + '      </span>\n' + '      <div ng-if="button.select" class="btn-group bootstrap-select show-tick">\n' + '        <button ng-if="!button.select.multiple" ark-select type="button" class="btn btn-default dropdown-toggle selectpicker"\n' + '        ng-model="button.select.value"\n' + '        id="{{ button.select.id }}"\n' + '        ng-options="{{button.select.options}}"\n' + '        placeholder="{{button.select.placeholder}}"\n' + '        ></button>\n' + '        <button ng-if="button.select.multiple" ark-select type="button" class="btn btn-default dropdown-toggle selectpicker"\n' + '        ng-model="button.select.value"\n' + '        id="{{ button.select.id }}"\n' + '        ng-options="{{button.select.options}}"\n' + '        placeholder="{{button.select.placeholder}}"\n' + '        multiple\n' + '        ></button>\n' + '      </div>\n' + '      <div class="inline input-container" ng-if="button.input">\n' + '        <div class="spacer nonClickable"></div>\n' + '        <span class="{{button.input.icon}} ark-fonticon" ng-if="button.input.icon"></span>\n' + '        <input\n' + '          ng-if="!button.input.eventHandlers"\n' + '          ng-model="button.input.value"\n' + '          class="inline form-control search-input"\n' + '          ng-class="{{button.input.className}}"\n' + '          id="{{button.input.id}}"\n' + '          type="text"\n' + '          placeholder="{{button.input.placeholder}}" >\n' + '        <input\n' + '          ng-if="button.input.eventHandlers"\n' + '          ng-model="button.input.value"\n' + '          class="inline form-control search-input"\n' + '          ng-class="{{button.input.className}}"\n' + '          id="{{button.input.id}}"\n' + '          type="text"\n' + '          placeholder="{{button.input.placeholder}}"\n' + '          parse-handlers handler-array="button.input.eventHandlers">\n' + '        <span class="icon-close search-box-cancel close-span ark-fonticon" ng-show="button.input.value !== \'\'" ng-click="button.input.value = \'\'"></span>\n' + '        <div class="spacer nonClickable"></div>\n' + '      </div>\n' + '      <div ng-if="button.HTMLtemplate" ng-bind-html="button.HTMLtemplate" class="toolbar-template"></div>\n' + '    </li>\n' + '  </ul>\n' + '  <ul class="righttoolbar ark-toolbar-buttons {{options.rightButtonContainer}}">\n' + '    <li ng-repeat="button in options.righttoolbar"\n' + '      ng-click="button.click($event, button)"\n' + '      ng-href="{{button.href}}"\n' + '      ng-class="{\'non-clickable\': button.nonClickable, \'spacer\' : button.spacer}"\n' + '      id="{{button.id}}"\n' + '      class="{{button.class}}">\n' + '      <span\n' + '        class="{{button.icon}} {{button.buttonStyleClass}} ark-fonticon"\n' + '        data-toggle="tooltip"\n' + '        data-placement="bottom"\n' + '        title="{{button.tooltipTitle}}"\n' + '        ng-if="button.icon"></span>\n' + '      <span\n' + '        class="icon-title"\n' + '        title="{{button.tooltipTitle}}"\n' + '        ng-if="button.title">\n' + '        {{ button.title }}\n' + '      </span>\n' + '      <div ng-if="button.select" class="btn-group bootstrap-select show-tick">\n' + '        <button ng-if="!button.select.multiple" ark-select type="button" class="btn btn-default dropdown-toggle selectpicker"\n' + '        ng-model="button.select.value"\n' + '        id="{{ button.select.id }}"\n' + '        ng-options="{{button.select.options}}"\n' + '        placeholder="{{button.select.placeholder}}"\n' + '        ></button>\n' + '        <button ng-if="button.select.multiple" ark-select type="button" class="btn btn-default dropdown-toggle selectpicker"\n' + '        ng-model="button.select.value"\n' + '        id="{{ button.select.id }}"\n' + '        ng-options="{{button.select.options}}"\n' + '        placeholder="{{button.select.placeholder}}"\n' + '        multiple\n' + '        ></button>\n' + '      </div>\n' + '\n' + '      <div class="inline input-container" ng-if="button.input">\n' + '        <div class="spacer nonClickable"></div>\n' + '        <span class="{{button.input.icon}} ark-fonticon" ng-if="button.input.icon"></span>\n' + '        <input\n' + '          ng-if="!button.input.eventHandlers"\n' + '          ng-model="button.input.value"\n' + '          class="inline form-control search-input"\n' + '          type="text"\n' + '          placeholder="{{button.input.placeholder}}" >\n' + '        <input\n' + '          ng-if="button.input.eventHandlers"\n' + '          ng-model="button.input.value"\n' + '          class="inline form-control search-input"\n' + '          type="text"\n' + '          placeholder="{{button.input.placeholder}}"\n' + '          parse-handlers handler-array="button.input.eventHandlers" >\n' + '        <span class="icon-close search-box-cancel close-span ark-fonticon" ng-show="button.input.value !== \'\'" ng-click="button.input.value = \'\'"></span>\n' + '        <div class="spacer nonClickable"></div>\n' + '      </div>\n' + '      <div ng-if="button.HTMLtemplate" ng-bind-html="button.HTMLtemplate" class="toolbar-template"></div>\n' + '    </li>\n' + '  </ul>\n' + '</div>\n');
  }
]);
'use strict';
angular.module('ark-components').controller('arkAppLauncherCtrl', [
  '$scope',
  '$window',
  '$timeout',
  '$log',
  '_',
  'arkNavMenuModel',
  function ($scope, $window, $timeout, $log, _, arkNavMenuModel) {
    var delegate = $scope.delegate;
    $scope.customAction = function customAction(item) {
      var confirmation;
      if (item.id && item.url && delegate.customAction[item.id]) {
        if (item.requireConfirmation) {
          confirmation = $window.confirm(delegate.localization.localizedStrings.ARE_YOU_SURE);
          if (confirmation) {
            delegate.customAction[item.id](item.url);
          }
        } else {
          delegate.customAction[item.id](item.url);
        }
      }
    };
    (function init() {
      var i18n = $scope.appSettings.i18n[delegate.localization.currentLanguage], localization = delegate.localization;
      $scope.user = $scope.userData.user;
      $scope.usermenu = arkNavMenuModel($scope.appSettings.usermenu, i18n);
      $scope.currentAppName = $scope.appSettings.appDisplayName;
      $scope.aboutApplication = delegate.aboutApplication;
      $scope.baseUrlAssets = $scope.appSettings.baseUrlAssets;
      function onTranslateChangeSuccess() {
        $scope.currentLanguage = _.findWhere(localization.languages, { id: localization.currentLanguageId });
        $scope.usermenu = arkNavMenuModel($scope.appSettings.usermenu, localization.localizedStrings);
      }
      if (localization) {
        $scope.localization = localization;
        $scope.localizationIcons = {};
        _.each(localization.languages, function (item) {
          var country = /\-([^\-]*)/.exec(item.id)[1];
          $scope.localizationIcons[item.id] = 'country-' + country.toLowerCase();
        });
        // Listen when translation change
        // TODO: Refactor
        $scope.$root.$on('$translateChangeSuccess', onTranslateChangeSuccess);
        // Initial state
        onTranslateChangeSuccess();
        $scope.changeLanguage = function (langId) {
          var selectedLanguage = _.findWhere(localization.languages, { id: langId });
          if (selectedLanguage) {
            $scope.currentLanguage = selectedLanguage;
            if (localization.changeLanguage) {
              localization.changeLanguage(langId).then(function (localizedStrings) {
                localization.localizedStrings = localizedStrings;
              });
            }
          } else {
            $log.error('Could not change to language', langId, 'as it could not be found');
          }
        };
      }
      $scope.appGroups = $scope.userData.getAppGroups && $scope.userData.getAppGroups();  // TODO: get rid of previous line and replace it with following
                                                                                          // if ($scope.userData.widgets) {
                                                                                          //   $scope.appGroups = _.groupBy(_.where($scope.userData.widgets, {
                                                                                          //     'status': 'ok'
                                                                                          //   }), 'category');
                                                                                          // }
    }());
  }
]);
'use strict';
angular.module('ark-components').directive('arkAppLauncher', function () {
  return {
    templateUrl: 'ark-app-launcher/ark-app-launcher.html',
    restrict: 'E',
    transclude: false,
    replace: true,
    scope: {
      delegate: '=',
      helpmenu: '=',
      appSettings: '=',
      userData: '=',
      appLauncherEnable: '='
    },
    controller: 'arkAppLauncherCtrl'
  };
}).filter('truncate', function () {
  return function (value, wordwise, max, tail) {
    if (!value) {
      return '';
    }
    max = parseInt(max, 10);
    if (!max) {
      return value;
    }
    if (value.length <= max) {
      return value;
    }
    value = value.substr(0, max);
    if (wordwise) {
      var lastspace = value.lastIndexOf(' ');
      if (lastspace !== -1) {
        value = value.substr(0, lastspace);
      }
    }
    return value + (tail || '\u2026');
  };
});
/*jshint camelcase: false */
'use strict';
angular.module('ark-components').factory('arkNavMenuItemModel', function () {
  function arkNavMenuItemModel(item, i18n) {
    var processedItem;
    if (item) {
      processedItem = {};
      processedItem.id = item.id || '';
      processedItem.name = item.name || item.id || '';
      processedItem.fonticon = item.fonticon || '';
      processedItem.url = item.url || '';
      processedItem.target = item.target || '';
      processedItem.customAction = item.custom_action || false;
      processedItem.requireConfirmation = item.require_confirmation || false;
      processedItem.disable = item.disable || false;
      if (i18n && item.id && i18n[item.id]) {
        processedItem.name = i18n[item.id];
      }
      processedItem.isDivider = item.type && item.type === 'divider' || false;
    }
    return processedItem;
  }
  return arkNavMenuItemModel;
});
'use strict';
angular.module('ark-components').factory('arkNavMenuModel', [
  'arkNavMenuItemModel',
  '$log',
  function (arkNavMenuItemModel, $log) {
    function arkNavMenu(items, i18n) {
      var processedItems = [];
      if (items && angular.isArray(items)) {
        for (var i in items) {
          processedItems.push(arkNavMenuItemModel(items[i], i18n));
        }
      } else {
        $log.error('arkNavMenu: items not an array');
      }
      return processedItems;
    }
    return arkNavMenu;
  }
]);
'use strict';
angular.module('ark-components').directive('arkDatepickerPopupWrap', [
  '$templateCache',
  function ($templateCache) {
    return {
      restrict: 'EA',
      replace: true,
      transclude: true,
      template: $templateCache.get('ark-datepicker/ark-datepicker-popup-wrap.html'),
      link: function (scope, element) {
        element.bind('click', function (event) {
          event.preventDefault();
          event.stopPropagation();
        });
      }
    };
  }
]);
'use strict';
angular.module('ark-components').constant('arkDatepickerPopupConfig', {
  datepickerPopup: 'yyyy-MM-dd',
  currentText: 'Today',
  clearText: 'Clear',
  closeText: 'Done',
  closeOnDateSelection: true,
  appendToBody: false,
  showButtonBar: false
});
'use strict';
angular.module('ark-components').directive('arkDatepickerPopup', [
  '$compile',
  '$parse',
  '$document',
  '$position',
  'dateFilter',
  'arkDatepickerPopupConfig',
  function ($compile, $parse, $document, $position, dateFilter, arkDatepickerPopupConfig) {
    return {
      restrict: 'EA',
      require: 'ngModel',
      scope: {
        isOpen: '=?',
        currentText: '@',
        clearText: '@',
        closeText: '@',
        dateDisabled: '&'
      },
      link: function (scope, element, attrs, ngModel) {
        var dateFormat, closeOnDateSelection = angular.isDefined(attrs.closeOnDateSelection) ? scope.$parent.$eval(attrs.closeOnDateSelection) : arkDatepickerPopupConfig.closeOnDateSelection, appendToBody = angular.isDefined(attrs.datepickerAppendToBody) ? scope.$parent.$eval(attrs.datepickerAppendToBody) : arkDatepickerPopupConfig.appendToBody;
        scope.showButtonBar = angular.isDefined(attrs.showButtonBar) ? scope.$parent.$eval(attrs.showButtonBar) : arkDatepickerPopupConfig.showButtonBar;
        scope.getText = function (key) {
          return scope[key + 'Text'] || arkDatepickerPopupConfig[key + 'Text'];
        };
        attrs.$observe('arkDatepickerPopup', function (value) {
          dateFormat = value || arkDatepickerPopupConfig.datepickerPopup;
          ngModel.$render();
        });
        // popup element used to display calendar
        var popupEl = angular.element('<div ark-datepicker-popup-wrap><div ark-datepicker></div></div>');
        popupEl.attr({
          'ng-model': 'date',
          'ng-change': 'dateSelection()'
        });
        function cameltoDash(string) {
          return string.replace(/([A-Z])/g, function ($1) {
            return '-' + $1.toLowerCase();
          });
        }
        // datepicker element
        var datepickerEl = angular.element(popupEl.children()[0]);
        if (attrs.datepickerOptions) {
          angular.forEach(scope.$parent.$eval(attrs.datepickerOptions), function (value, option) {
            datepickerEl.attr(cameltoDash(option), value);
          });
        }
        angular.forEach([
          'minDate',
          'maxDate'
        ], function (key) {
          if (attrs[key]) {
            scope.$parent.$watch($parse(attrs[key]), function (value) {
              scope[key] = value;
            });
            datepickerEl.attr(cameltoDash(key), key);
          }
        });
        if (attrs.dateDisabled) {
          datepickerEl.attr('date-disabled', 'dateDisabled({ date: date, mode: mode })');
        }
        // TODO: reverse from dateFilter string to Date object
        function parseDate(viewValue) {
          if (!viewValue) {
            ngModel.$setValidity('date', true);
            return null;
          } else if (angular.isDate(viewValue) && !isNaN(viewValue)) {
            ngModel.$setValidity('date', true);
            return viewValue;
          } else if (angular.isString(viewValue)) {
            var date = new Date(viewValue);
            if (isNaN(date)) {
              ngModel.$setValidity('date', false);
              return undefined;
            } else {
              ngModel.$setValidity('date', true);
              return date;
            }
          } else {
            ngModel.$setValidity('date', false);
            return undefined;
          }
        }
        ngModel.$parsers.unshift(parseDate);
        // Inner change
        scope.dateSelection = function (dt) {
          if (angular.isDefined(dt)) {
            scope.date = dt;
          }
          ngModel.$setViewValue(scope.date);
          ngModel.$render();
          if (closeOnDateSelection) {
            scope.isOpen = false;
          }
        };
        element.bind('input change keyup', function () {
          scope.$apply(function () {
            scope.date = ngModel.$modelValue;
          });
        });
        // Outter change
        ngModel.$render = function () {
          var date = ngModel.$viewValue ? dateFilter(ngModel.$viewValue, dateFormat) : '';
          element.val(date);
          scope.date = parseDate(ngModel.$modelValue);
        };
        var documentClickBind = function (event) {
          if (scope.isOpen && event.target !== element[0]) {
            scope.$apply(function () {
              scope.isOpen = false;
            });
          }
        };
        var openCalendar = function () {
          scope.$apply(function () {
            scope.isOpen = true;
          });
        };
        scope.$watch('isOpen', function (value) {
          if (value) {
            scope.position = appendToBody ? $position.offset(element) : $position.position(element);
            scope.position.top = scope.position.top + element.prop('offsetHeight');
            $document.bind('click', documentClickBind);
            element.unbind('focus', openCalendar);
            element[0].focus();
          } else {
            $document.unbind('click', documentClickBind);
            element.bind('focus', openCalendar);
          }
        });
        scope.select = function (date) {
          if (date === 'today') {
            var today = new Date();
            if (angular.isDate(ngModel.$modelValue)) {
              date = new Date(ngModel.$modelValue);
              date.setFullYear(today.getFullYear(), today.getMonth(), today.getDate());
            } else {
              date = new Date(today.setHours(0, 0, 0, 0));
            }
          }
          scope.dateSelection(date);
        };
        var $popup = $compile(popupEl)(scope);
        if (appendToBody) {
          $document.find('body').append($popup);
        } else {
          element.after($popup);
        }
        scope.$on('$destroy', function () {
          $popup.remove();
          element.unbind('focus', openCalendar);
          $document.unbind('click', documentClickBind);
        });
      }
    };
  }
]);
'use strict';
angular.module('ark-components').constant('arkDatepickerConfig', {
  formatDay: 'd',
  formatMonth: 'MMMM',
  formatYear: 'yyyy',
  formatDayHeader: 'E',
  formatDayTitle: 'MMMM yyyy',
  formatMonthTitle: 'yyyy',
  datepickerMode: 'day',
  minMode: 'day',
  maxMode: 'year',
  showWeeks: false,
  startingDay: 0,
  yearRange: 20,
  minDate: null,
  maxDate: null
});
'use strict';
angular.module('ark-components').controller('arkDatepickerCtrl', [
  '$scope',
  '$attrs',
  '$parse',
  '$interpolate',
  '$log',
  'dateFilter',
  'arkDatepickerConfig',
  '_',
  function ($scope, $attrs, $parse, $interpolate, $log, dateFilter, arkDatepickerConfig, _) {
    var self = this, ngModelCtrl = { $setViewValue: angular.noop };
    // nullModelCtrl;
    // Configuration attributes
    angular.forEach([
      'formatDay',
      'formatMonth',
      'formatYear',
      'formatDayHeader',
      'formatDayTitle',
      'formatMonthTitle',
      'minMode',
      'maxMode',
      'showWeeks',
      'startingDay',
      'yearRange'
    ], function (key, index) {
      self[key] = angular.isDefined($attrs[key]) ? index < 8 ? $interpolate($attrs[key])($scope.$parent) : $scope.$parent.$eval($attrs[key]) : arkDatepickerConfig[key];
    });
    // Watchable attributes
    angular.forEach([
      'minDate',
      'maxDate'
    ], function (key) {
      if ($attrs[key]) {
        $scope.$parent.$watch($parse($attrs[key]), function (value) {
          self[key] = value ? new Date(value) : null;
          self.refreshView();
        });
      } else {
        self[key] = arkDatepickerConfig[key] ? new Date(arkDatepickerConfig[key]) : null;
      }
    });
    this.currentCalendarDate = angular.isDefined($attrs.initDate) ? $scope.$parent.$eval($attrs.initDate) : new Date();
    this.init = function (ngModelCtrl_) {
      ngModelCtrl = ngModelCtrl_;
      ngModelCtrl.$render = function () {
        self.render();
      };
    };
    this.render = function () {
      if (ngModelCtrl.$modelValue) {
        var date = $scope.timezoneMode ? new Date($scope.prevDate) : new Date(ngModelCtrl.$modelValue);
        var isValid = !isNaN(date);
        if (isValid) {
          this.currentCalendarDate = date;
        } else {
          $log.error('Datepicker directive: "ng-model" value must be a Date object, a number of milliseconds since 01.01.1970 or a string representing an RFC2822 or ISO 8601 date.');
        }
        ngModelCtrl.$setValidity('date', isValid);
      }
      this.refreshView();
    };
    this.refreshView = function () {
      if (this.mode) {
        this._refreshView();
        var date;
        if ($scope.timezoneMode) {
          date = new Date($scope.prevDate);
        } else {
          date = ngModelCtrl.$modelValue ? new Date(ngModelCtrl.$modelValue) : null;
        }
        ngModelCtrl.$setValidity('date-disabled', !date || this.mode && !this.isDisabled(date));
      }
    };
    this.createDateObject = function (date, format) {
      var model;
      if ($scope.timezoneMode) {
        model = new Date($scope.prevDate);
      } else {
        model = ngModelCtrl.$modelValue ? new Date(ngModelCtrl.$modelValue) : null;
      }
      return {
        date: date,
        label: dateFilter(date, format),
        selected: model && this.compare(date, model) === 0,
        disabled: this.isDisabled(date),
        current: this.compare(date, new Date()) === 0
      };
    };
    this.isDisabled = function (date) {
      return this.minDate && this.compare(date, this.minDate) < 0 || this.maxDate && this.compare(date, this.maxDate) > 0 || $scope.dateDisabled && $scope.dateDisabled({
        date: date,
        mode: $scope.datepickerMode
      });
    };
    // Split array into smaller arrays
    this.split = function (arr, size) {
      var arrays = [];
      while (arr.length > 0) {
        arrays.push(arr.splice(0, size));
      }
      return arrays;
    };
    $scope.select = function (date) {
      if ($scope.datepickerMode === self.minMode) {
        var dt = ngModelCtrl.$modelValue ? new Date(ngModelCtrl.$modelValue) : new Date(0, 0, 0, 0, 0, 0, 0);
        dt.setFullYear(date.getFullYear(), date.getMonth(), date.getDate());
        if ($scope.timepickerMode) {
          dt.setHours($scope.date.getHours());
          dt.setMinutes($scope.date.getMinutes());
        }
        $scope.date = dt;
        if ($scope.timepickerMode && $scope.timezoneMode) {
          // format date string for timezoneMode
          $scope.prevDate = dt;
          ngModelCtrl.$setViewValue(dt.toLocaleString() + ' ' + $scope.timeData.timeZone);
          ngModelCtrl.$render();
        } else if ($scope.timepickerMode) {
          // format date string for timepickerMode
          ngModelCtrl.$setViewValue(dt.toLocaleString());
          ngModelCtrl.$render();
        } else {
          // format date string for default
          ngModelCtrl.$setViewValue(dt);
          ngModelCtrl.$render();
        }
      } else {
        self.currentCalendarDate = date;
        $scope.datepickerMode = self.mode.previous;
      }
    };
    $scope.move = function (direction) {
      var year = self.currentCalendarDate.getFullYear() + direction * (self.mode.step.years || 0), month = self.currentCalendarDate.getMonth() + direction * (self.mode.step.months || 0);
      self.currentCalendarDate.setFullYear(year, month, 1);
      self.refreshView();
    };
    $scope.toggleMode = function () {
      $scope.datepickerMode = $scope.datepickerMode === self.maxMode ? self.minMode : self.mode.next;
    };
    // timepicker controller resources
    $scope.hourList = [
      '1',
      '2',
      '3',
      '4',
      '5',
      '6',
      '7',
      '8',
      '9',
      '10',
      '11',
      '12'
    ];
    $scope.minuteList = [
      '00',
      '05',
      '10',
      '15',
      '20',
      '25',
      '30',
      '35',
      '40',
      '45',
      '50',
      '55'
    ];
    $scope.timeZoneList = [
      'GMT-12:00',
      'GMT-11:00',
      'GMT-10:00',
      'GMT-09:00',
      'GMT-08:00',
      'GMT-07:00',
      'GMT-06:00',
      'GMT-05:00',
      'GMT-04:30',
      'GMT-04:00',
      'GMT-03:30',
      'GMT-03:00',
      'GMT-02:00',
      'GMT-01:00',
      'GMT+00:00',
      'GMT+01:00',
      'GMT+02:00',
      'GMT+03:00',
      'GMT+03:30',
      'GMT+04:00',
      'GMT+05:00',
      'GMT+05:30',
      'GMT+05:45',
      'GMT+06:00',
      'GMT+06:30',
      'GMT+07:00',
      'GMT+08:00',
      'GMT+09:00',
      'GMT+09:30',
      'GMT+10:00',
      'GMT+11:00',
      'GMT+12:00',
      'GMT+13:00'
    ];
    $scope.showHourList = false;
    $scope.showMinuteList = false;
    $scope.showTimeZoneList = false;
    $scope.timeZoneShow = false;
    // initialize timeData object for two-way data binding within child scopes (i.e. within ng-if)
    $scope.timeData = {
      hour: 0,
      minute: 0,
      noon: 'AM',
      timeZone: 'GMT-05:00'
    };
    var controller = this;
    // watches for changes to timeData variables
    $scope.$watchCollection('[timeData.hour, timeData.minute, timeData.noon, timeData.timeZone]', function () {
      if (!$scope.isInvalidHour() && !$scope.isInvalidMinute() && !$scope.isInvalidNoon()) {
        var newDate = angular.copy($scope.date);
        var hours = parseInt($scope.timeData.hour);
        var minutes = parseInt($scope.timeData.minute);
        if ($scope.timeData.noon === 'PM') {
          if (hours < 12) {
            hours = hours + 12;
          }
        } else {
          if (hours === 12) {
            hours = 0;
          }
        }
        newDate.setHours(hours);
        newDate.setMinutes(minutes);
        $scope.date = newDate;
        $scope.select(newDate);
      }
    });
    //Hour Section
    $scope.isInvalidHour = function () {
      return controller.isInvalidHour($scope.timeData.hour, $scope.timeData.noon);
    };
    controller.isInvalidHour = function (hour, noon) {
      return !hour || isNaN(hour) || hour.indexOf('.') !== -1 || hour.length > 2 || noon === 'AM' && (parseInt(hour) > 12 || parseInt(hour) < 0) || noon === 'PM' && (parseInt(hour) > 12 || parseInt(hour) < 1);
    };
    $scope.validateHour = function () {
      if ($scope.isInvalidHour()) {
        $scope.timeData.hour = $scope.prevHour;
      } else {
        $scope.prevHour = $scope.timeData.hour;
      }
      $scope.showHourList = false;
    };
    $scope.addHour = function () {
      if ($scope.timeData.noon === 'AM') {
        if ($scope.timeData.hour === '11') {
          $scope.timeData.noon = 'PM';
          $scope.timeData.hour = '12';
        } else {
          $scope.timeData.hour = parseInt($scope.timeData.hour) % 12 + 1 + '';
        }
      } else {
        if ($scope.timeData.hour === '11') {
          $scope.timeData.noon = 'AM';
        }
        $scope.timeData.hour = parseInt($scope.timeData.hour) % 12 + 1 + '';
      }
      $scope.prevHour = $scope.timeData.hour;
      $scope.prevNoon = $scope.timeData.noon;
    };
    $scope.minusHour = function () {
      if ($scope.timeData.noon === 'AM') {
        if ($scope.timeData.hour === '00' || $scope.timeData.hour === '0' || $scope.timeData.hour === '12') {
          $scope.timeData.noon = 'PM';
          $scope.timeData.hour = '11';
        } else {
          $scope.timeData.hour = parseInt($scope.timeData.hour) - 1 + '';
        }
      } else {
        if ($scope.timeData.hour === '12') {
          $scope.timeData.noon = 'AM';
        }
        $scope.timeData.hour = $scope.timeData.hour === '01' || $scope.timeData.hour === '1' ? $scope.timeData.hour = '12' : parseInt($scope.timeData.hour) - 1 + '';
      }
      $scope.prevHour = $scope.timeData.hour;
      $scope.prevNoon = $scope.timeData.noon;
    };
    // Minute section
    $scope.isInvalidMinute = function () {
      return controller.isInvalidMinute($scope.timeData.minute);
    };
    controller.isInvalidMinute = function (minute) {
      return !minute || isNaN(minute) || minute.indexOf('.') !== -1 || minute.length > 2 || parseInt(minute) > 59 || parseInt(minute) < 0;
    };
    $scope.formatNumber = function (input) {
      if (input.length === 1) {
        input = '0' + input;
      }
      return input;
    };
    $scope.addMinute = function () {
      if ($scope.timeData.minute === '59') {
        $scope.addHour();
      }
      $scope.timeData.minute = $scope.formatNumber((parseInt($scope.timeData.minute) + 1) % 60 + '');
      $scope.prevMinute = $scope.timeData.minute;
    };
    $scope.minusMinute = function () {
      if ($scope.timeData.minute === '0' || $scope.timeData.minute === '00') {
        $scope.minusHour();
      }
      $scope.timeData.minute = $scope.formatNumber((parseInt($scope.timeData.minute) + 59) % 60 + '');
      $scope.prevMinute = $scope.timeData.minute;
    };
    $scope.validateMinute = function () {
      if ($scope.isInvalidMinute()) {
        $scope.timeData.minute = $scope.prevMinute;
      } else {
        $scope.timeData.minute = $scope.formatNumber($scope.timeData.minute);
        $scope.prevMinute = $scope.timeData.minute;
      }
      $scope.showMinuteList = false;
    };
    // AM/PM section
    $scope.changeNoon = function () {
      if ($scope.timeData.noon === 'AM') {
        if ($scope.timeData.hour === '0' || $scope.timeData.hour === '00') {
          $scope.timeData.hour = '12';
          $scope.prevHour = $scope.timeData.hour;
        }
        $scope.timeData.noon = 'PM';
      } else {
        $scope.timeData.noon = 'AM';
      }
      $scope.prevNoon = $scope.timeData.noon;
    };
    $scope.validateNoon = function () {
      if (!$scope.isInvalidNoon()) {
        if ($scope.timeData.noon.toLowerCase() === 'pm' && $scope.timeData.hour === '0') {
          $scope.timeData.hour = '12';
          $scope.prevHour = $scope.timeData.hour;
        }
        $scope.timeData.noon = $scope.timeData.noon.toUpperCase();
        $scope.prevNoon = $scope.timeData.noon;
      } else {
        $scope.timeData.noon = $scope.prevNoon;
      }
    };
    $scope.isInvalidNoon = function () {
      return controller.isInvalidNoon($scope.timeData.noon);
    };
    // returns bool
    controller.isInvalidNoon = function (noon) {
      return noon.toUpperCase() !== 'AM' && noon.toUpperCase() !== 'PM';
    };
    // Timezone Section
    $scope.isInvalidTimeZone = function () {
      return !_.contains($scope.timeZoneList, $scope.timeData.timeZone);
    };
    $scope.validateTimeZone = function () {
      if ($scope.isInvalidTimeZone()) {
        $scope.timeData.timeZone = $scope.prevTimeZone;
      } else {
        $scope.prevTimeZone = $scope.timeData.timeZone;
      }
      $scope.showTimeZoneList = false;
    };
    $scope.addTimeZone = function () {
      if ($scope.timeZoneIndex > 0) {
        $scope.timeZoneIndex--;
      }
      $scope.timeData.timeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      $scope.prevTimeZone = $scope.timeData.timeZone;
    };
    $scope.minusTimeZone = function () {
      if ($scope.timeZoneIndex < $scope.timeZoneList.length - 1) {
        $scope.timeZoneIndex++;
      }
      $scope.timeData.timeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      $scope.prevTimeZone = $scope.timeData.timeZone;
    };
    // UI section
    $scope.showHour = function () {
      $scope.showHourList = true;
    };
    $scope.showMinute = function () {
      $scope.showMinuteList = true;
    };
    $scope.showTimeZone = function () {
      $scope.showTimeZoneList = true;
    };
    $scope.toggleTimeZone = function () {
      $scope.timeZoneShow = !$scope.timeZoneShow;
    };
    $scope.selectHour = function (item) {
      $scope.timeData.hour = item;
      $scope.prevHour = item;
    };
    $scope.selectMinute = function (item) {
      $scope.timeData.minute = item;
      $scope.prevMinute = item;
    };
    $scope.selectTimeZone = function (item, index) {
      $scope.timeData.timeZone = item;
      $scope.prevTimeZone = item;
      $scope.timeZoneIndex = index;
    };
    $scope.initializeTimeVars = function () {
      if ($scope.dateTimeDefault) {
        var dateTimeDefault = new Date($scope.dateTimeDefault);
        if (!isNaN(dateTimeDefault)) {
          $scope.date = angular.copy(dateTimeDefault);
        } else {
          $scope.date = new Date();
        }
      } else {
        $scope.date = new Date();
      }
      $scope.timeZoneIndex = 7;
      $scope.prevTimeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      $scope.timeData.timeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      var hours = $scope.date.getHours();
      var minutes = $scope.date.getMinutes();
      var noon;
      if (hours >= 12) {
        noon = 'PM';
        if (hours > 12) {
          hours = hours - 12;
        }
      } else {
        noon = 'AM';
      }
      if (minutes < 10) {
        minutes = '0' + minutes;
      }
      $scope.prevHour = hours.toString();
      $scope.timeData.hour = hours.toString();
      $scope.prevMinute = minutes.toString();
      $scope.timeData.minute = minutes.toString();
      $scope.prevNoon = noon;
      $scope.timeData.noon = noon;
    };
    (function init() {
      if ($scope.timepickerMode) {
        $scope.initializeTimeVars();
      }
      $scope.datepickerMode = $scope.datepickerMode || arkDatepickerConfig.datepickerMode;
    }());
  }
]);
'use strict';
angular.module('ark-components').directive('arkDatepicker', [
  '$templateCache',
  function ($templateCache) {
    return {
      restrict: 'EA',
      replace: true,
      template: $templateCache.get('ark-datepicker/ark-datepicker.html'),
      scope: {
        datepickerMode: '=?',
        dateDisabled: '&',
        timepickerMode: '@',
        timezoneMode: '@',
        dateTimeDefault: '@'
      },
      require: [
        'arkDatepicker',
        '?^ngModel'
      ],
      controller: 'arkDatepickerCtrl',
      link: function (scope, element, attrs, ctrls) {
        var datepickerCtrl = ctrls[0], ngModelCtrl = ctrls[1];
        if (ngModelCtrl) {
          datepickerCtrl.init(ngModelCtrl);
        }
        scope.timepickerMode = scope.$eval(scope.timepickerMode) || false;
        scope.timezoneMode = scope.$eval(scope.timezoneMode) || false;
      }
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkDaypicker', [
  'dateFilter',
  '$templateCache',
  function (dateFilter, $templateCache) {
    return {
      restrict: 'EA',
      replace: true,
      template: $templateCache.get('ark-datepicker/ark-daypicker.html'),
      require: '^arkDatepicker',
      link: function (scope, element, attrs, ctrl) {
        scope.showWeeks = ctrl.showWeeks;
        ctrl.mode = {
          step: { months: 1 },
          next: 'month'
        };
        function getDaysInMonth(year, month) {
          return new Date(year, month, 0).getDate();
        }
        function getDates(startDate, n) {
          var dates = new Array(n), current = new Date(startDate), i = 0;
          current.setHours(12);
          // Prevent repeated dates because of timezone bug
          while (i < n) {
            dates[i++] = new Date(current);
            current.setDate(current.getDate() + 1);
          }
          return dates;
        }
        ctrl._refreshView = function () {
          var year = ctrl.currentCalendarDate.getFullYear(), month = ctrl.currentCalendarDate.getMonth(), firstDayOfMonth = new Date(year, month, 1), difference = ctrl.startingDay - firstDayOfMonth.getDay(), numDisplayedFromPreviousMonth = difference > 0 ? 7 - difference : -difference, firstDate = new Date(firstDayOfMonth), numDates = 0;
          if (numDisplayedFromPreviousMonth > 0) {
            firstDate.setDate(-numDisplayedFromPreviousMonth + 1);
            numDates += numDisplayedFromPreviousMonth;  // Previous
          }
          numDates += getDaysInMonth(year, month + 1);
          // Current
          numDates += (7 - numDates % 7) % 7;
          // Next
          var days = getDates(firstDate, numDates);
          for (var i = 0; i < numDates; i++) {
            days[i] = angular.extend(ctrl.createDateObject(days[i], ctrl.formatDay), { secondary: days[i].getMonth() !== month });
          }
          scope.labels = new Array(7);
          for (var j = 0; j < 7; j++) {
            if (ctrl.formatDayHeader === 'E') {
              //Substring grabs just the first character. This is to match AW design mockups
              scope.labels[j] = dateFilter(days[j].date, 'EEE').substr(0, 1);
            } else {
              scope.labels[j] = dateFilter(days[j].date, ctrl.formatDayHeader);
            }
          }
          scope.title = dateFilter(ctrl.currentCalendarDate, ctrl.formatDayTitle);
          scope.rows = ctrl.split(days, 7);
          if (scope.showWeeks) {
            scope.weekNumbers = [];
            var weekNumber = getISO8601WeekNumber(scope.rows[0][0].date), numWeeks = scope.rows.length;
            while (scope.weekNumbers.push(weekNumber++) < numWeeks) {
            }
          }
        };
        ctrl.compare = function (date1, date2) {
          return new Date(date1.getFullYear(), date1.getMonth(), date1.getDate()) - new Date(date2.getFullYear(), date2.getMonth(), date2.getDate());
        };
        function getISO8601WeekNumber(date) {
          var checkDate = new Date(date);
          checkDate.setDate(checkDate.getDate() + 4 - (checkDate.getDay() || 7));
          // Thursday
          var time = checkDate.getTime();
          checkDate.setMonth(0);
          // Compare with Jan 1
          checkDate.setDate(1);
          return Math.floor(Math.round((time - checkDate) / 86400000) / 7) + 1;
        }
        ctrl.refreshView();
      }
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkMonthpicker', [
  'dateFilter',
  '$templateCache',
  function (dateFilter, $templateCache) {
    return {
      restrict: 'EA',
      replace: true,
      template: $templateCache.get('ark-datepicker/ark-monthpicker.html'),
      require: '^arkDatepicker',
      link: function (scope, element, attrs, ctrl) {
        ctrl.mode = {
          step: { years: 1 },
          previous: 'day',
          next: 'year'
        };
        ctrl._refreshView = function () {
          var months = new Array(12), year = ctrl.currentCalendarDate.getFullYear();
          for (var i = 0; i < 12; i++) {
            months[i] = ctrl.createDateObject(new Date(year, i, 1), ctrl.formatMonth);
          }
          scope.title = dateFilter(ctrl.currentCalendarDate, ctrl.formatMonthTitle);
          scope.rows = ctrl.split(months, 3);
        };
        ctrl.compare = function (date1, date2) {
          return new Date(date1.getFullYear(), date1.getMonth()) - new Date(date2.getFullYear(), date2.getMonth());
        };
        ctrl.refreshView();
      }
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkYearpicker', [
  'dateFilter',
  '$templateCache',
  function (dateFilter, $templateCache) {
    return {
      restrict: 'EA',
      replace: true,
      template: $templateCache.get('ark-datepicker/ark-yearpicker.html'),
      require: '^arkDatepicker',
      link: function (scope, element, attrs, ctrl) {
        ctrl.mode = {
          step: { years: ctrl.yearRange },
          previous: 'month'
        };
        ctrl._refreshView = function () {
          var range = this.mode.step.years, years = new Array(range), start = parseInt((ctrl.currentCalendarDate.getFullYear() - 1) / range, 10) * range + 1;
          for (var i = 0; i < range; i++) {
            years[i] = ctrl.createDateObject(new Date(start + i, 0, 1), ctrl.formatYear);
          }
          scope.title = [
            years[0].label,
            years[range - 1].label
          ].join(' - ');
          scope.rows = ctrl.split(years, 5);
        };
        ctrl.compare = function (date1, date2) {
          return date1.getFullYear() - date2.getFullYear();
        };
        ctrl.refreshView();
      }
    };
  }
]);
'use strict';
angular.module('ark-components').factory('$position', [
  '$document',
  '$window',
  function ($document, $window) {
    function getStyle(el, cssprop) {
      if (el.currentStyle) {
        //IE
        return el.currentStyle[cssprop];
      } else if ($window.getComputedStyle) {
        return $window.getComputedStyle(el)[cssprop];
      }
      // finally try and get inline style
      return el.style[cssprop];
    }
    /**
     * Checks if a given element is statically positioned
     * @param element - raw DOM element
     */
    function isStaticPositioned(element) {
      return (getStyle(element, 'position') || 'static') === 'static';
    }
    /**
     * returns the closest, non-statically positioned parentOffset of a given element
     * @param element
     */
    var parentOffsetEl = function (element) {
      var docDomEl = $document[0];
      var offsetParent = element.offsetParent || docDomEl;
      while (offsetParent && offsetParent !== docDomEl && isStaticPositioned(offsetParent)) {
        offsetParent = offsetParent.offsetParent;
      }
      return offsetParent || docDomEl;
    };
    return {
      position: function (element) {
        var elBCR = this.offset(element);
        var offsetParentBCR = {
            top: 0,
            left: 0
          };
        var offsetParentEl = parentOffsetEl(element[0]);
        if (offsetParentEl !== $document[0]) {
          offsetParentBCR = this.offset(angular.element(offsetParentEl));
          offsetParentBCR.top += offsetParentEl.clientTop - offsetParentEl.scrollTop;
          offsetParentBCR.left += offsetParentEl.clientLeft - offsetParentEl.scrollLeft;
        }
        var boundingClientRect = element[0].getBoundingClientRect();
        return {
          width: boundingClientRect.width || element.prop('offsetWidth'),
          height: boundingClientRect.height || element.prop('offsetHeight'),
          top: elBCR.top - offsetParentBCR.top,
          left: elBCR.left - offsetParentBCR.left
        };
      },
      offset: function (element) {
        var boundingClientRect = element[0].getBoundingClientRect();
        return {
          width: boundingClientRect.width || element.prop('offsetWidth'),
          height: boundingClientRect.height || element.prop('offsetHeight'),
          top: boundingClientRect.top + ($window.pageYOffset || $document[0].documentElement.scrollTop),
          left: boundingClientRect.left + ($window.pageXOffset || $document[0].documentElement.scrollLeft)
        };
      },
      positionElements: function (hostEl, targetEl, positionStr, appendToBody) {
        var positionStrParts = positionStr.split('-');
        var pos0 = positionStrParts[0], pos1 = positionStrParts[1] || 'center';
        var hostElPos, targetElWidth, targetElHeight, targetElPos;
        hostElPos = appendToBody ? this.offset(hostEl) : this.position(hostEl);
        targetElWidth = targetEl.prop('offsetWidth');
        targetElHeight = targetEl.prop('offsetHeight');
        var shiftWidth = {
            center: function () {
              return hostElPos.left + hostElPos.width / 2 - targetElWidth / 2;
            },
            left: function () {
              return hostElPos.left;
            },
            right: function () {
              return hostElPos.left + hostElPos.width;
            }
          };
        var shiftHeight = {
            center: function () {
              return hostElPos.top + hostElPos.height / 2 - targetElHeight / 2;
            },
            top: function () {
              return hostElPos.top;
            },
            bottom: function () {
              return hostElPos.top + hostElPos.height;
            }
          };
        switch (pos0) {
        case 'right':
          targetElPos = {
            top: shiftHeight[pos1](),
            left: shiftWidth[pos0]()
          };
          break;
        case 'left':
          targetElPos = {
            top: shiftHeight[pos1](),
            left: hostElPos.left - targetElWidth
          };
          break;
        case 'bottom':
          targetElPos = {
            top: shiftHeight[pos0](),
            left: shiftWidth[pos1]()
          };
          break;
        default:
          targetElPos = {
            top: hostElPos.top - targetElHeight,
            left: shiftWidth[pos1]()
          };
          break;
        }
        return targetElPos;
      }
    };
  }
]);
'use strict';
angular.module('ark-components').controller('arkFilterBarCtrl', [
  '$scope',
  function ($scope) {
    $scope.hasContent = false;
    $scope.isSearching = false;
    $scope.displayDropdown = false;
    $scope.items = [];
    $scope.clearInputText = function () {
      $scope.searchText = '';
    };
    $scope.clickItem = function (selectedItem) {
      $scope.selectFunction({ item: selectedItem });
      $scope.clickedItem = true;
      $scope.prevSearchText = selectedItem;
      $scope.searchText = selectedItem;
      $scope.isSearching = false;
      $scope.displayDropdown = false;
    };
    $scope.searchForContent = function (searchText) {
      $scope.isSearching = true;
      $scope.prevSearchText = searchText;
      $scope.filterFunction({
        searchText: $scope.searchText,
        callback: function (data) {
          $scope.items = $scope.itemsLength ? data.slice(0, parseInt($scope.itemsLength)) : data.slice(0, 3);
          $scope.isSearching = false;
          $scope.displayDropdown = true;
        }
      });
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkFilterBar', [
  '$timeout',
  function ($timeout) {
    return {
      restrict: 'E',
      scope: {
        itemsLength: '@listLength',
        filterFunction: '&',
        selectFunction: '&',
        delay: '@searchDelay'
      },
      controller: 'arkFilterBarCtrl',
      templateUrl: 'ark-filter-bar/ark-filter-bar.html',
      link: function ($scope) {
        $scope.newSearchText = '';
        $scope.$watch('searchText', function (newVal) {
          if (!$scope.clickedItem) {
            if (!newVal) {
              $scope.hasContent = false;
              $scope.displayDropdown = false;
            } else {
              $scope.hasContent = true;
              $scope.newSearchText = newVal;
              var delay = $scope.delay ? parseInt($scope.delay) : 500;
              $timeout(function () {
                if ($scope.newSearchText === newVal && $scope.searchText) {
                  $scope.searchForContent(newVal);
                }
              }, delay);
            }
          } else {
            $scope.clickedItem = false;
          }
        });
      }
    };
  }
]);
'use strict';
angular.module('ark-components').controller('arkFooterCtrl', [
  '$scope',
  function ($scope) {
    var self = this;
    $scope.i18n = {};
    self.defaultTexts = {
      'COPYRIGHT': 'Genesys',
      'PRIVACY_POLICY': 'Privacy Policy',
      'TERMS_OF_USE': 'Terms of Use',
      'POWERED_BY': 'Powered by Genesys'
    };
    function updateLocale() {
      if ($scope.locale) {
        for (var name in self.defaultTexts) {
          if (self.defaultTexts.hasOwnProperty(name)) {
            $scope.i18n[name] = $scope.locale[name] || self.defaultTexts[name];
          }
        }
      }
    }
    $scope.$watch('locale', updateLocale, true);
    if (!$scope.locale) {
      $scope.i18n = this.defaultTexts;
    }
    $scope.currentYear = new Date().getFullYear();
  }
]);
'use strict';
angular.module('ark-components').directive('arkFooter', function () {
  return {
    restrict: 'E',
    replace: true,
    scope: {
      tenantLogoLink: '@',
      genesysLogoLink: '@',
      termsAndConditions: '@',
      privacyPolicy: '@',
      appVersion: '=',
      footerSize: '@',
      locale: '='
    },
    templateUrl: 'ark-footer/ark-footer.html',
    controller: 'arkFooterCtrl',
    link: function ($scope, element, attrs) {
      $scope.showLargeFooter = !(angular.isDefined(attrs.footerSize) && attrs.footerSize === 'small');
      $scope.showTermsofUse = angular.isDefined(attrs.termsAndConditions) && attrs.termsAndConditions !== '';
      $scope.showPrivacyPolicy = angular.isDefined(attrs.privacyPolicy) && attrs.privacyPolicy !== '';
    }
  };
});
/*
 * angular-loading-bar
 *
 * intercepts XHR requests and creates a loading bar.
 * Based on the excellent nprogress work by rstacruz (more info in readme)
 *
 * (c) 2013 Wes Cruver
 * License: MIT
 */
(function () {
  'use strict';
  angular.module('ark-loading-bar', ['cfp.loadingBarInterceptor']);
  /**
   * loadingBarInterceptor service
   *
   * Registers itself as an Angular interceptor and listens for XHR requests.
   */
  angular.module('cfp.loadingBarInterceptor', ['ark-loading-bar-manual']).config([
    '$httpProvider',
    function ($httpProvider) {
      var interceptor = [
          '$q',
          '$cacheFactory',
          '$timeout',
          '$rootScope',
          'arkLoadingBar',
          function ($q, $cacheFactory, $timeout, $rootScope, arkLoadingBar) {
            /**
             * The total number of requests made
             */
            var reqsTotal = 0;
            /**
             * The number of requests completed (either successfully or not)
             */
            var reqsCompleted = 0;
            /**
             * The amount of time spent fetching before showing the loading bar
             */
            var latencyThreshold = arkLoadingBar.latencyThreshold;
            /**
             * $timeout handle for latencyThreshold
             */
            var startTimeout;
            /**
             * calls arkLoadingBar.complete() which removes the
             * loading bar from the DOM.
             */
            function setComplete() {
              $timeout.cancel(startTimeout);
              arkLoadingBar.complete();
              reqsCompleted = 0;
              reqsTotal = 0;
            }
            /**
             * Determine if the response has already been cached
             * @param  {Object}  config the config option from the request
             * @return {Boolean} retrns true if cached, otherwise false
             */
            function isCached(config) {
              var cache;
              var defaults = $httpProvider.defaults;
              if (config.method !== 'GET' || config.cache === false) {
                config.cached = false;
                return false;
              }
              if (config.cache === true && defaults.cache === undefined) {
                cache = $cacheFactory.get('$http');
              } else if (defaults.cache !== undefined) {
                cache = defaults.cache;
              } else {
                cache = config.cache;
              }
              var cached = cache !== undefined ? cache.get(config.url) !== undefined : false;
              if (config.cached !== undefined && cached !== config.cached) {
                return config.cached;
              }
              config.cached = cached;
              return cached;
            }
            return {
              'request': function (config) {
                // Check to make sure this request hasn't already been cached and that
                // the requester didn't explicitly ask us to ignore this request:
                if (!config.ignoreLoadingBar && !isCached(config)) {
                  $rootScope.$broadcast('arkLoadingBar:loading', { url: config.url });
                  if (reqsTotal === 0) {
                    startTimeout = $timeout(function () {
                      arkLoadingBar.start();
                    }, latencyThreshold);
                  }
                  reqsTotal++;
                  arkLoadingBar.set(reqsCompleted / reqsTotal);
                }
                return config;
              },
              'response': function (response) {
                if (!response.config.ignoreLoadingBar && !isCached(response.config)) {
                  reqsCompleted++;
                  $rootScope.$broadcast('arkLoadingBar:loaded', { url: response.config.url });
                  if (reqsCompleted >= reqsTotal) {
                    setComplete();
                  } else {
                    arkLoadingBar.set(reqsCompleted / reqsTotal);
                  }
                }
                return response;
              },
              'responseError': function (rejection) {
                if (!rejection.config.ignoreLoadingBar && !isCached(rejection.config)) {
                  reqsCompleted++;
                  $rootScope.$broadcast('arkLoadingBar:loaded', { url: rejection.config.url });
                  if (reqsCompleted >= reqsTotal) {
                    setComplete();
                  } else {
                    arkLoadingBar.set(reqsCompleted / reqsTotal);
                  }
                }
                return $q.reject(rejection);
              }
            };
          }
        ];
      $httpProvider.interceptors.push(interceptor);
    }
  ]);
  /**
   * Loading Bar
   *
   * This service handles adding and removing the actual element in the DOM.
   * Generally, best practices for DOM manipulation is to take place in a
   * directive, but because the element itself is injected in the DOM only upon
   * XHR requests, and it's likely needed on every view, the best option is to
   * use a service.
   */
  angular.module('ark-loading-bar-manual', []).provider('arkLoadingBar', function () {
    this.includeSpinner = false;
    this.includeBar = true;
    this.latencyThreshold = 100;
    this.startSize = 0.02;
    this.parentSelector = 'body';
    this.spinnerTemplate = '<div id="loading-bar-spinner"><div class="spinner-icon"></div></div>';
    this.$get = [
      '$document',
      '$timeout',
      '$animate',
      '$rootScope',
      function ($document, $timeout, $animate, $rootScope) {
        var $parentSelector = this.parentSelector, loadingBarContainer = angular.element('<div id="loading-bar"><div class="bar"><div class="peg"></div></div></div>'), loadingBar = loadingBarContainer.find('div').eq(0), spinner = angular.element(this.spinnerTemplate);
        var incTimeout, completeTimeout, started = false, status = 0;
        var includeSpinner = this.includeSpinner;
        var includeBar = this.includeBar;
        var startSize = this.startSize;
        /**
           * Inserts the loading bar element into the dom, and sets it to 2%
           */
        function _start() {
          var $parent = $document.find($parentSelector);
          $timeout.cancel(completeTimeout);
          // do not continually broadcast the started event:
          if (started) {
            return;
          }
          $rootScope.$broadcast('arkLoadingBar:started');
          started = true;
          if (includeBar) {
            $animate.enter(loadingBarContainer, $parent);
          }
          if (includeSpinner) {
            $animate.enter(spinner, $parent);
          }
          _set(startSize);
        }
        /**
           * Set the loading bar's width to a certain percent.
           *
           * @param n any value between 0 and 1
           */
        function _set(n) {
          if (!started) {
            return;
          }
          var pct = n * 100 + '%';
          loadingBar.css('width', pct);
          status = n;
          // increment loadingbar to give the illusion that there is always
          // progress but make sure to cancel the previous timeouts so we don't
          // have multiple incs running at the same time.
          $timeout.cancel(incTimeout);
          incTimeout = $timeout(function () {
            _inc();
          }, 250);
        }
        /**
           * Increments the loading bar by a random amount
           * but slows down as it progresses
           */
        function _inc() {
          if (_status() >= 1) {
            return;
          }
          var rnd = 0;
          // TODO: do this mathmatically instead of through conditions
          var stat = _status();
          if (stat >= 0 && stat < 0.25) {
            // Start out between 3 - 6% increments
            rnd = (Math.random() * (5 - 3 + 1) + 3) / 100;
          } else if (stat >= 0.25 && stat < 0.65) {
            // increment between 0 - 3%
            rnd = Math.random() * 3 / 100;
          } else if (stat >= 0.65 && stat < 0.9) {
            // increment between 0 - 2%
            rnd = Math.random() * 2 / 100;
          } else if (stat >= 0.9 && stat < 0.99) {
            // finally, increment it .5 %
            rnd = 0.005;
          } else {
            // after 99%, don't increment:
            rnd = 0;
          }
          var pct = _status() + rnd;
          _set(pct);
        }
        function _status() {
          return status;
        }
        function _complete() {
          $rootScope.$broadcast('arkLoadingBar:completed');
          _set(1);
          $timeout.cancel(completeTimeout);
          // Attempt to aggregate any start/complete calls within 500ms:
          completeTimeout = $timeout(function () {
            $animate.leave(loadingBarContainer, function () {
              status = 0;
              started = false;
            });
            $animate.leave(spinner);
          }, 500);
        }
        return {
          start: _start,
          set: _set,
          status: _status,
          inc: _inc,
          complete: _complete,
          includeSpinner: this.includeSpinner,
          latencyThreshold: this.latencyThreshold,
          parentSelector: this.parentSelector,
          startSize: this.startSize
        };
      }
    ];  //
  });  // wtf javascript. srsly
}());
//
/**
 * @name login controller
 * @description
 *     Provides implementation for the login Controller
 */
'use strict';
angular.module('ark-components').controller('arkLoginCtrl', [
  '$scope',
  '$http',
  function ($scope, $http) {
    var controller = this;
    $scope.languageMenu = [];
    $scope.isLoading = false;
    this.loadDisplayPage = function () {
      var loginJSON = $scope.loginService.getLoginJSON();
      var keys = Object.keys(loginJSON);
      for (var i = 0; i < keys.length; i++) {
        $scope.languageMenu.push({
          value: keys[i],
          title: loginJSON[keys[i]].title,
          errorMsg: loginJSON[keys[i]].errorMessages
        });
      }
    };
    $scope.login = function () {
      $scope.isLoading = true;
      $scope.errorMessage = '';
      $scope.errorMsgType = '';
      var usernameInput = $scope.userNameInput;
      var passwordInput = $scope.passwordInput;
      var languageInput = $scope.language.value;
      var loginJSON = $scope.loginService.getLoginJSON();
      if (!usernameInput || !passwordInput && $scope.isPasswordMandatory) {
        $scope.errorMessage = loginJSON[$scope.language.value].errorMessages.emptyField;
        $scope.errorMsgType = 'emptyField';
        $scope.isLoading = false;
        return;
      }
      $scope.loginService.login(usernameInput, passwordInput, languageInput, function (error) {
        var foundError = $scope.errorField !== undefined && error && error[$scope.errorField] ? error[$scope.errorField] : 'incorrectLogin';
        $scope.errorMessage = loginJSON[$scope.language.value].errorMessages[foundError] || loginJSON[$scope.language.value].errorMessages.incorrectLogin;
        $scope.errorMsgType = 'incorrectLogin';
        $scope.isLoading = false;
      });
    };
    if (angular.isDefined($scope.remoteMessageUrl)) {
      $http.get($scope.remoteMessageUrl).success(function (data) {
        $scope.remoteMessage = data;
      });
    }
    this.ctrlInit = function ctrlInit() {
      $scope.loginService.init(function () {
        controller.loadDisplayPage();
        $scope.language = $scope.languageMenu[0];
      });
    };
    this.ctrlInit();
  }
]);
'use strict';
angular.module('ark-components').directive('arkLogin', [
  '$window',
  function ($window) {
    return {
      restrict: 'E',
      transclude: true,
      scope: {
        genesysLogoLink: '@logoLink',
        forgotPassword: '=',
        loginService: '=',
        remoteMessageUrl: '@'
      },
      controller: 'arkLoginCtrl',
      templateUrl: 'ark-login/ark-login.html',
      link: function ($scope, element, attrs) {
        $scope.showLanguageBar = !angular.isDefined(attrs.showLanguageBar) ? true : $scope.$eval(attrs.showLanguageBar);
        $scope.isPasswordMandatory = !angular.isDefined(attrs.isPasswordMandatory) ? true : $scope.$eval(attrs.isPasswordMandatory);
        $scope.errorField = !angular.isDefined(attrs.errorField) ? undefined : attrs.errorField;
        $scope.showForgotPassword = angular.isDefined(attrs.forgotPassword);
        $scope.forgotPasswordFn = typeof $scope.forgotPassword === 'function' ? $scope.forgotPassword : function () {
          $window.open($scope.forgotPassword);
        };
        $scope.$watch('language', function (newValue) {
          if (newValue) {
            $scope.loginService.changeLanguage(newValue.value, function (data) {
              $scope.formTitle = data.loginFormTitle;
              $scope.errorMessages = data.errorMessages;
              var type = $scope.errorMsgType;
              $scope.errorMessage = $scope.language.errorMsg[type];
            });
          }
        }, true);
      }
    };
  }
]);
/**
 * @ngdoc controller
 * @name arkNavbarCtrl
 * @description
 *     Provides implementation for the Navigation Bar Controller
 */
'use strict';
angular.module('ark-components').controller('arkNavbarCtrl', [
  'navigationBarService',
  '$scope',
  '$timeout',
  function (navigationBarService, $scope, $timeout) {
    $scope.sDefaultI18n = 'en-US';
    $scope.hasContent = false;
    $scope.isSearching = false;
    $scope.displayDropdown = false;
    $scope.items = [];
    $scope.searchbar = { searchText: '' };
    $scope.updateNavigation = function () {
      var oJSON = navigationBarService.getNavigationJSON();
      if (oJSON) {
        $scope.navigationJSON = oJSON;
        if ($scope.navigationJSON.i18n[navigationBarService.getI18n()]) {
          $scope.i18n = $scope.navigationJSON.i18n[navigationBarService.getI18n()];
        } else {
          $scope.i18n = $scope.navigationJSON.i18n[$scope.sDefaultI18n];
        }
      }
    };
    $scope.matchRoute = function (sRoute) {
      if (navigationBarService.matchRoute) {
        return navigationBarService.matchRoute(sRoute);
      }
      return {
        module: false,
        subModule: false
      };
    };
    $scope.clearInputText = function () {
      $scope.searchbar.searchText = '';
    };
    $scope.clickItem = function (selectedItem) {
      $scope.search.selectFunction(selectedItem);
    };
    $scope.searchForContent = function (searchText) {
      $scope.isSearching = true;
      $scope.prevSearchText = searchText;
      $scope.search.filterFunction(searchText, function (data) {
        $scope.items = $scope.itemsLength ? data.slice(0, parseInt($scope.itemsLength)) : data.slice(0, 3);
        $scope.isSearching = false;
        $scope.displayDropdown = true;
      });
    };
    navigationBarService.onJSONUpdate(function () {
      $timeout(function () {
        $scope.updateNavigation();
      });
    });
    $scope.updateNavigation();
  }
]);
'use strict';
angular.module('ark-components').directive('arkNavbar', [
  '$timeout',
  '$templateCache',
  '_',
  function ($timeout, $templateCache, _) {
    return {
      restrict: 'E',
      scope: { search: '=searchAction' },
      transclude: false,
      replace: true,
      templateUrl: 'ark-navbar/ark-navbar.html',
      controller: 'arkNavbarCtrl',
      link: function ($scope) {
        $scope.newSearchText = '';
        var deferSearch = _.throttle(function (newVal) {
            if ($scope.newSearchText === newVal && $scope.searchbar.searchText) {
              $scope.searchForContent(newVal);
            }
          }, 300);
        $scope.$watch('searchbar.searchText', function (newVal) {
          if (!newVal) {
            $scope.hasContent = false;
            $scope.displayDropdown = false;
          } else {
            $scope.hasContent = true;
            $scope.newSearchText = newVal;
            deferSearch(newVal);
          }
        });
      }
    };
  }
]).directive('stopClose', function () {
  return {
    restrict: 'A',
    link: function (scope, element) {
      element.bind('click', function (event) {
        event.preventDefault();
        event.stopPropagation();
      });
    }
  };
});
'use strict';
(function (d) {
  var b = '[data-toggle="dropdown"]', a = function (f) {
      var e = d(f).on('click.dropdown.data-api', this.toggle);
      d('html').on('click.dropdown.data-api', function () {
        if (!e.hasClass('dropdown-nested')) {
          e.parent().removeClass('open');
        }
      });
    };
  a.prototype = {
    constructor: a,
    toggle: function (j) {
      var i = d(this), h, f, g;
      if (i.is('.disabled, :disabled')) {
        return;
      }
      f = i.attr('data-target');
      if (!f) {
        f = i.attr('href');
        f = f && f.replace(/.*(?=#[^\s]*$)/, '');
      }
      h = d(f);
      if (!h.length) {
        h = i.parent();
      }
      g = h.hasClass('open');
      var isNested = i.hasClass('dropdown-nested');
      if (!g && isNested) {
        h.addClass('nesting');
      } else {
        c();
      }
      if (!g) {
        $('.dropdown.open.nesting').removeClass('open nesting');
        h.toggleClass('open');
      }
      return false;
    }
  };
  function c() {
    d(b).parent().removeClass('open');
  }
  d.fn.dropdown = function (e) {
    return this.each(function () {
      var g = d(this), f = g.data('dropdown');
      if (!f) {
        g.data('dropdown', f = new a(this));
      }
      if (typeof e === 'string') {
        f[e].call(g);
      }
    });
  };
  d.fn.dropdown.Constructor = a;
  d(function () {
    d('html').on('click.dropdown.data-api', c);
    d('body').on('click.dropdown', '.dropdown form', function (f) {
      f.stopPropagation();
    }).on('click.dropdown.data-api', b, a.prototype.toggle);
  });
}(window.jQuery));
'use strict';
angular.module('ark-components').controller('arkNestedSearchCtrl', [
  '$scope',
  '$timeout',
  function ($scope, $timeout) {
    $scope.searchResults = [];
    $scope.currSearchIndex = '';
    $scope.collapseList = [];
    $scope.$watch('search.searchValue', function (newValue, oldValue) {
      if (newValue !== oldValue) {
        $scope.delayPromise = $timeout(function () {
          //delayed call will finally run after 'delay' amount of ms after the
          //input stops changing
          if (newValue !== $scope.search.searchValue) {
            return;
          }
          // Searching start
          //case sensitivity is set here
          var searchValue = $scope.config.caseSensitive ? newValue : newValue.toLowerCase();
          //if the query is not the required length, just clear all results and do nothing
          if (searchValue.length < $scope.config.minChars) {
            $scope.clearSearchResults();
            $scope.lastSearch = '';
          }  //if the query is a continuation of a previous query, ex. 'Suga' -> 'Sugar'
          else if ($scope.lastSearch && $scope.lastSearch.length !== 0 && searchValue.indexOf($scope.lastSearch) === 0) {
            var tempList = [];
            //loop through previous query's results
            for (var i = 0; i < $scope.searchResults.length; i++) {
              //loop through searchable fields
              for (var j = 0; j < $scope.config.searchParam.length; j++) {
                //string compare is the field value to compare the query with
                //if the field matches the query, keep it. Otherwise reset it
                if (typeof $scope.searchResults[i][0][$scope.config.searchParam[j]] === 'string') {
                  var stringCompare = $scope.config.caseSensitive ? $scope.searchResults[i][0][$scope.config.searchParam[j]] : $scope.searchResults[i][0][$scope.config.searchParam[j]].toLowerCase();
                  if ($scope.config.indexSensitive ? stringCompare.indexOf(searchValue) === 0 : stringCompare.indexOf(searchValue) >= 0) {
                    tempList.push($scope.searchResults[i]);
                    break;
                  } else {
                    $scope.searchResults[i][0].secondarySearchResult = false;
                    $scope.searchResults[i][0].primarySearchResult = false;
                    $scope.toggleExpand(false, i);
                  }
                }
              }
            }
            $scope.searchResults = tempList;
            //go to first result
            $scope.switchPrimaryResult('init');
            $scope.lastSearch = searchValue;
          } else {
            $scope.clearSearchResults();
            //call the recursive search for every tree in the forest
            $scope.currDepth = 0;
            for (var k = 0; k < $scope.model.length; k++) {
              $scope.recursiveSearch($scope.model[k], searchValue, $scope.recursionResultFound);
            }
            //go to first result
            $scope.switchPrimaryResult('init');
            $scope.lastSearch = searchValue;
          }
          if ($scope.callback) {
            $scope.callback({ results: $scope.searchResults });
          }
          $timeout.cancel($scope.delayPromise);
          $scope.delayPromise = null;
        }, $scope.config.delay);
      }
    });
    $scope.recursiveSearch = function (currNode, searchValue, callback) {
      $scope.currDepth += 1;
      //only search the fields if the node is of required depth
      if ($scope.currDepth >= $scope.config.minDepth) {
        //loop through searchable fields
        for (var i = 0; i < $scope.config.searchParam.length; i++) {
          //string compare is the field value to compare the query with
          if (typeof currNode[$scope.config.searchParam[i]] === 'string') {
            var stringCompare = $scope.config.caseSensitive ? currNode[$scope.config.searchParam[i]] : currNode[$scope.config.searchParam[i]].toLowerCase();
            if ($scope.config.indexSensitive ? stringCompare.indexOf(searchValue) === 0 : stringCompare.indexOf(searchValue) >= 0) {
              callback(currNode);
              break;
            }
          }
        }
      }
      //if the node is not expanded, push it into stack as a non-expanded parent node
      if (!currNode[$scope.config.expandedParam]) {
        $scope.collapseList.push(currNode);
      }
      //recurse
      if ($scope.currDepth <= $scope.config.maxDepth && currNode[$scope.config.subTreeParam]) {
        for (var j = 0; j < currNode[$scope.config.subTreeParam].length; j++) {
          $scope.recursiveSearch(currNode[$scope.config.subTreeParam][j], searchValue, callback);
        }
      }
      //pop the non-expanded parent node
      if (!currNode[$scope.config.expandedParam]) {
        $scope.collapseList.pop();
      }
      $scope.currDepth -= 1;
    };
    $scope.recursionResultFound = function (currNode) {
      //if the field matches the query, push the following pair:
      // ['matched node','non-expanded parentNodes']
      //set as secondary result
      var tempIndex = $scope.searchResults.push([
          currNode,
          $scope.collapseList.slice(0)
        ]) - 1;
      currNode.secondarySearchResult = true;
      if ($scope.config.expandResults === 'find') {
        $scope.toggleExpand(true, tempIndex);
      }
    };
    $scope.switchPrimaryResult = function (option) {
      switch (option) {
      case 'init':
        //set first result as primary result
        if ($scope.searchResults.length > 0) {
          $scope.currSearchIndex = 0;
          $scope.searchResults[$scope.currSearchIndex][0].primarySearchResult = true;
        }
        break;
      case 'next':
        //next result button
        $scope.searchResults[$scope.currSearchIndex][0].primarySearchResult = false;
        $scope.toggleExpand(false, $scope.currSearchIndex);
        $scope.currSearchIndex = $scope.currSearchIndex >= 0 && $scope.currSearchIndex < $scope.searchResults.length - 1 ? $scope.currSearchIndex + 1 : 0;
        $scope.searchResults[$scope.currSearchIndex][0].primarySearchResult = true;
        break;
      case 'previous':
        //previous result button
        $scope.searchResults[$scope.currSearchIndex][0].primarySearchResult = false;
        $scope.toggleExpand(false, $scope.currSearchIndex);
        $scope.currSearchIndex = $scope.currSearchIndex > 0 ? $scope.currSearchIndex - 1 : $scope.searchResults.length - 1;
        $scope.searchResults[$scope.currSearchIndex][0].primarySearchResult = true;
        break;
      }
      $scope.toggleExpand(true, $scope.currSearchIndex);
    };
    $scope.toggleExpand = function (option, index) {
      //loop through a search results list of non-expanded parent nodes, and expand them
      if ($scope.searchResults.length > 0 && $scope.searchResults[index][1]) {
        for (var h = 0; h < $scope.searchResults[index][1].length; h++) {
          $scope.searchResults[index][1][h][$scope.config.expandedParam] = option;
        }
      }
    };
    $scope.clearSearchResults = function () {
      for (var k = 0; k < $scope.searchResults.length; k++) {
        $scope.searchResults[k][0].secondarySearchResult = false;
        $scope.searchResults[k][0].primarySearchResult = false;
        $scope.toggleExpand(false, k);
      }
      $scope.searchResults = [];
      $scope.collapseList = [];
      $scope.currSearchIndex = '';
    };
    $scope.searchKeyPress = function ($event) {
      //link up and down arrows to next and previous buttons
      if ($scope.searchResults.length) {
        if ($event.which === 40) {
          $scope.switchPrimaryResult('next');
          $event.preventDefault();
        } else if ($event.which === 38) {
          $scope.switchPrimaryResult('previous');
          $event.preventDefault();
        }
      }
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkNestedSearch', function () {
  return {
    restrict: 'E',
    scope: {
      config: '=searchOptions',
      model: '=treeModel',
      callback: '&'
    },
    templateUrl: 'ark-nested-search/ark-nested-search.html',
    controller: 'arkNestedSearchCtrl',
    link: function (scope) {
      //Setting Defaults
      scope.config.caseSensitive = scope.config.caseSensitive || false;
      scope.config.indexSensitive = scope.config.indexSensitive || false;
      scope.config.maxDepth = scope.config.maxDepth || Number.POSITIVE_INFINITY;
      scope.config.minDepth = scope.config.minDepth || 0;
      scope.config.expandResults = scope.config.expandResults || 'focus';
      // can be set to 'focus' or 'find'
      scope.config.searchParam = scope.config.searchParam || ['label'];
      scope.config.subTreeParam = scope.config.subTreeParam || 'items';
      scope.config.expandedParam = scope.config.expandedParam || 'expanded';
      // can be set to an array of node properties to search through aswell
      scope.config.delay = scope.config.delay || 0;
      scope.config.minChars = scope.config.minChars || 1;
      scope.search = { searchValue: '' };
    }
  };
});
'use strict';
angular.module('ark-components').directive('arkNestedTree', [
  '$rootScope',
  function ($rootScope) {
    return {
      restrict: 'AE',
      scope: {
        treeName: '@',
        model: '=treeModel',
        config: '=treeConfig',
        setSelection: '=',
        setCheckbox: '=',
        lazyLoading: '@useLazyLoading',
        restService: '=',
        setEdited: '=',
        startEditing: '=',
        preselectedNodeId: '=?preselectedNodeId'
      },
      templateUrl: 'ark-nested-tree/ark-nested-tree.html',
      controller: 'dropdownTreeCtrl',
      link: function (scope, element, attr) {
        $rootScope.templateIndex = 0;
        scope.checkbox = scope.$eval(attr.checkbox) || false;
        scope.editMode = scope.$eval(attr.editMode) || false;
        scope.lazyLoading = scope.$eval(attr.lazyLoading) || false;
        scope.showBorder = angular.isDefined(attr.showBorder) ? scope.$eval(attr.showBorder) : true;
        scope.dropdownArrow = angular.isDefined(attr.dropdownArrow) ? scope.$eval(attr.dropdownArrow) : true;
        scope.highlightNode = scope.$eval(attr.highlight);
        // If the user does not specify a 'highlight', then we fall back on whether checkbox is enabled or not.
        if (scope.highlightNode === undefined) {
          scope.highlightNode = !scope.checkbox;
        }
        // Object that keeps track of tree properties
        scope.treeInfo = { currentSelectedNode: null };
        scope.element = element;
        if (scope.useLeafsOnly) {
          scope.useLeafsOnly = true;
        } else {
          scope.useLeafsOnly = false;
        }
      }
    };
  }
]);
'use strict';
angular.module('ark-components').factory('ArkNestedTreeService', function () {
  var nestedTree = {};
  //Used for augmenting nodes before rendering the
  //tree for the first time. Called from the controller
  nestedTree.augmentNode = function (node, parentNode) {
    var parentId = parentNode.id || 0;
    node.isShow = node.isShow || true;
    node.expanded = node.expanded || false;
    node.parentId = parentId;
    node.isGroup = node.items ? true : false;
    var checkedCount = 0;
    var isMid = false;
    if (node.items) {
      for (var i = 0; i < node.items.length; i++) {
        nestedTree.augmentNode(node.items[i], node);
        if (node.items[i].isChecked && !node.items[i].isMid) {
          checkedCount++;
        }
        if (node.items[i].isMid) {
          isMid = true;
        }
      }
    }
    node.isMid = node.isMid || (isMid || checkedCount > 0) && checkedCount !== node.items.length || false;
    node.isChecked = parentNode.isChecked || node.isMid || node.isChecked || node.items && (node.items.length > 0 && checkedCount === node.items.length) || false;
  };
  nestedTree.addNode = function (node, parentNode) {
    var toSearch = null;
    if (parentNode.items && !parentNode.length) {
      toSearch = parentNode.items;
      nestedTree.augmentNode(node, parentNode);
    } else if (!parentNode.items && parentNode.length) {
      toSearch = parentNode;
      nestedTree.augmentNode(node, parentNode);
    }
    var notThere = false;
    for (var i = 0; i < toSearch.length; i++) {
      if (toSearch[i].id === node.id) {
        notThere = true;
        break;
      }
    }
    if (!notThere) {
      toSearch.push(node);
    }
  };
  nestedTree.deleteNode = function (nodeId, parentNode) {
    if (parentNode) {
      var toSearch = null;
      if (parentNode.items && !parentNode.length) {
        toSearch = parentNode.items;
      } else if (!parentNode.items && parentNode.length) {
        toSearch = parentNode;
      }
      for (var i = 0; i < toSearch.length; i++) {
        if (nodeId === toSearch[i].id) {
          toSearch.splice(i, 1);
          break;
        }
      }
    }
  };
  return nestedTree;
});
/*
  @license Angular Treeview version 0.1.6
  ⓒ 2013 AHN JAE-HA http://github.com/eu81273/angular.treeview
  License: MIT
*/
/*jshint funcscope:true*/
/*jshint shadow:true*/
'use strict';
angular.module('ark-components').directive('treeAutofocus', [
  '$timeout',
  function ($timeout) {
    return {
      link: function (scope, element, attrs) {
        var focusValue = attrs.treeAutofocus;
        if (focusValue) {
          $timeout(function () {
            element[0].focus();
          });
        }
      }
    };
  }
]).directive('treeEnter', function () {
  return function (scope, element, attrs) {
    element.bind('keydown keypress', function (event) {
      if (event.which === 13) {
        scope.$apply(function () {
          scope.$eval(attrs.treeEnter);
        });
        event.preventDefault();
      }
    });
  };
}).directive('treeModel', [
  '$compile',
  '$log',
  '$templateCache',
  '$rootScope',
  function ($compile, $log, $templateCache, $rootScope) {
    return {
      restrict: 'AE',
      link: function (scope, element, attrs) {
        var defaultTreeConfig = {
            'use-inline-controls': false,
            'enable-add-group-control': true,
            'add-group-icon': 'icon-folder-add',
            'add-group-callback': null,
            'enable-add-item-control': true,
            'add-item-icon': 'icon-add',
            'add-item-callback': null,
            'enable-delete-item-control': true,
            'delete-item-icon': 'icon-trash',
            'delete-item-callback': null,
            'allow-folder-edition': true,
            'max-group-depth': 3
          };
        scope.tempCheckedOptions = [];
        var treeId = attrs.treeId;
        //tree model
        var treeModel = attrs.treeModel || 'model';
        var nodeId = attrs.nodeId || 'id';
        var nodeLeafIds = attrs.nodeLeafIds || 'leafIds';
        var nodeLabel = attrs.nodeLabel || 'label';
        var nodeIcon = attrs.nodeIcon || 'icon';
        var nodeChildren = attrs.nodeChildren || 'items';
        var numOfChildren = attrs.numOfChildren || 'numberOfItems';
        var treeName = attrs.treeName || '';
        var selectorIndex = attrs.selectorIndex || '0';
        var nodeHtmlContent = attrs.nodeHtmlContent || 'htmlContent';
        var maxChildHeight = attrs.maxChildHeight || 'maxHeight';
        var levelDepth = parseInt(attrs.levelDepth) + 1;
        var treeConfig = angular.extend(defaultTreeConfig, scope.config || {});
        //var parentId = parseInt(attrs.parentId) || '0';
        var selectedShowCondition = '(node.isChecked || !selectedOnly) && node.isShow';
        var showExpandCollapseCondition = '(dropdownArrow && !node.unselectable && (node.' + numOfChildren + ' || node.' + nodeChildren + '.length))';
        var previousNodeEditingValue = {};
        var currentTargetAction;
        //tree template
        var template = '<ul ng-class="{\'default-cursor\': editMode, \'max-height-set\': node.' + maxChildHeight + ' && (node.' + numOfChildren + ' > node.' + maxChildHeight + ' || node.' + nodeChildren + '.length > node.' + maxChildHeight + ')}" style="max-height: {{ node.' + maxChildHeight + '*23.55 }}px">' + '<li ng-repeat="node in ' + treeModel + '" ng-class="{\'first-depth\' : ' + levelDepth + ' === 1}">' + '<div class="node-row-container" ng-init="initSelectedNode(node)" ng-class="{\'node-selected\': node.isSelected && highlightNode, \'highlight-node\': highlightNode, \'unselectable\' : node.unselectable}" ng-click="setSelectedNode()" >' + '<span class="blank" ng-show="(' + levelDepth + ' === 1 && !' + showExpandCollapseCondition + ' && ' + selectedShowCondition + ') || (' + levelDepth + '!== 1 && (!dropdownArrow || node.unselectable) && (node.' + numOfChildren + ' || node.' + nodeChildren + '.length))"><span class="blank fonticon icon-chevron-left"></span></span>' + '<span class="elbow" ng-show="' + levelDepth + ' !== 1 && !node.' + nodeChildren + '.length && !node.' + numOfChildren + ' && ' + selectedShowCondition + '"><span class="elbow fonticon icon-chevron-left"></span></span>' + '<span class="collapsed" ng-show="' + showExpandCollapseCondition + ' && !node.expanded && ' + selectedShowCondition + '" ng-click="' + treeId + '.selectNode(node)"><span class="collapsed fonticon icon-dropdown-arrow"></span></span>' + '<span class= "expanded" ng-show="' + showExpandCollapseCondition + ' && node.expanded  && ' + selectedShowCondition + '" ng-click="' + treeId + '.selectNode(node)"><span class="expanded fonticon icon-dropdown-arrow"></span></span>' + '<span ng-if="(checkbox) || (!checkbox && node.needCheckbox)">' + '<span ng-if="node.needCheckbox !== false">' + '<span class="triCheckbox" ng-show="' + selectedShowCondition + '" ng-class="{\'mid\' : node.isMid, \'checked\' : node.isChecked}" ng-click="(' + scope.useLeafsOnly + ' && node.' + numOfChildren + ') ||' + treeId + '.selectCheckbox(node);">' + '<span class="fonticon" ng-show="' + !scope.useLeafsOnly + ' || !node.' + numOfChildren + '" ng-class="{\'icon-checkbox\' : !node.isChecked && !node.isMid, \'icon-checkbox-tick\' : node.isChecked && !node.isMid, \'icon-select-yes\' : node.isChecked && node.isMid}"></span>' + '<span class="fonticon" ng-show="' + scope.useLeafsOnly + ' && node.' + numOfChildren + '" ng-class="{\'icon-folder\' : !node.expanded, \'icon-folder-open\' : node.expanded}" ng-click="' + treeId + '.selectNode(node)"></span></span>' + '</span>' + '</span>' + '<span ng-if="(checkbox && (node.needCheckbox === false))" class="need-checkbox-off-padding"></span>' + '<span ng-if="!node.' + nodeHtmlContent + '" class="node-label" ng-show="' + selectedShowCondition + ' && !editMode" ng-click="' + treeId + '.selectNode(node)"><span class="nodeLabel" ng-class="{primarySearchResult: node.primarySearchResult, secondarySearchResult: node.secondarySearchResult, \'unselectable\' : node.unselectable}"><span ng-if="hasIcons()" class="fonticon {{node.' + nodeIcon + '}}"></span>{{node.' + nodeLabel + '}}</span></span>' + '<span ng-if="node.' + nodeHtmlContent + '" class="node-label" ng-init="createLabelTemplate(node)" ng-show="' + selectedShowCondition + ' && !editMode" ng-click="' + treeId + '.selectNode(node)"><span class="nodeLabel" ng-class="{primarySearchResult: node.primarySearchResult, secondarySearchResult: node.secondarySearchResult, \'unselectable\' : node.unselectable}"><span ng-if="hasIcons()" class="fonticon {{node.' + nodeIcon + '}}"></span><span ng-include="node.templateUrl" ng-class="{\'unselectable\' : node.unselectable}"></span></span></span>' + '<span ng-if="editMode" class="edit-wrapper" ng-init="node.isEditing=((node.isNew) ? true:false)"><input class="form-control" type="text" ng-model="node.' + nodeLabel + '" tree-enter="setEditMode(node.isEditing)" ng-if="node.isEditing" ng-blur="setEditMode(node.isEditing)" tree-autofocus="true"/><span class="edit-label" ng-click="setEditMode(node.isEditing)" ng-if="!node.isEditing" ng-class="{primarySearchResult: node.primarySearchResult, secondarySearchResult: node.secondarySearchResult, \'unselectable\' : node.unselectable}"><span ng-if="hasIcons()" class="fonticon {{node.' + nodeIcon + '}}"></span>{{node.' + nodeLabel + '}}</span></span>' + '<span class="inline-controls" ng-show="' + treeConfig['use-inline-controls'] + '">' + '<a class="pull-right inline-control-icon" ng-show="' + treeConfig['enable-delete-item-control'] + '"><span class="fonticon ' + treeConfig['delete-item-icon'] + '" ng-click="deleteNode()"></span></a>' + '<a class="pull-right inline-control-icon" ng-show="{{' + (treeConfig['enable-add-group-control'] && levelDepth < treeConfig['max-group-depth']) + ' && node.isGroup }}"><span class="fonticon ' + treeConfig['add-group-icon'] + '" ng-click="addGroupToNode()"></span></a>' + '<a class="pull-right inline-control-icon" ng-show="{{' + (treeConfig['enable-add-item-control'] && levelDepth < treeConfig['max-group-depth']) + ' && node.isGroup }}"><span class="fonticon ' + treeConfig['add-item-icon'] + '" ng-click="addItemToNode()"></span></a>' + '</span>' + '</div>' + '<span ng-show="node.expanded && ' + selectedShowCondition + '" tree-id="' + treeId + '" tree-model="node.' + nodeChildren + '" node-id="' + nodeId + '" node-label="' + nodeLabel + '" node-children="' + nodeChildren + '" tree-name="' + treeName + '" level-depth="' + levelDepth + '" selector-index = "' + selectorIndex + '"></span>' + '</li>' + '</ul>';
        scope.createLabelTemplate = function (node) {
          var newUrl = 'label-template' + $rootScope.templateIndex++;
          $templateCache.put(newUrl, node.htmlContent);
          node.templateUrl = newUrl;
        };
        scope.addItemToNode = function () {
          scope.node.expanded = true;
          scope.node[nodeChildren].push({
            label: '',
            parentId: scope.node.id || 0,
            isShow: true,
            isEditing: true,
            isNew: true
          });
        };
        scope.addGroupToNode = function () {
          scope.node.expanded = true;
          scope.node[nodeChildren].push({
            label: '',
            parentId: scope.node.id || 0,
            isShow: true,
            isGroup: true,
            isEditing: true,
            isNew: true,
            items: []
          });
        };
        scope.deleteNode = function () {
          if (treeConfig['delete-item-callback']) {
            treeConfig['delete-item-callback'](scope.node);
          }
        };
        scope.setEditMode = function (oldValue) {
          if (scope.node[nodeChildren] && treeConfig['allow-folder-edition'] || !scope.node[nodeChildren]) {
            scope.node.isEditing = !oldValue;
            if (oldValue) {
              if (scope.node.isNew) {
                //Give users capability to provide callbacks for when new group/item is created and has been edited.
                scope.node.isNew = false;
                if (!scope.node.isGroup && typeof treeConfig['add-item-callback'] === 'function') {
                  treeConfig['add-item-callback'](scope.node);
                } else if (scope.node.isGroup && typeof treeConfig['add-group-callback'] === 'function') {
                  treeConfig['add-group-callback'](scope.node);
                }
              } else if (typeof scope.setEdited === 'function') {
                //Give users capability to provide a callback once a node value has changed providing previous and updated node values.
                scope.setEdited(previousNodeEditingValue, scope.node);
              }
              currentTargetAction = undefined;
              previousNodeEditingValue = {};
            } else {
              if (typeof scope.startEditing === 'function') {
                scope.startEditing(scope.node);
              }
              previousNodeEditingValue = angular.copy(scope.node);
            }
          }
        };
        scope.hasIcons = function () {
          var toReturn = scope.node[nodeIcon] ? true : false;
          return toReturn;
        };
        scope.setSelectedNode = function () {
          if (!scope.node.unselectable) {
            if (scope.treeInfo.currentSelectedNode) {
              scope.treeInfo.currentSelectedNode.isSelected = false;
            }
            scope.node.isSelected = true;
            scope.treeInfo.currentSelectedNode = scope.node;
          }
        };
        // initialize node as selected or unselected
        scope.initSelectedNode = function (node) {
          if (angular.isDefined(node.id) && node.id === scope.preselectedNodeId) {
            node.isSelected = true;
            scope.treeInfo.currentSelectedNode = node;
            var parentId = node.parentId;
            // expands all parents of selected node
            while (parentId !== 0) {
              parentId = expandParent(scope.model, parentId);
            }
          } else {
            node.isSelected = false;
          }
        };
        // expands parent of selected node
        var expandParent = function (object, nodeId) {
          // checks all surface level nodes for id
          for (var i = 0; i < object.length; i++) {
            if (object[i].id === nodeId) {
              object[i].expanded = true;
              return object[i].parentId;
            }
          }
          // checks items of surface level nodes for id
          for (var i = 0; i < object.length; i++) {
            if (object[i].items) {
              var returnedId = expandParent(object[i].items, nodeId);
              if (returnedId) {
                return returnedId;
              }
            }
          }
          // returns 0 if id is not found in branch
          return 0;
        };
        var expandCollapseNode = function (selectedNode) {
          if (selectedNode[nodeChildren] && selectedNode.expanded) {
            for (var i = 0; i < selectedNode[nodeChildren].length; i++) {
              selectedNode[nodeChildren][i].isShow = true;
              selectedNode[nodeChildren][i].expanded = false;
            }
          }
        };
        var addSelectedNodesToModel = function (nodesList) {
          if (!angular.isArray(nodesList)) {
            return;
          }
          angular.forEach(nodesList, function (node) {
            if (!scope.useLeafsOnly) {
              if (node.isChecked && !node.isMid) {
                if (scope.useLeafIds) {
                  angular.forEach(node[nodeLeafIds], function (id) {
                    scope.model.values.push(id);
                  });
                } else {
                  scope.model.values.push(node[nodeId]);
                }
                scope.model.names.push(node[nodeLabel]);
              } else if (node.isMid) {
                addSelectedNodesToModel(node[nodeChildren]);
              }  // useLeafsOnly: do not add ids of nodes that have children (leaf nodes only)
            } else {
              if (node.isChecked) {
                if (!node.numberOfItems) {
                  scope.model.values.push(node[nodeId]);
                  if (node.externalId) {
                    scope.model.names.push(node.externalId);
                  } else {
                    scope.model.names.push(node[nodeLabel]);
                  }
                } else {
                  addSelectedNodesToModel(node[nodeChildren]);
                }
              }
            }
          });
        };
        //check tree id, tree model
        if (treeId && treeModel) {
          //root node
          if (attrs.filterTreeview) {
            //create tree object if not exists
            scope[treeId] = scope[treeId] || {};
            //if node head clicks,
            scope[treeId].selectNode = scope[treeId].selectNode || function (selectedNode) {
              //remove in ark code
              if (angular.isDefined(scope.setSelection)) {
                scope.setSelection(selectedNode);
              }
              //Collapse or Expand
              if (!selectedNode.unselectable) {
                selectedNode.expanded = !selectedNode.expanded;
              }
              var hasChildrenToLoad = selectedNode[numOfChildren] > 0 && (!selectedNode[nodeChildren] || !selectedNode[nodeChildren].length);
              var useLazyLoading = scope.lazyLoading;
              if (useLazyLoading && selectedNode.expanded && hasChildrenToLoad) {
                // lazy load node children
                if (scope.restService) {
                  scope.restService.getNodeChildren(treeName, selectedNode[nodeId], function (nodeChildrenItems) {
                    angular.forEach(nodeChildrenItems, function (node) {
                      node.isChecked = node.isChecked || false;
                      node.isMid = node.isMid || false;
                      node.isShow = node.isShow || true;
                      node.expanded = node.expanded || false;
                      node.parentId = selectedNode[nodeId];
                      if (selectedNode.isChecked) {
                        node.isChecked = true;
                      }
                    });
                    selectedNode[nodeChildren] = nodeChildrenItems;
                    expandCollapseNode(selectedNode);
                  });
                } else {
                  $log.error('No service is provided for lazy loading');
                }
              }
            };
            //update data in service (excuted any time a checkbox state is toggled)
            scope[treeId].updateSelected = scope[treeId].updateSelected || function () {
              if (scope.model.values && scope.model.names) {
                // clear the data model:
                scope.model.values.splice(0, scope.model.values.length);
                scope.model.names.splice(0, scope.model.names.length);
                // add all the selected items back to the data model:
                addSelectedNodesToModel(scope[treeModel]);
              }
            };
            //checkbox helper functions
            scope[treeId].checkBox = scope[treeId].checkBox || function (selectedNode) {
              selectedNode.isChecked = true;
              selectedNode.isMid = false;
              scope[treeId].updateSelected();
              scope.tempCheckedOptions.push({
                node: selectedNode,
                checkType: 'checked'
              });
            };
            scope[treeId].uncheckBox = scope[treeId].uncheckBox || function (selectedNode) {
              selectedNode.isChecked = false;
              selectedNode.isMid = false;
              scope[treeId].updateSelected();
              scope.tempCheckedOptions.push({
                node: selectedNode,
                checkType: 'unchecked'
              });
            };
            scope[treeId].midcheckBox = scope[treeId].midcheckBox || function (selectedNode) {
              selectedNode.isChecked = true;
              selectedNode.isMid = true;
              scope[treeId].updateSelected();
              scope.tempCheckedOptions.push({
                node: selectedNode,
                checkType: 'midchecked'
              });
            };
            //recursive functions
            scope[treeId].checkAllChildren = function (node) {
              if (node[nodeChildren]) {
                for (var i = 0; i < node[nodeChildren].length; i++) {
                  scope[treeId].checkBox(node[nodeChildren][i]);
                  scope[treeId].checkAllChildren(node[nodeChildren][i]);
                }
              }
            };
            scope[treeId].uncheckAllChildren = function (node) {
              if (node[nodeChildren]) {
                for (var i = 0; i < node[nodeChildren].length; i++) {
                  scope[treeId].uncheckBox(node[nodeChildren][i]);
                  scope[treeId].uncheckAllChildren(node[nodeChildren][i]);
                }
              }
            };
            scope[treeId].selectCheckbox = scope[treeId].selectCheckbox || function (selectedNode) {
              //if box is unchecked or midchecked
              if (!selectedNode.isChecked || selectedNode.isMid) {
                scope[treeId].checkBox(selectedNode);
                //recursively check all children
                scope[treeId].checkAllChildren(selectedNode);
                //recursive function that updates parent checkboxes when a child is checked
                scope[treeId].checkParent = function (node, nodeChild) {
                  var isChild = false;
                  //go through every child and verify if nodeChild is one of them
                  if (node[nodeChildren]) {
                    for (var i = 0; i < node[nodeChildren].length; i++) {
                      if (node[nodeChildren][i] === nodeChild) {
                        isChild = true;
                        break;
                      }
                    }
                  }
                  //we're studying the children of the parent of the node
                  //we know that the nodeChild is checked, but his siblings might not be
                  //go through every child and verify if they are all checked
                  if (isChild) {
                    var allChecked = true;
                    if (node[nodeChildren]) {
                      for (var i = 0; i < node[nodeChildren].length; i++) {
                        if (!node[nodeChildren][i].isChecked || node[nodeChildren][i].isMid) {
                          allChecked = false;
                          break;
                        }
                      }
                    }
                    if (allChecked) {
                      scope[treeId].checkBox(node);
                      //if the checked node isn't at the root, repeat
                      var isRoot = false;
                      for (var i = 0; i < scope[treeModel].length; i++) {
                        if (node === scope[treeModel][i]) {
                          isRoot = true;
                          break;
                        }
                      }
                      if (!isRoot) {
                        for (var k = 0; k < scope[treeModel].length; k++) {
                          scope[treeId].checkParent(scope[treeModel][k], node);
                        }
                      }
                    } else {
                      scope[treeId].midcheckBox(node);
                      //if the checked node isn't at the root, repeat
                      isRoot = false;
                      for (var i = 0; i < scope[treeModel].length; i++) {
                        if (node === scope[treeModel][i]) {
                          isRoot = true;
                          break;
                        }
                      }
                      if (!isRoot) {
                        for (var k = 0; k < scope[treeModel].length; k++) {
                          scope[treeId].checkParent(scope[treeModel][k], node);
                        }
                      }
                    }  //if child isn't found then proceed a level deeper
                  } else {
                    if (node[nodeChildren]) {
                      for (var i = 0; i < node[nodeChildren].length; i++) {
                        scope[treeId].checkParent(node[nodeChildren][i], nodeChild);
                      }
                    }
                  }
                };
                //goes through each child of the root
                for (var j = 0; j < scope[treeModel].length; j++) {
                  scope[treeId].checkParent(scope[treeModel][j], selectedNode);
                }  //if box is checked
              } else if (!selectedNode.isMid) {
                scope[treeId].uncheckBox(selectedNode);
                //recursively uncheck all children
                scope[treeId].uncheckAllChildren(selectedNode);
                //recursive function that updates parent checkboxes when a child is checked
                scope[treeId].uncheckParent = function (node, nodeChild) {
                  var isChild = false;
                  //go through every child and check if nodeChild is one of them
                  if (node[nodeChildren]) {
                    for (var i = 0; i < node[nodeChildren].length; i++) {
                      if (node[nodeChildren][i] === nodeChild) {
                        isChild = true;
                        break;
                      }
                    }
                  }
                  //go through every child and check if they are all unchecked
                  if (isChild) {
                    var allUnchecked = true;
                    if (node[nodeChildren]) {
                      for (var i = 0; i < node[nodeChildren].length; i++) {
                        if (node[nodeChildren][i].isChecked) {
                          allUnchecked = false;
                          break;
                        }
                      }
                    }
                    if (allUnchecked) {
                      scope[treeId].uncheckBox(node);
                      //if the unchecked node isn't at the root, repeat
                      var isRoot = false;
                      for (var i = 0; i < scope[treeModel].length; i++) {
                        if (node === scope[treeModel][i]) {
                          isRoot = true;
                          break;
                        }
                      }
                      if (!isRoot) {
                        for (var k = 0; k < scope[treeModel].length; k++) {
                          scope[treeId].uncheckParent(scope[treeModel][k], node);
                        }
                      }
                    } else {
                      scope[treeId].midcheckBox(node);
                      //if the unchecked node isn't at the root, repeat
                      isRoot = false;
                      for (var i = 0; i < scope[treeModel].length; i++) {
                        if (node === scope[treeModel][i]) {
                          isRoot = true;
                          break;
                        }
                      }
                      if (!isRoot) {
                        for (var k = 0; k < scope[treeModel].length; k++) {
                          scope[treeId].uncheckParent(scope[treeModel][k], node);
                        }
                      }
                    }  //if child isn't found then proceed a level deeper
                  } else {
                    if (node[nodeChildren]) {
                      for (var i = 0; i < node[nodeChildren].length; i++) {
                        scope[treeId].uncheckParent(node[nodeChildren][i], nodeChild);
                      }
                    }
                  }
                };
                //goes through each child of the root
                for (var j = 0; j < scope[treeModel].length; j++) {
                  scope[treeId].uncheckParent(scope[treeModel][j], selectedNode);
                }
              }
              if (angular.isDefined(scope.setCheckbox)) {
                scope.setCheckbox(scope.tempCheckedOptions);
              }
              scope.tempCheckedOptions = [];
            };
          }
          //Rendering template.
          element.html('').append($compile(template)(scope));  //scope.nodeLabels = angular.element(element).find('.nodeLabel');
        }
      }
    };
  }
]);
/*jshint funcscope:false*/
/*jshint shadow:false*/
'use strict';
angular.module('ark-components').controller('dropdownTreeCtrl', [
  '$scope',
  '$log',
  'ArkNestedTreeService',
  function ($scope, $log, ArkNestedTreeService) {
    $scope.filterData = [];
    $scope.populateFilter = function (response) {
      if (response && response.items) {
        $scope.filterData = response.items;
      } else if (response && !response.items) {
        $scope.filterData = response;
      }
      for (var j = 0; j < $scope.filterData.length; j++) {
        ArkNestedTreeService.augmentNode($scope.filterData[j], $scope.filterData);
      }  // $scope.nodeList = tempList;
         // tempList = [];
    };
    $scope.$watch('model', function () {
      if ($scope.model) {
        $scope.populateFilter($scope.model);
      }
    });  // var tempList = [];
         // var parentId;
         // $scope.emptyList = [];
         // var arrayContains = function(arr, itemToFind) {
         //     var found = false;
         //     angular.forEach(arr, function(item) {
         //         if (item === itemToFind) {
         //             found = true;
         //         }
         //     });
         //     return found;
         // };
  }
]);
'use strict';
/*jshint expr:true */
angular.module('ark-components').provider('$selectTooltip', function () {
  var defaults = this.defaults = {
      animation: 'am-fade',
      prefixClass: 'tooltip',
      prefixEvent: 'tooltip',
      container: false,
      target: false,
      placement: 'top',
      template: 'ark-select/tooltip.tpl.html',
      contentTemplate: false,
      trigger: 'hover focus',
      keyboard: false,
      html: false,
      show: false,
      title: '',
      type: '',
      delay: 0
    };
  this.$get = [
    '$window',
    '$rootScope',
    '$compile',
    '$q',
    '$templateCache',
    '$http',
    '$animate',
    'dimensions',
    '$$rAF',
    function ($window, $rootScope, $compile, $q, $templateCache, $http, $animate, dimensions, $$rAF) {
      var trim = String.prototype.trim;
      var isTouch = 'createTouch' in $window.document;
      var htmlReplaceRegExp = /ng-bind="/gi;
      function TooltipFactory(element, config) {
        var $selectTooltip = {};
        // Common vars
        var nodeName = element[0].nodeName.toLowerCase();
        var options = $selectTooltip.$options = angular.extend({}, defaults, config);
        $selectTooltip.$promise = fetchTemplate(options.template);
        var scope = $selectTooltip.$scope = options.scope && options.scope.$new() || $rootScope.$new();
        if (options.delay && angular.isString(options.delay)) {
          options.delay = parseFloat(options.delay);
        }
        // Support scope as string options
        if (options.title) {
          $selectTooltip.$scope.title = options.title;
        }
        // Provide scope helpers
        scope.$hide = function () {
          scope.$$postDigest(function () {
            $selectTooltip.hide();
          });
        };
        scope.$show = function () {
          scope.$$postDigest(function () {
            $selectTooltip.show();
          });
        };
        scope.$toggle = function () {
          scope.$$postDigest(function () {
            $selectTooltip.toggle();
          });
        };
        $selectTooltip.$isShown = scope.$isShown = false;
        // Private vars
        var timeout, hoverState;
        // Support contentTemplate option
        if (options.contentTemplate) {
          $selectTooltip.$promise = $selectTooltip.$promise.then(function (template) {
            var templateEl = angular.element(template);
            return fetchTemplate(options.contentTemplate).then(function (contentTemplate) {
              var contentEl = findElement('[ng-bind="content"]', templateEl[0]);
              if (!contentEl.length) {
                contentEl = findElement('[ng-bind="title"]', templateEl[0]);
              }
              contentEl.removeAttr('ng-bind').html(contentTemplate);
              return templateEl[0].outerHTML;
            });
          });
        }
        // Fetch, compile then initialize tooltip
        var tipLinker, tipElement, tipTemplate, tipContainer;
        $selectTooltip.$promise.then(function (template) {
          if (angular.isObject(template)) {
            template = template.data;
          }
          if (options.html) {
            template = template.replace(htmlReplaceRegExp, 'ng-bind-html="');
          }
          template = trim.apply(template);
          tipTemplate = template;
          tipLinker = $compile(template);
          $selectTooltip.init();
        });
        $selectTooltip.init = function () {
          // Options: delay
          if (options.delay && angular.isNumber(options.delay)) {
            options.delay = {
              show: options.delay,
              hide: options.delay
            };
          }
          // Replace trigger on touch devices ?
          // if(isTouch && options.trigger === defaults.trigger) {
          //   options.trigger.replace(/hover/g, 'click');
          // }
          // Options : container
          if (options.container === 'self') {
            tipContainer = element;
          } else if (options.container) {
            tipContainer = findElement(options.container);
          }
          // Options: trigger
          var triggers = options.trigger.split(' ');
          angular.forEach(triggers, function (trigger) {
            if (trigger === 'click') {
              element.on('click', $selectTooltip.toggle);
            } else if (trigger !== 'manual') {
              element.on(trigger === 'hover' ? 'mouseenter' : 'focus', $selectTooltip.enter);
              element.on(trigger === 'hover' ? 'mouseleave' : 'blur', $selectTooltip.leave);
              nodeName === 'button' && trigger !== 'hover' && element.on(isTouch ? 'touchstart' : 'mousedown', $selectTooltip.$onFocusElementMouseDown);
            }
          });
          // Options: target
          if (options.target) {
            options.target = angular.isElement(options.target) ? options.target : findElement(options.target)[0];
          }
          // Options: show
          if (options.show) {
            scope.$$postDigest(function () {
              options.trigger === 'focus' ? element[0].focus() : $selectTooltip.show();
            });
          }
        };
        $selectTooltip.destroy = function () {
          // Unbind events
          var triggers = options.trigger.split(' ');
          for (var i = triggers.length; i--;) {
            var trigger = triggers[i];
            if (trigger === 'click') {
              element.off('click', $selectTooltip.toggle);
            } else if (trigger !== 'manual') {
              element.off(trigger === 'hover' ? 'mouseenter' : 'focus', $selectTooltip.enter);
              element.off(trigger === 'hover' ? 'mouseleave' : 'blur', $selectTooltip.leave);
              nodeName === 'button' && trigger !== 'hover' && element.off(isTouch ? 'touchstart' : 'mousedown', $selectTooltip.$onFocusElementMouseDown);
            }
          }
          // Remove element
          if (tipElement) {
            tipElement.remove();
            tipElement = null;
          }
          // Cancel pending callbacks
          clearTimeout(timeout);
          // Destroy scope
          scope.$destroy();
        };
        $selectTooltip.enter = function () {
          clearTimeout(timeout);
          hoverState = 'in';
          if (!options.delay || !options.delay.show) {
            return $selectTooltip.show();
          }
          timeout = setTimeout(function () {
            if (hoverState === 'in') {
              $selectTooltip.show();
            }
          }, options.delay.show);
        };
        $selectTooltip.show = function () {
          scope.$emit(options.prefixEvent + '.show.before', $selectTooltip);
          var parent = options.container ? tipContainer : null;
          var after = options.container ? null : element;
          // Hide any existing tipElement
          if (tipElement) {
            tipElement.remove();
          }
          // Fetch a cloned element linked from template
          tipElement = $selectTooltip.$element = tipLinker(scope, function (clonedElement, scope) {
          });
          // jshint ignore:line
          // Set the initial positioning.
          tipElement.css({
            top: '0px',
            left: '0px',
            display: 'block'
          }).addClass(options.placement);
          // Options: animation
          if (options.animation) {
            tipElement.addClass(options.animation);
          }
          // Options: type
          if (options.type) {
            tipElement.addClass(options.prefixClass + '-' + options.type);
          }
          $animate.enter(tipElement, parent, after, function () {
            scope.$emit(options.prefixEvent + '.show', $selectTooltip);
          });
          $selectTooltip.$isShown = scope.$isShown = true;
          scope.$$phase || scope.$root && scope.$root.$$phase || scope.$digest();
          $$rAF($selectTooltip.$applyPlacement);
          // var a = bodyEl.offsetWidth + 1; ?
          // Bind events
          if (options.keyboard) {
            if (options.trigger !== 'focus') {
              $selectTooltip.focus();
              tipElement.on('keyup', $selectTooltip.$onKeyUp);
            } else {
              element.on('keyup', $selectTooltip.$onFocusKeyUp);
            }
          }
        };
        $selectTooltip.leave = function () {
          clearTimeout(timeout);
          hoverState = 'out';
          if (!options.delay || !options.delay.hide) {
            return $selectTooltip.hide();
          }
          timeout = setTimeout(function () {
            if (hoverState === 'out') {
              $selectTooltip.hide();
            }
          }, options.delay.hide);
        };
        $selectTooltip.hide = function (blur) {
          if (!$selectTooltip.$isShown) {
            return;
          }
          scope.$emit(options.prefixEvent + '.hide.before', $selectTooltip);
          $animate.leave(tipElement, function () {
            scope.$emit(options.prefixEvent + '.hide', $selectTooltip);
          });
          $selectTooltip.$isShown = scope.$isShown = false;
          scope.$$phase || scope.$root && scope.$root.$$phase || scope.$digest();
          // Unbind events
          if (options.keyboard && tipElement !== null) {
            tipElement.off('keyup', $selectTooltip.$onKeyUp);
          }
          // Allow to blur the input when hidden, like when pressing enter key
          if (blur && options.trigger === 'focus') {
            return element[0].blur();
          }
        };
        $selectTooltip.toggle = function () {
          $selectTooltip.$isShown ? $selectTooltip.leave() : $selectTooltip.enter();
        };
        $selectTooltip.focus = function () {
          tipElement[0].focus();
        };
        // Protected methods
        $selectTooltip.$applyPlacement = function () {
          if (!tipElement) {
            return;
          }
          // Get the position of the tooltip element.
          var elementPosition = getPosition();
          // Get the height and width of the tooltip so we can center it.
          var tipWidth = tipElement.prop('offsetWidth'), tipHeight = tipElement.prop('offsetHeight');
          // Get the tooltip's top and left coordinates to center it with this directive.
          var tipPosition = getCalculatedOffset(options.placement, elementPosition, tipWidth, tipHeight);
          // Now set the calculated positioning.
          tipPosition.top += 'px';
          tipPosition.left += 'px';
          tipElement.css(tipPosition);
          tipElement.children().css(tipPosition);
        };
        $selectTooltip.$onKeyUp = function (evt) {
          evt.which === 27 && $selectTooltip.hide();
        };
        $selectTooltip.$onFocusKeyUp = function (evt) {
          evt.which === 27 && element[0].blur();
        };
        $selectTooltip.$onFocusElementMouseDown = function (evt) {
          evt.preventDefault();
          evt.stopPropagation();
          // Some browsers do not auto-focus buttons (eg. Safari)
          $selectTooltip.$isShown ? element[0].blur() : element[0].focus();
        };
        // Private methods
        function getPosition() {
          if (options.container === 'body') {
            return dimensions.offset(options.target || element[0]);
          } else {
            return dimensions.position(options.target || element[0]);
          }
        }
        function getCalculatedOffset(placement, position, actualWidth, actualHeight) {
          var offset;
          var split = placement.split('-');
          switch (split[0]) {
          case 'right':
            offset = {
              top: position.top + position.height / 2 - actualHeight / 2,
              left: position.left + position.width
            };
            break;
          case 'bottom':
            offset = {
              top: position.top + position.height,
              left: position.left + position.width / 2 - actualWidth / 2
            };
            break;
          case 'left':
            offset = {
              top: position.top + position.height / 2 - actualHeight / 2,
              left: position.left - actualWidth
            };
            break;
          default:
            offset = {
              top: position.top - actualHeight,
              left: position.left + position.width / 2 - actualWidth / 2
            };
            break;
          }
          if (!split[1]) {
            return offset;
          }
          // Add support for corners @todo css
          if (split[0] === 'top' || split[0] === 'bottom') {
            switch (split[1]) {
            case 'left':
              offset.left = position.left;
              break;
            case 'right':
              offset.left = position.left + position.width - actualWidth;
            }
          } else if (split[0] === 'left' || split[0] === 'right') {
            switch (split[1]) {
            case 'top':
              offset.top = position.top - actualHeight;
              break;
            case 'bottom':
              offset.top = position.top + position.height;
            }
          }
          return offset;
        }
        return $selectTooltip;
      }
      // Helper functions
      function findElement(query, element) {
        return angular.element((element || document).querySelectorAll(query));
      }
      function fetchTemplate(template) {
        return $q.when($templateCache.get(template) || $http.get(template)).then(function (res) {
          if (angular.isObject(res)) {
            $templateCache.put(template, res.data);
            return res.data;
          }
          return res;
        });
      }
      return TooltipFactory;
    }
  ];
}).directive('bsTooltip', [
  '$window',
  '$location',
  '$sce',
  '$selectTooltip',
  '$$rAF',
  function ($window, $location, $sce, $selectTooltip, $$rAF) {
    return {
      restrict: 'EAC',
      scope: true,
      link: function postLink(scope, element, attr) {
        // Directive options
        var options = { scope: scope };
        angular.forEach([
          'template',
          'contentTemplate',
          'placement',
          'container',
          'target',
          'delay',
          'trigger',
          'keyboard',
          'html',
          'animation',
          'type'
        ], function (key) {
          if (angular.isDefined(attr[key])) {
            options[key] = attr[key];
          }
        });
        // Observe scope attributes for change
        angular.forEach(['title'], function (key) {
          attr[key] && attr.$observe(key, function (newValue, oldValue) {
            scope[key] = $sce.trustAsHtml(newValue);
            angular.isDefined(oldValue) && $$rAF(function () {
              tooltip && tooltip.$applyPlacement();
            });
          });
        });
        // Support scope as an object
        attr.bsTooltip && scope.$watch(attr.bsTooltip, function (newValue, oldValue) {
          if (angular.isObject(newValue)) {
            angular.extend(scope, newValue);
          } else {
            scope.title = newValue;
          }
          angular.isDefined(oldValue) && $$rAF(function () {
            tooltip && tooltip.$applyPlacement();
          });
        }, true);
        // Initialize popover
        var tooltip = $selectTooltip(element, options);
        // Garbage collection
        scope.$on('$destroy', function () {
          tooltip.destroy();
          options = null;
          tooltip = null;
        });
      }
    };
  }
]).provider('$select', function () {
  var defaults = this.defaults = {
      animation: 'am-fade',
      prefixClass: 'select',
      placement: 'bottom-left',
      template: 'ark-select/ark-select.html',
      trigger: 'focus',
      container: false,
      keyboard: true,
      html: false,
      delay: 0,
      multiple: false,
      sort: false,
      caretHtml: '&nbsp;<span class="fonticon icon-dropdown-arrow"></span>',
      placeholder: 'Choose among the following...',
      maxLength: 2,
      maxLengthHtml: 'selected',
      iconCheckmark: 'fonticon fonticon-ok icon-tick check-mark',
      parentId: ''
    };
  this.$get = [
    '$window',
    '$document',
    '$rootScope',
    '$selectTooltip',
    function ($window, $document, $rootScope, $selectTooltip) {
      // var bodyEl = angular.element($window.document.body);
      var isTouch = 'createTouch' in $window.document;
      function SelectFactory(element, controller, config) {
        var $select = {};
        // Common vars
        var options = angular.extend({}, defaults, config);
        $select = $selectTooltip(element, options);
        var scope = $select.$scope;
        scope.$matches = [];
        scope.$activeIndex = 0;
        scope.$isMultiple = options.multiple;
        scope.$iconCheckmark = options.iconCheckmark;
        scope.$parentId = options.parentId;
        scope.$activate = function (index) {
          scope.$$postDigest(function () {
            $select.activate(index);
          });
        };
        scope.$select = function (index) {
          scope.$$postDigest(function () {
            $select.select(index);
          });
        };
        scope.$isVisible = function () {
          return $select.$isVisible();
        };
        scope.$isActive = function (index) {
          return $select.$isActive(index);
        };
        // Public methods
        $select.update = function (matches) {
          scope.$matches = matches;
          $select.$updateActiveIndex();
        };
        $select.activate = function (index) {
          if (options.multiple) {
            scope.$activeIndex.sort();
            $select.$isActive(index) ? scope.$activeIndex.splice(scope.$activeIndex.indexOf(index), 1) : scope.$activeIndex.push(index);
            if (options.sort) {
              scope.$activeIndex.sort();
            }
          } else {
            scope.$activeIndex = index;
          }
          return scope.$activeIndex;
        };
        $select.select = function (index) {
          var value = scope.$matches[index].value;
          scope.$apply(function () {
            $select.activate(index);
            if (options.multiple) {
              controller.$setViewValue(scope.$activeIndex.map(function (index) {
                return scope.$matches[index].value;
              }));  /*element[0].getElementsByTagName('span')[0].innerHTML = (scope.$activeIndex.map(function(index) {
                return scope.$matches[index].value;
              }));*/
            } else {
              controller.$setViewValue(value);
              /*element[0].getElementsByTagName('span')[0].innerHTML = value;*/
              $select.hide();
            }
          });
          // Emit event
          scope.$emit('$select.select', value, index);
        };
        // Protected methods
        $select.$updateActiveIndex = function () {
          if (controller.$modelValue && scope.$matches.length) {
            if (options.multiple && angular.isArray(controller.$modelValue)) {
              var isWorking = true;
              for (var i = 0; i < controller.$modelValue.length; i++) {
                isWorking = typeof $select.$getIndex(controller.$modelValue[i]) !== 'undefined';
                if (!isWorking) {
                  break;
                }
              }
              scope.$activeIndex = isWorking ? controller.$modelValue.map(function (value) {
                return $select.$getIndex(value);
              }) : [];
            } else {
              scope.$activeIndex = $select.$getIndex(controller.$modelValue);
            }
          } else if (scope.$activeIndex >= scope.$matches.length) {
            scope.$activeIndex = options.multiple ? [] : 0;
          }
        };
        $select.$isVisible = function () {
          if (!options.minLength || !controller) {
            return scope.$matches.length;
          }
          // minLength support
          return scope.$matches.length && controller.$viewValue.length >= options.minLength;
        };
        $select.$isActive = function (index) {
          if (options.multiple) {
            return scope.$activeIndex.indexOf(index) !== -1;
          } else {
            return scope.$activeIndex === index;
          }
        };
        $select.$getIndex = function (value) {
          var l = scope.$matches.length, i = l;
          if (!l) {
            return;
          }
          for (i = l; i--;) {
            if (scope.$matches[i].value === value) {
              break;
            }
          }
          if (i < 0) {
            return;
          }
          return i;
        };
        $select.$onMouseDown = function (evt) {
          // Prevent blur on mousedown on .dropdown-menu
          evt.preventDefault();
          evt.stopPropagation();
          // Emulate click for mobile devices
          if (isTouch) {
            var targetEl = angular.element(evt.target);
            targetEl.triggerHandler('click');
          }
        };
        $select.$onKeyDown = function (evt) {
          if (!/(9|13|38|40)/.test(evt.keyCode)) {
            return;
          }
          evt.preventDefault();
          evt.stopPropagation();
          // Select with enter
          if (!options.multiple && (evt.keyCode === 13 || evt.keyCode === 9)) {
            return $select.select(scope.$activeIndex);
          }
          // Navigate with keyboard
          if (evt.keyCode === 38 && scope.$activeIndex > 0) {
            scope.$activeIndex--;
          } else if (evt.keyCode === 40 && scope.$activeIndex < scope.$matches.length - 1) {
            scope.$activeIndex++;
          } else if (angular.isUndefined(scope.$activeIndex)) {
            scope.$activeIndex = 0;
          }
          scope.$digest();
        };
        $select.$updateParentId = function (parentId) {
          scope.$parentId = parentId;
        };
        // Overrides
        var _show = $select.show;
        $select.show = function () {
          _show();
          if (options.multiple) {
            $select.$element.addClass('select-multiple');
          }
          setTimeout(function () {
            $select.$element.on(isTouch ? 'touchstart' : 'mousedown', $select.$onMouseDown);
            if (options.keyboard) {
              element.on('keydown', $select.$onKeyDown);
            }
          });
        };
        var _hide = $select.hide;
        $select.hide = function () {
          $select.$element.off(isTouch ? 'touchstart' : 'mousedown', $select.$onMouseDown);
          if (options.keyboard) {
            element.off('keydown', $select.$onKeyDown);
          }
          _hide(true);
        };
        return $select;
      }
      SelectFactory.defaults = defaults;
      return SelectFactory;
    }
  ];
}).directive('arkSelect', [
  '$window',
  '$parse',
  '$q',
  '$select',
  '$parseOptions',
  function ($window, $parse, $q, $select, $parseOptions) {
    var defaults = $select.defaults;
    return {
      restrict: 'EAC',
      require: 'ngModel',
      link: function postLink(scope, element, attr, controller) {
        // Directive options
        var options = { scope: scope };
        angular.forEach([
          'placement',
          'container',
          'delay',
          'trigger',
          'keyboard',
          'html',
          'animation',
          'template',
          'placeholder',
          'multiple',
          'maxLength',
          'maxLengthHtml'
        ], function (key) {
          if (angular.isDefined(attr[key])) {
            options[key] = attr[key];
          }
        });
        // Add support for select markup
        if (element[0].nodeName.toLowerCase() === 'select') {
          var inputEl = element;
          inputEl.css('display', 'none');
          //element = angular.element('<button type="button" class="btn btn-default"></button>');
          element = angular.element('<div class="btn-group bootstrap-select"><button type="button" class="btn btn-default dropdown-toggle selectpicker btn-default"></button></div>');
          inputEl.after(element);
        }
        scope.$watch('element.context.id', function () {
          select.$updateParentId(element.context.id);
        });
        // Build proper ngOptions
        var parsedOptions = $parseOptions(attr.ngOptions);
        // Initialize select
        var select = $select(element, controller, options);
        // Watch ngOptions values before filtering for changes
        var watchedOptions = parsedOptions.$match[7].trim();
        scope.$watch(watchedOptions, function () {
          // console.warn('scope.$watch(%s)', watchedOptions, newValue, oldValue);
          parsedOptions.valuesFn(scope, controller).then(function (values) {
            select.update(values);
            controller.$render();
          });
        }, true);
        // Watch model for changes
        scope.$watch(attr.ngModel, function () {
          // console.warn('scope.$watch(%s)', attr.ngModel, newValue, oldValue);
          select.$updateActiveIndex();
          controller.$render();
        }, true);
        // Model rendering in view
        controller.$render = function () {
          // console.warn('$render', element.attr('ng-model'), 'controller.$modelValue', typeof controller.$modelValue, controller.$modelValue, 'controller.$viewValue', typeof controller.$viewValue, controller.$viewValue);
          var selected, index;
          if (options.multiple && angular.isArray(controller.$modelValue)) {
            selected = controller.$modelValue.map(function (value) {
              index = select.$getIndex(value);
              return angular.isDefined(index) ? select.$scope.$matches[index].label : options.placeholder;
            }).filter(angular.isDefined);
            if (selected.length > (options.maxLength || defaults.maxLength)) {
              selected = selected.length + ' ' + (options.maxLengthHtml || defaults.maxLengthHtml);
            } else {
              selected = selected.join(', ');
            }
          } else {
            index = select.$getIndex(controller.$modelValue);
            selected = angular.isDefined(index) ? select.$scope.$matches[index].label : false;
          }
          if (attr.multiple) {
            element.html('<span class="filter-option">' + (selected ? selected : attr.placeholder || defaults.placeholder) + '</span>' + '<span class="fonticon icon-pencil"></span>');
          } else {
            element.html('<span class="filter-option">' + (selected ? selected : attr.placeholder || defaults.placeholder) + '</span>' + defaults.caretHtml);
          }
        };
        // Garbage collection
        scope.$on('$destroy', function () {
          select.destroy();
          options = null;
          select = null;
        });
      }
    };
  }
]);
/*jshint expr:false */
'use strict';
/*jshint expr:true */
angular.version.minor < 3 && angular.version.dot < 14 && angular.module('ng').factory('$$rAF', [
  '$window',
  '$timeout',
  function ($window, $timeout) {
    var requestAnimationFrame = $window.requestAnimationFrame || $window.webkitRequestAnimationFrame || $window.mozRequestAnimationFrame;
    var cancelAnimationFrame = $window.cancelAnimationFrame || $window.webkitCancelAnimationFrame || $window.mozCancelAnimationFrame || $window.webkitCancelRequestAnimationFrame;
    var rafSupported = !!requestAnimationFrame;
    var raf = rafSupported ? function (fn) {
        var id = requestAnimationFrame(fn);
        return function () {
          cancelAnimationFrame(id);
        };
      } : function (fn) {
        var timer = $timeout(fn, 16.66, false);
        // 1000 / 60 = 16.666
        return function () {
          $timeout.cancel(timer);
        };
      };
    raf.supported = rafSupported;
    return raf;
  }
]);
angular.module('ark-components').factory('dimensions', function () {
  // var jqLite = angular.element;
  var fn = {};
  /**
     * Test the element nodeName
     * @param element
     * @param name
     */
  var nodeName = fn.nodeName = function (element, name) {
      return element.nodeName && element.nodeName.toLowerCase() === name.toLowerCase();
    };
  /**
     * Returns the element computed style
     * @param element
     * @param prop
     * @param extra
     */
  fn.css = function (element, prop, extra) {
    var value;
    if (element.currentStyle) {
      //IE
      value = element.currentStyle[prop];
    } else if (window.getComputedStyle) {
      value = window.getComputedStyle(element)[prop];
    } else {
      value = element.style[prop];
    }
    return extra === true ? parseFloat(value) || 0 : value;
  };
  /**
     * Provides read-only equivalent of jQuery's offset function:
     * @required-by bootstrap-tooltip, bootstrap-affix
     * @url http://api.jquery.com/offset/
     * @param element
     */
  fn.offset = function (element) {
    var boxRect = element.getBoundingClientRect();
    var docElement = element.ownerDocument;
    return {
      width: boxRect.width || element.offsetWidth,
      height: boxRect.height || element.offsetHeight,
      top: boxRect.top + (window.pageYOffset || docElement.documentElement.scrollTop) - (docElement.documentElement.clientTop || 0),
      left: boxRect.left + (window.pageXOffset || docElement.documentElement.scrollLeft) - (docElement.documentElement.clientLeft || 0)
    };
  };
  /**
     * Provides read-only equivalent of jQuery's position function
     * @required-by bootstrap-tooltip, bootstrap-affix
     * @url http://api.jquery.com/offset/
     * @param element
     */
  fn.position = function (element) {
    var offsetParentRect = {
        top: 0,
        left: 0
      }, offsetParentElement, offset;
    // Fixed elements are offset from window (parentOffset = {top:0, left: 0}, because it is it's only offset parent
    if (fn.css(element, 'position') === 'fixed') {
      // We assume that getBoundingClientRect is available when computed position is fixed
      offset = element.getBoundingClientRect();
    } else {
      // Get *real* offsetParentElement
      offsetParentElement = offsetParent(element);
      offset = fn.offset(element);
      // Get correct offsets
      offset = fn.offset(element);
      if (!nodeName(offsetParentElement, 'html')) {
        offsetParentRect = fn.offset(offsetParentElement);
      }
      // Add offsetParent borders
      offsetParentRect.top += fn.css(offsetParentElement, 'borderTopWidth', true);
      offsetParentRect.left += fn.css(offsetParentElement, 'borderLeftWidth', true);
    }
    // Subtract parent offsets and element margins
    return {
      width: element.offsetWidth,
      height: element.offsetHeight,
      top: offset.top - offsetParentRect.top - fn.css(element, 'marginTop', true),
      left: offset.left - offsetParentRect.left - fn.css(element, 'marginLeft', true)
    };
  };
  /**
     * Returns the closest, non-statically positioned offsetParent of a given element
     * @required-by fn.position
     * @param element
     */
  var offsetParent = function offsetParentElement(element) {
    var docElement = element.ownerDocument;
    var offsetParent = element.offsetParent || docElement;
    if (nodeName(offsetParent, '#document')) {
      return docElement.documentElement;
    }
    while (offsetParent && !nodeName(offsetParent, 'html') && fn.css(offsetParent, 'position') === 'static') {
      offsetParent = offsetParent.offsetParent;
    }
    return offsetParent || docElement.documentElement;
  };
  /**
     * Provides equivalent of jQuery's height function
     * @required-by bootstrap-affix
     * @url http://api.jquery.com/height/
     * @param element
     * @param outer
     */
  fn.height = function (element, outer) {
    var value = element.offsetHeight;
    if (outer) {
      value += fn.css(element, 'marginTop', true) + fn.css(element, 'marginBottom', true);
    } else {
      value -= fn.css(element, 'paddingTop', true) + fn.css(element, 'paddingBottom', true) + fn.css(element, 'borderTopWidth', true) + fn.css(element, 'borderBottomWidth', true);
    }
    return value;
  };
  /**
     * Provides equivalent of jQuery's width function
     * @required-by bootstrap-affix
     * @url http://api.jquery.com/width/
     * @param element
     * @param outer
     */
  fn.width = function (element, outer) {
    var value = element.offsetWidth;
    if (outer) {
      value += fn.css(element, 'marginLeft', true) + fn.css(element, 'marginRight', true);
    } else {
      value -= fn.css(element, 'paddingLeft', true) + fn.css(element, 'paddingRight', true) + fn.css(element, 'borderLeftWidth', true) + fn.css(element, 'borderRightWidth', true);
    }
    return value;
  };
  return fn;
}).provider('$parseOptions', function () {
  var defaults = this.defaults = { regexp: /^\s*(.*?)(?:\s+as\s+(.*?))?(?:\s+group\s+by\s+(.*))?\s+for\s+(?:([\$\w][\$\w]*)|(?:\(\s*([\$\w][\$\w]*)\s*,\s*([\$\w][\$\w]*)\s*\)))\s+in\s+(.*?)(?:\s+track\s+by\s+(.*?))?$/ };
  this.$get = [
    '$parse',
    '$q',
    function ($parse, $q) {
      function ParseOptionsFactory(attr, config) {
        var $parseOptions = {};
        // Common vars
        var options = angular.extend({}, defaults, config);
        $parseOptions.$values = [];
        // Private vars
        var match, displayFn, valueName, keyName, groupByFn, valueFn, valuesFn;
        $parseOptions.init = function () {
          $parseOptions.$match = match = attr.match(options.regexp);
          displayFn = $parse(match[2] || match[1]), valueName = match[4] || match[6], keyName = match[5], groupByFn = $parse(match[3] || ''), valueFn = $parse(match[2] ? match[1] : valueName), valuesFn = $parse(match[7]);
        };
        $parseOptions.valuesFn = function (scope, controller) {
          return $q.when(valuesFn(scope, controller)).then(function (values) {
            $parseOptions.$values = values ? parseValues(values, scope) : {};
            return $parseOptions.$values;
          });
        };
        // Private functions
        function parseValues(values, scope) {
          return values.map(function (match, index) {
            var locals = {}, label, value;
            locals[valueName] = match;
            label = displayFn(scope, locals);
            value = valueFn(scope, locals) || index;
            return {
              label: label,
              value: value
            };
          });
        }
        $parseOptions.init();
        return $parseOptions;
      }
      return ParseOptionsFactory;
    }
  ];
});
/*jshint expr:false */
'use strict';
angular.module('ark-components').controller('arkSideTabsCtrl', [
  '$scope',
  function ($scope) {
    // sets initial selected template
    $scope.selectedItemIndex = $scope.activeTab && $scope.tabsList[$scope.activeTab] ? $scope.activeTab : 0;
    $scope.activeTab = $scope.selectedItemIndex;
    $scope.selectedTemplate = $scope.tabsList[$scope.selectedItemIndex].templateUrl;
    // watches for changes to activeTab and sets selectedTemplate
    $scope.$watch('activeTab', function () {
      $scope.selectedItemIndex = $scope.tabsList[$scope.activeTab] ? $scope.activeTab : $scope.selectedItemIndex;
      $scope.activeTab = $scope.selectedItemIndex;
      $scope.selectedTemplate = $scope.tabsList[$scope.selectedItemIndex].templateUrl;
    });
    $scope.setActive = function (indexNum) {
      $scope.selectedItemIndex = indexNum;
      $scope.activeTab = indexNum;
      $scope.selectedTemplate = $scope.tabsList[indexNum].templateUrl;
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkSideTabs', [
  '$timeout',
  '$templateCache',
  function ($timeout, $templateCache) {
    return {
      restrict: 'E',
      scope: {
        tabsList: '=',
        switchReload: '@',
        parentData: '=parentData',
        activeTab: '=?activeTab'
      },
      controller: 'arkSideTabsCtrl',
      templateUrl: 'ark-side-tabs/ark-side-tabs.html',
      link: function ($scope) {
        $scope.$watch('switchReload', function (newValue) {
          $scope.reload = !angular.isDefined(newValue) ? false : $scope.$eval($scope.switchReload);
        });
        $scope.$watch('tabsList', function (newValue) {
          var newTabs = [];
          var index = 0;
          newValue.forEach(function (n) {
            if (angular.isDefined(n.template)) {
              var newUrl = 'ark-side-tab-template' + index++;
              $templateCache.put(newUrl, n.template);
              newTabs.push({
                title: n.title,
                icon: n.icon,
                templateUrl: newUrl
              });
            } else {
              newTabs.push(n);
            }
          });
          $scope.tabs = newTabs;
          $scope.tabsList = newTabs;
        }, true);
      }
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkSidebar', function () {
  return {
    restrict: 'AE',
    scope: {
      showSidebar: '=?',
      showShadow: '=?',
      template: '='
    },
    templateUrl: 'ark-sidebar/ark-sidebar.html',
    link: function (scope) {
      if (scope.showShadow === undefined) {
        scope.showShadow = true;
      }
      if (scope.showSidebar === undefined) {
        scope.showSidebar = true;
      }
    }
  };
});
'use strict';
angular.module('ark-components').controller('arkSliderCtrl', [
  '$scope',
  function ($scope) {
    $scope.isActive = false;
    $scope.setActive = function () {
      $scope.isActive = !$scope.isActive;
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkSlider', function () {
  return {
    restrict: 'E',
    scope: {
      tooltip: '@',
      percentage: '@'
    },
    transclude: true,
    controller: 'arkSliderCtrl',
    templateUrl: 'ark-slider/ark-slider.html',
    link: function (scope, element) {
      var input = element.find('input');
      var ngModelCtrl = angular.element(input).controller('ngModel');
      scope.useTooltip = scope.$eval(scope.tooltip) || false;
      scope.showPercentage = scope.$eval(scope.percentage) || false;
      var inputWidth = scope.useTooltip ? 100 : 75;
      angular.element(input).css('width', inputWidth + '%');
      if (!input || !ngModelCtrl || input[0].type !== 'range') {
        return;
      }
      scope.$watch(function () {
        scope.inputValue = ngModelCtrl.$viewValue;
        return ngModelCtrl.$viewValue;
      }, function (newValue) {
        if (typeof newValue !== 'undefined') {
          var min = parseInt(input[0].min !== '' ? input[0].min : 0);
          var max = parseInt(input[0].max !== '' ? input[0].max : 100);
          var cur = parseInt(newValue);
          element.find('.slider-fill').css('width', (cur - min) / (max - min) * inputWidth + '%');
        }
      });
    }
  };
});
'use strict';
angular.module('ark-components').controller('arkTagsCtrl', [
  '$scope',
  '$timeout',
  function ($scope, $timeout) {
    var controller = this;
    this.restartAnimation = function (index) {
      var currTag = angular.element($scope.element).find('span.tag-label').eq(index).parent();
      //sanity check
      if (currTag.length) {
        currTag.removeClass('animated pulse');
        $timeout(function () {
          currTag.addClass('animated pulse');
        });
      }
    };
    $scope.addTag = function () {
      if ($scope.inputTag) {
        for (var i = 0; i < $scope.tagList.length; i++) {
          if ($scope.tagList[i] === $scope.inputTag) {
            $scope.inputTag = '';
            controller.restartAnimation(i);
            return;
          }
        }
        $scope.tagList.push($scope.inputTag);
        $scope.inputTag = '';
        if ($scope.sort) {
          $scope.tagList.sort(function (a, b) {
            if (a.toLowerCase() < b.toLowerCase()) {
              return -1;
            } else if (a.toLowerCase() > b.toLowerCase()) {
              return 1;
            }
            //sanity check
            return 0;
          });
        }
      } else {
        angular.element($scope.element).find('#tagsinput_tag').focus();
      }
    };
    $scope.removeTag = function (tag) {
      var index = $scope.tagList.indexOf(tag);
      $scope.tagList.splice(index, 1);
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkTags', function () {
  return {
    restrict: 'E',
    scope: { tagList: '=tags' },
    templateUrl: 'ark-tags/ark-tags.html',
    controller: 'arkTagsCtrl',
    link: function (scope, element, attr) {
      scope.element = element;
      scope.sort = attr.sort !== undefined ? true : false;
      scope.tagList = scope.tagList || [];
      if (scope.sort && scope.tagList.length) {
        scope.tagList.sort(function (a, b) {
          if (a.toLowerCase() < b.toLowerCase()) {
            return -1;
          } else if (a.toLowerCase() > b.toLowerCase()) {
            return 1;
          }
          //sanity check
          return 0;
        });
      }
      // TODO: Avoid using id (#tagsinput_tag), if multiple ark-tags directives
      // are on the same page, it could case problems
      element.find('#tagsinput_tag').bind('keydown keypress', function (event) {
        if (event.which === 13) {
          scope.$apply(function () {
            scope.addTag();
          });
          event.preventDefault();
        }
      });
    }
  };
});
'use strict';
angular.module('ark-components').controller('arkTimePickerCtrl', [
  '$scope',
  '_',
  function ($scope, _) {
    $scope.hourList = [
      '1',
      '2',
      '3',
      '4',
      '5',
      '6',
      '7',
      '8',
      '9',
      '10',
      '11',
      '12'
    ];
    $scope.minuteList = [
      '00',
      '05',
      '10',
      '15',
      '20',
      '25',
      '30',
      '35',
      '40',
      '45',
      '50',
      '55'
    ];
    $scope.timeZoneList = [
      'GMT-12:00',
      'GMT-11:00',
      'GMT-10:00',
      'GMT-09:00',
      'GMT-08:00',
      'GMT-07:00',
      'GMT-06:00',
      'GMT-05:00',
      'GMT-04:30',
      'GMT-04:00',
      'GMT-03:30',
      'GMT-03:00',
      'GMT-02:00',
      'GMT-01:00',
      'GMT+00:00',
      'GMT+01:00',
      'GMT+02:00',
      'GMT+03:00',
      'GMT+03:30',
      'GMT+04:00',
      'GMT+05:00',
      'GMT+05:30',
      'GMT+05:45',
      'GMT+06:00',
      'GMT+06:30',
      'GMT+07:00',
      'GMT+08:00',
      'GMT+09:00',
      'GMT+09:30',
      'GMT+10:00',
      'GMT+11:00',
      'GMT+12:00',
      'GMT+13:00'
    ];
    $scope.showHourList = false;
    $scope.showMinuteList = false;
    $scope.showTimeZoneList = false;
    var controller = this;
    //Hour Section
    $scope.isInvalidHour = function () {
      return controller.isInvalidHour($scope.hour, $scope.noon);
    };
    controller.isInvalidHour = function (hour, noon) {
      return !hour || isNaN(hour) || hour.indexOf('.') !== -1 || hour.length > 2 || noon === 'AM' && (parseInt(hour) > 12 || parseInt(hour) < 0) || noon === 'PM' && (parseInt(hour) > 12 || parseInt(hour) < 1);
    };
    $scope.validateHour = function () {
      if ($scope.isInvalidHour()) {
        $scope.hour = $scope.prevHour;
      } else {
        $scope.prevHour = $scope.hour;
      }
      $scope.showHourList = false;
    };
    $scope.addHour = function () {
      if ($scope.noon === 'AM') {
        if ($scope.hour === '11') {
          $scope.noon = 'PM';
          $scope.hour = '12';
        } else {
          $scope.hour = parseInt($scope.hour) % 12 + 1 + '';
        }
      } else {
        if ($scope.hour === '11') {
          $scope.noon = 'AM';
        }
        $scope.hour = parseInt($scope.hour) % 12 + 1 + '';
      }
      $scope.prevHour = $scope.hour;
      $scope.prevNoon = $scope.noon;
    };
    $scope.minusHour = function () {
      if ($scope.noon === 'AM') {
        if ($scope.hour === '00' || $scope.hour === '0' || $scope.hour === '12') {
          $scope.noon = 'PM';
          $scope.hour = '11';
        } else {
          $scope.hour = parseInt($scope.hour) - 1 + '';
        }
      } else {
        if ($scope.hour === '12') {
          $scope.noon = 'AM';
        }
        $scope.hour = $scope.hour === '01' || $scope.hour === '1' ? $scope.hour = '12' : parseInt($scope.hour) - 1 + '';
      }
      $scope.prevHour = $scope.hour;
      $scope.prevNoon = $scope.noon;
    };
    // Minute section
    $scope.isInvalidMinute = function () {
      return controller.isInvalidMinute($scope.minute);
    };
    controller.isInvalidMinute = function (minute) {
      return !minute || isNaN(minute) || minute.indexOf('.') !== -1 || minute.length > 2 || parseInt(minute) > 59 || parseInt(minute) < 0;
    };
    $scope.formatNumber = function (input) {
      if (input.length === 1) {
        input = '0' + input;
      }
      return input;
    };
    $scope.addMinute = function () {
      if ($scope.minute === '59') {
        $scope.addHour();
      }
      $scope.minute = $scope.formatNumber((parseInt($scope.minute) + 1) % 60 + '');
      $scope.prevMinute = $scope.minute;
    };
    $scope.minusMinute = function () {
      if ($scope.minute === '0' || $scope.minute === '00') {
        $scope.minusHour();
      }
      $scope.minute = $scope.formatNumber((parseInt($scope.minute) + 59) % 60 + '');
      $scope.prevMinute = $scope.minute;
    };
    $scope.validateMinute = function () {
      if ($scope.isInvalidMinute()) {
        $scope.minute = $scope.prevMinute;
      } else {
        $scope.minute = $scope.formatNumber($scope.minute);
        $scope.prevMinute = $scope.minute;
      }
      $scope.showMinuteList = false;
    };
    // AM/PM section
    $scope.changeNoon = function () {
      if ($scope.noon === 'AM') {
        if ($scope.hour === '0' || $scope.hour === '00') {
          $scope.hour = '12';
          $scope.prevHour = $scope.hour;
        }
        $scope.noon = 'PM';
      } else {
        $scope.noon = 'AM';
      }
      $scope.prevNoon = $scope.noon;
    };
    $scope.validateNoon = function () {
      if ($scope.noon.toLowerCase() === 'am' || $scope.noon.toLowerCase() === 'pm') {
        if ($scope.noon.toLowerCase() === 'pm' && $scope.hour === '0') {
          $scope.hour = '12';
          $scope.prevHour = $scope.hour;
        }
        $scope.noon = $scope.noon.toUpperCase();
        $scope.prevNoon = $scope.noon;
      } else {
        $scope.noon = $scope.prevNoon;
      }
    };
    // returns bool
    controller.isInvalidNoon = function (noon) {
      return noon.toUpperCase() !== 'AM' && noon.toUpperCase() !== 'PM';
    };
    // Time Zone Section
    $scope.isInvalidTimeZone = function () {
      return !_.contains($scope.timeZoneList, $scope.timeZone);
    };
    $scope.validateTimeZone = function () {
      if ($scope.isInvalidTimeZone()) {
        $scope.timeZone = $scope.prevTimeZone;
      } else {
        $scope.prevTimeZone = $scope.timeZone;
      }
      $scope.showTimeZoneList = false;
    };
    $scope.addTimeZone = function () {
      if ($scope.timeZoneIndex > 0) {
        $scope.timeZoneIndex--;
      }
      $scope.timeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      $scope.prevTimeZone = $scope.timeZone;
    };
    $scope.minusTimeZone = function () {
      if ($scope.timeZoneIndex < $scope.timeZoneList.length - 1) {
        $scope.timeZoneIndex++;
      }
      $scope.timeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      $scope.prevTimeZone = $scope.timeZone;
    };
    $scope.showHour = function () {
      $scope.showHourList = true;
    };
    $scope.showMinute = function () {
      $scope.showMinuteList = true;
    };
    $scope.showTimeZone = function () {
      $scope.showTimeZoneList = true;
    };
    $scope.selectHour = function (item) {
      $scope.hour = item;
      $scope.prevHour = item;
    };
    $scope.selectMinute = function (item) {
      $scope.minute = item;
      $scope.prevMinute = item;
    };
    $scope.selectTimeZone = function (item, index) {
      $scope.timeZone = item;
      $scope.prevTimeZone = item;
      $scope.timeZoneIndex = index;
    };
    // returns boolean
    controller.isInvalidFormat = function () {
      if ($scope.time.split('.').length === 3 || $scope.time.split(':').length === 3) {
        // if format is hh.mm.am
        var timeString = $scope.time.split('.');
        if (timeString.length === 1) {
          timeString = $scope.time.split(':');
        }
        if ($scope.timezoneMode) {
          var timezoneString;
          var times = timeString[2].split('-');
          var timezoneRange = '-';
          if (times.length === 1) {
            times = timeString[2].split('+');
            timezoneRange = '+';
          }
          timeString[2] = times[0];
          timezoneString = timezoneRange + times[1];
          $scope.timeZone = 'GMT' + timezoneString;
        }
        if (timeString[0].length === 1) {
          timeString[0] = '0' + timeString[0];
        }
        if (timeString[1].length === 1) {
          timeString[1] = '0' + timeString[1];
        }
        return controller.isInvalidNoon(timeString[2].toUpperCase()) || controller.isInvalidHour(timeString[0], timeString[2].toUpperCase()) || controller.isInvalidMinute(timeString[1]);
      } else {
        // if format does not contain hours, mins, noon
        return true;
      }
    };
    // void
    controller.setDefaultTime = function () {
      // set to default
      $scope.prevHour = '9';
      $scope.hour = '9';
      $scope.prevMinute = '00';
      $scope.minute = '00';
      $scope.prevNoon = 'AM';
      $scope.noon = 'AM';
      $scope.timeZoneIndex = 7;
      $scope.prevTimeZone = $scope.timeZoneList[$scope.timeZoneIndex];
      $scope.timeZone = $scope.timeZoneList[$scope.timeZoneIndex];
    };
    // void
    controller.displayNothing = function () {
      $scope.prevHour = '';
      $scope.hour = '';
      $scope.prevMinute = '';
      $scope.minute = '';
      $scope.prevNoon = '';
      $scope.noon = '';
      $scope.prevTimeZone = '';
      $scope.timeZone = '';
    };
    controller.removeLeadingZero = function (numString) {
      return numString.replace(/^0+/, '');
    };
    (function init() {
      if ($scope.time) {
        if (!controller.isInvalidFormat()) {
          var timezoneString, times;
          var timezoneRange = '-';
          if ($scope.time.split('.').length === 3) {
            var time_format_period = $scope.time.split('.');
            $scope.prevHour = controller.removeLeadingZero(time_format_period[0]);
            $scope.hour = controller.removeLeadingZero(time_format_period[0]);
            $scope.prevMinute = time_format_period[1];
            $scope.minute = time_format_period[1];
            if ($scope.timezoneMode) {
              times = time_format_period[2].split('-');
              if (times.length === 1) {
                times = time_format_period[2].split('+');
                timezoneRange = '+';
              }
              time_format_period[2] = times[0];
              timezoneString = timezoneRange + times[1];
              $scope.timeZoneIndex = _.indexOf($scope.timeZoneList, $scope.timeZone);
              $scope.timeZone = 'GMT' + timezoneString;
              $scope.prevTimeZone = 'GMT' + timezoneString;
            }
            $scope.prevNoon = time_format_period[2].toUpperCase();
            $scope.noon = time_format_period[2].toUpperCase();
          } else {
            var time_format_colon = $scope.time.split(':');
            $scope.prevHour = controller.removeLeadingZero(time_format_colon[0]);
            $scope.hour = controller.removeLeadingZero(time_format_colon[0]);
            $scope.prevMinute = time_format_colon[1];
            $scope.minute = time_format_colon[1];
            if ($scope.timezoneMode) {
              times = time_format_colon[2].split('-');
              if (times.length === 1) {
                times = time_format_colon[2].split('+');
                timezoneRange = '+';
              }
              time_format_colon[2] = times[0];
              timezoneString = timezoneRange + times[1];
              $scope.timeZoneIndex = _.indexOf($scope.timeZoneList, $scope.timeZone);
              $scope.timeZone = 'GMT' + timezoneString;
              $scope.prevTimeZone = 'GMT' + timezoneString;
            }
            $scope.prevNoon = time_format_colon[2].toUpperCase();
            $scope.noon = time_format_colon[2].toUpperCase();
          }
        } else {
          // not valid, so display nothing in the component ui
          controller.displayNothing();
        }
      } else {
        controller.setDefaultTime();
      }
    }());
  }
]);
/*jshint evil:true*/
'use strict';
angular.module('ark-components').directive('arkTimePicker', function () {
  return {
    restrict: 'E',
    scope: {
      time: '=ngModel',
      headerLabel: '@label',
      widgetMode: '@',
      timezoneMode: '@'
    },
    controller: 'arkTimePickerCtrl',
    templateUrl: 'ark-time-picker/ark-time-picker.html',
    link: function ($scope) {
      $scope.widgetMode = $scope.$eval($scope.widgetMode) || false;
      $scope.timezoneMode = $scope.$eval($scope.timezoneMode) || false;
      $scope.$watchCollection('[hour, minute, noon, timeZone]', function () {
        $scope.time = $scope.hour + '.' + $scope.minute + '.' + $scope.noon;
        if ($scope.timezoneMode) {
          $scope.time += $scope.timeZone;
          $scope.time = $scope.time.replace('GMT', '');
        }
      });
    }
  };
}).directive('whilePressed', [
  '$parse',
  '$interval',
  function ($parse, $interval) {
    return {
      restrict: 'A',
      link: function (scope, element, attrs) {
        var action = $parse(attrs.whilePressed), intervalPromise = null, TICK_LENGTH = 250;
        function tickAction() {
          action(scope);
        }
        function bindWhilePressed() {
          element.on('mousedown', beginAction);
        }
        function beginAction(e) {
          e.preventDefault();
          scope.$apply(action);
          intervalPromise = $interval(tickAction, TICK_LENGTH);
          element.on('mouseup', endAction);
          element.on('mouseleave', endAction);
        }
        function endAction() {
          $interval.cancel(intervalPromise);
          element.off('mouseup', endAction);
          element.off('mouseleave', endAction);
        }
        bindWhilePressed();
      }
    };
  }
]);
/*jshint evil:false*/
'use strict';
/*
 * AngularJS Toaster
 * Version: 0.4.7
 *
 * Copyright 2013 Jiri Kavulak.
 * All Rights Reserved.
 * Use, reproduction, distribution, and modification of this code is subject to the terms and
 * conditions of the MIT license, available at http://www.opensource.org/licenses/mit-license.php
 *
 * Author: Jiri Kavulak
 * Related to project of John Papa and Hans Fjällemark
 */
angular.module('ark-components').service('toaster', [
  '$rootScope',
  function ($rootScope) {
    this.pop = function (type, title, body, timeout, clickHandler) {
      this.toast = {
        type: type,
        title: title,
        body: body,
        timeout: timeout,
        bodyOutputType: '',
        clickHandler: clickHandler
      };
      $rootScope.$broadcast('toaster-newToast');
    };
    this.clear = function () {
      $rootScope.$broadcast('toaster-clearToasts');
    };
  }
]).constant('toasterConfig', {
  'limit': 0,
  'close-button': false,
  'time-out': 3000,
  'icon-classes': {
    error: 'icon-alert-circle',
    info: 'icon-alert-info',
    wait: 'icon-clock',
    success: 'icon-alert-checkmark',
    warning: 'icon-alert-triangle'
  },
  'body-output-type': '',
  'body-template': 'toasterBodyTmpl.html',
  'icon-class': 'icon-alert-info',
  'position-class': 'toast-bottom-right',
  'title-class': 'toast-title',
  'message-class': 'toast-message',
  'check-for-navbar': false,
  'width': 22.5
}).directive('arkToaster', [
  '$compile',
  '$timeout',
  '$sce',
  'toasterConfig',
  'toaster',
  function ($compile, $timeout, $sce, toasterConfig, toaster) {
    return {
      replace: true,
      restrict: 'EA',
      scope: true,
      link: function (scope, elm, attrs) {
        var id = 0, mergedConfig = {};
        function configure (options) {
          mergedConfig = angular.extend({}, toasterConfig, options);
          scope.config = {
            position: mergedConfig['position-class'],
            title: mergedConfig['title-class'],
            message: mergedConfig['message-class'],
            closeButton: mergedConfig['close-button'],
            width: mergedConfig.width
          };
        }
        configure();
        scope.$watch(attrs.toasterOptions, configure);

        scope.configureTimer = function configureTimer(toast) {
          var timeout = typeof toast.timeout === 'number' ? toast.timeout : mergedConfig['time-out'];
          if (timeout > 0 && !toast.timerId) {
            toast.timerId = $timeout(function () {
              scope.removeToast(toast.id);
            }, timeout);
          }
        };
        scope.setTop = function () {
          var boundClient = angular.element('nav.navbar.navbar-default')[0].getBoundingClientRect();
          var newVal = boundClient.top + boundClient.height;
          switch (true) {
          case newVal < 0:
            elm.css('bottom', 0);
            break;
          case newVal >= 0:
            elm.css('bottom', newVal);
            break;
          }
        };
        if (mergedConfig['check-for-navbar'] && angular.element('nav.navbar.navbar-default').length) {
          scope.$watch(function () {
            return scope.toasters.length;
          }, function (newVal) {
            if (newVal === 0) {
              window.removeEventListener('scroll', scope.setTop);
            }
          }, true);
        }
        function addToast(toast) {
          if (mergedConfig['check-for-navbar'] && angular.element('nav.navbar.navbar-default').length) {
            window.addEventListener('scroll', scope.setTop);
            scope.setTop();
          }
          toast.type = mergedConfig['icon-classes'][toast.type];
          if (!toast.type) {
            toast.type = mergedConfig['icon-class'];
          }
          id++;
          angular.extend(toast, { id: id });
          // // Set the toast.bodyOutputType to the default if it isn't set
          // toast.bodyOutputType = toast.bodyOutputType || mergedConfig['body-output-type'];
          // switch (toast.bodyOutputType) {
          //     case 'trustedHtml':
          //         toast.html = $sce.trustAsHtml(toast.body);
          //         break;
          //     case 'template':
          //         toast.bodyTemplate = toast.body || mergedConfig['body-template'];
          //         break;
          // }
          scope.configureTimer(toast);
          //if (mergedConfig['newest-on-top'] === true) {
          scope.toasters.unshift(toast);
          if (mergedConfig.limit > 0 && scope.toasters.length > mergedConfig.limit) {
            scope.toasters.pop();  // } else {
                                   //     scope.toasters.push(toast);
                                   //     if (mergedConfig.limit > 0 && scope.toasters.length > mergedConfig.limit) {
                                   //         scope.toasters.shift();
                                   //     }
          }
        }
        scope.toasters = [];
        scope.$on('toaster-newToast', function () {
          addToast(toaster.toast);
        });
        scope.$on('toaster-clearToasts', function () {
          scope.toasters.splice(0, scope.toasters.length);
        });
      },
      controller: [
        '$scope',
        function ($scope) {
          $scope.stopTimer = function (toast) {
            if (toast.timerId) {
              $timeout.cancel(toast.timerId);
              toast.timerId = null;
            }
          };
          $scope.restartTimer = function (toast) {
            if (!toast.timerId) {
              $scope.configureTimer(toast);
            }
          };
          $scope.removeToast = function (id) {
            var i = 0;
            for (i; i < $scope.toasters.length; i++) {
              if ($scope.toasters[i].id === id) {
                break;
              }
            }
            $scope.toasters.splice(i, 1);
          };
          $scope.click = function (toaster) {
            //if ($scope.config.tap === true) {
            if (toaster.clickHandler && angular.isFunction($scope.$parent.$eval(toaster.clickHandler))) {
              $scope.$parent.$eval(toaster.clickHandler)(toaster);
              // var result = $scope.$parent.$eval(toaster.clickHandler)(toaster);
              //if (result === true) {
              $scope.removeToast(toaster.id);  //}
            } else {
              if (angular.isString(toaster.clickHandler)) {
                console.log('TOAST-NOTE: Your click handler is not inside a parent scope of toaster-container.');
              }
              $scope.removeToast(toaster.id);
            }  //}
          };
        }
      ],
      template: '<div id="toast-container" ng-class="config.position" style="width: {{config.width}}%">' + '<div class="toaster-top-bar" ng-show="toasters.length > 4">{{toasters.length}} notifications<div class="toaster-hide-all" ng-click="clear()">Hide all</div></div>' + '<div ng-repeat="toaster in toasters" class="toast" ng-click="click(toaster)" ng-mouseover="stopTimer(toaster)" ng-mouseout="restartTimer(toaster)">' + '<button class="toast-close-button" ng-show="config.closeButton"><span class="icon-close close toaster-dialog-close ng-scope"></span></button>' + '<div class="toaster-message-container">' + '<span ng-class="toaster.type" class="toasterType"></span>' + '<h1><div ng-class="config.title">{{toaster.title}}</div></h1>' + '</div>' + '<div ng-class="config.message" ng-switch on="toaster.bodyOutputType">' + '<div ng-switch-when="trustedHtml" ng-bind-html="toaster.html"></div>' + '<div ng-switch-when="template"><div ng-include="toaster.bodyTemplate"></div></div>' + '<div ng-switch-default >{{toaster.body}}</div>' + '</div>' + '</div>' + '</div>'
    };
  }
]);
'use strict';
angular.module('ark-components').directive('arkToolbar', function () {
  return {
    restrict: 'E',
    transclude: false,
    replace: false,
    scope: true,
    templateUrl: 'ark-toolbar/ark-toolbar.html',
    link: function (scope, element, attributes) {
      var requestedToolbarType = attributes.config;
      scope.$watch(function () {
        return scope[requestedToolbarType];
      }, function () {
        scope.options = scope[requestedToolbarType];
      }, true);
    }  // controller: function($scope, $element, $attrs) {
       //   $scope.$watch(function() {
       //     return angular.element($element).find('input, button.selectpicker').length;
       //   }, function(newV, oldV) {
       //     // Do something every time an input or select tag is rendered in DOM
       //     // nothing implimented yet
       //   });
       // },
  };
});
/*jshint ignore:start*/
'use strict';
angular.module('ark-components').directive('parseHandlers', [
  '$compile',
  function ($compile) {
    return {
      restrict: 'A',
      scope: { handlerArray: '=' },
      link: function ($scope, element, attrs) {
        for (var i = 0; i < $scope.handlerArray.length; i++) {
          if ($scope.handlerArray[i].handler) {
            if (angular.isFunction($scope.handlerArray[i].handler)) {
              var name = $scope.handlerArray[i].handlerName;
              var handler = $scope.handlerArray[i].handler;
              element.bind(name, function (event) {
                handler(event);
              });
            } else {
              element.attr($scope.handlerArray[i].handlerName, $scope.handlerArray[i].handler);
            }
          } else {
            element.attr($scope.handlerArray[i].handlerName, '');
          }
        }
      }
    };
  }
]);  /*jshint ignore:start*/