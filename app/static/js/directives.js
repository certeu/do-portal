'use strict';

angular.module('Portal.directives', ['Portal.services', 'Portal.templates', 'ui.utils'])
  .directive('doAppVersion', ['version', function(version) {
    return function(scope, elem, attrs) { // jshint ignore:line
      elem.text(version);
    };
  }])
  .directive('doAddItem', [function() {
    return {
      restrict: 'A',
      link: function(scope, elem, attrs) { // jshint ignore:line
        scope.addItem = function() {
          var newInput = '<input ng-model=a.asn ng-show="a.active" ' +
            'ui-keypress="{ 13: \'updateItem(a, \\\'asns\\\', $event)\'}" ' +
            'type="number" class="asn-edit">';
          $(newInput).insertBefore(elem);
        };
      }
    };
  }])
  .directive('doConfirm', [function() {
    return {
      priority: -1,
      restrict: 'A',
      link: function(scope, element, attrs) {
        element.bind('click', function(e) {
          var message = attrs.doConfirm;
          if (message && !confirm(message)) {
            e.stopImmediatePropagation();
            e.preventDefault();
          }
        });
      }
    };
  }])
  .directive('doMyAccount', ['Auth', 'notifications', function(Auth, notifications) {
    return {
      templateUrl: '/static/views/directive-do-my-account.html',
      restrict: 'E',
      link: function postLink(scope) {
        scope.credentials = {};
        Auth.getAccountInfo().then(function(resp) {
          scope.account = resp.data;
        });
        scope.resetAPIKey = function() {
          Auth.resetAPIKey().then(
            function(resp) {
              Auth.getAccountInfo().then(function(resp) {
                scope.account = resp.data;
              });
              notifications.showSuccess(resp.data.message);
            },
            function(err) {
              notifications.showError(err.data);
            }
          );
        };
      }
    };
  }])
  .directive('doOrganizationGroups', ['$filter', 'GridData', 'notifications', function($filter, GridData, notifications) {
    return {
      restrict: 'E',
      replace: true,
      templateUrl: '/static/views/directive-organization-groups.html',
      controller: function($scope) {
        $scope.deleteGroup = function(group) {
          GridData('organization_groups').delete(group, function(resp) {
            $scope.groups = $filter('filter')(
              $scope.groups,
              function(v, idx) { // jshint ignore:line
                return v.id !== group.id;
              }
            );
            notifications.showSuccess(resp);
          }, function(error) {
            notifications.showError(error.data);
          });
        };
      },
      link: function(scope, elem, attrs) { // jshint ignore:line
        GridData('organization_groups').query(function(resp) {
          scope.groups = resp.organization_groups;
        });
      }
    };
  }])
  .directive('doVulnerabilities', ['$filter', 'GridData', 'notifications', function($filter, GridData, notifications) {
    return {
      restrict: 'E',
      replace: true,
      templateUrl: '/static/views/directive-vulnerabilities.html',
      controller: function($scope) {
        $scope.deleteVulnerability = function(vuln) {
          GridData('vulnerabilities').delete(vuln, function(resp) {
            $scope.vulnerabilities = $filter('filter')(
              $scope.vulnerabilities,
              function(v, idx) { // jshint ignore:line
                return v.id !== vuln.id;
              }
            );
            notifications.showSuccess(resp);
          }, function(error) {
            notifications.showError(error.data);
          });
        };
        $scope.testVulnerability = function(vuln) {
          GridData('vulnerabilities/test').get(vuln, function(resp) {
            notifications.showSuccess(resp);
            $scope.loadPage($scope.currentPage);
          }, function(error) {
            notifications.showError(error.data);
          });
        };
        $scope.changestatusVulnerability = function(vuln) {
          GridData('vulnerabilities/changestatus').get(vuln, function(resp) {
            notifications.showSuccess(resp);
            $scope.loadPage($scope.currentPage);
          }, function(error) {
            notifications.showError(error.data);
          });
        };
      },

      link: function(scope, elem, attrs) { // jshint ignore:line
        GridData('vulnerabilities').query(function(resp) {
          scope.vulnerabilities = resp.vulnerabilities;
        });
      }
    };
  }])
  .directive('doOrganizations', ['$filter', 'Organization', 'GridData', 'notifications', function($filter, Organization, GridData, notifications) {
    return {
      restrict: 'E',
      replace: true,
      templateUrl: '/static/views/directive-organizations.html',
      controller: function($scope) {
        $scope.deleteOrg = function(org) {
          Organization.delete(org, function(resp) {
            //$scope.organizations = $filter('filter')($scope.organizations, {id: !org.id});
            $scope.organizations = $filter('filter')(
              $scope.organizations,
              function(v, idx) { // jshint ignore:line
                return v.id !== org.id;
              }
            );
            notifications.showSuccess(resp);
          }, function(error) {
            notifications.showError(error.data);
          });
        };

      },
      link: function(scope, elem, attrs) { // jshint ignore:line
        Organization.query(function(resp) {
          scope.organizations = resp.organizations;
        });
      }
    };
  }])
  .directive('doCrudGrid', ['$filter', 'GridData', 'notifications', function($filter, GridData, notifications) {
    return {
      restrict: 'A',
      replace: false,
      scope: {
        excludeKeys: '=?'
      },
      templateUrl: '/static/views/directive-crud-grid-template.html',
      link: function(scope, elem, attrs) {
        scope.objects = [];
        scope.properties = [];
        scope.excludeKeys = scope.excludeKeys || ['id'];
        scope.toggleEditMode = function(o) {
          o.active = !o.active;
        };
        scope.toggleAdd = function() {
          var o = {
            active: true,
            name: ''
          };
          if (!scope.properties || !scope.properties.length) {
            scope.properties = ['name'];
          }
          //scope.properties.forEach(function(field){
          //    o[field] = '';
          //});
          scope.objects.unshift(o);
          //console.log(scope.objects);
        };
        var errorCallback = function(e) {
          notifications.showError(e.data);
        };
        scope.updateItem = function(o) {
          GridData(attrs.endpoint).update({
            id: o.id
          }, o, function(resp) { // jshint ignore:line
            o.active = false;
          }, errorCallback);
        };
        scope.deleteItem = function(o) {
          GridData(attrs.endpoint).delete({
            id: o.id
          }, function(resp) { // jshint ignore:line
            scope.objects = $filter('filter')(
              scope.objects,
              function(v) {
                return v.id !== o.id;
              }
            );
          }, errorCallback);
        };
        var data = GridData(attrs.endpoint).query(function() {
          scope.objects = data[attrs.endpoint];
          var properties = [];
          var obj = scope.objects[0];
          for (var key in obj) {
            if (obj.hasOwnProperty(key) && typeof obj[key] !== 'function' && scope.excludeKeys.indexOf(key) === -1) {
              properties.push(key);
            }
          }
          scope.properties = properties;
        });
      }
    };
  }])
  .directive('doSampleDetails', ['GridData', 'notifications', function(GridData, notifications) {
    return {
      restrict: 'E',
      templateUrl: 'do/templates/do-sample-details.html',
      link: function(scope, elem, attrs) {
        GridData('samples').get({
          id: attrs.hash
        }).$promise.then(
          function(response) {
            scope.sample = response;
          },
          function(error) {
            notifications.showError(error.data);
          }
        );
      }
    };
  }])
  .directive('doStaticAnalysisReport', ['GridData', 'notifications', function(GridData, notifications) {
    return {
      restrict: 'E',
      templateUrl: 'do/templates/do-static-analysis-report.html',
      link: function(scope, elem, attrs) {
        GridData('analysis/static').get({
          id: attrs.hash
        }).$promise.then(
          function(response) {
            scope.static_report = response;
            scope.hexdump_lines = response.report_parsed.hex.match(/^.*((\r\n|\n|\r)|$)/gm);
            var bytes = [];
            for (var i = 0; i <= 15; i++) {
              bytes.push('0' + i.toString(16).toUpperCase());
              scope.bytes = bytes;
            }
          },
          function(error) {
            notifications.showError(error.data);
          }
        );
      }
    };
  }])
  .directive('doAvReport', ['GridData', 'notifications', function(GridData, notifications) {
    return {
      restrict: 'E',
      templateUrl: 'do/templates/do-av-report.html',
      link: function(scope, elem, attrs) {
        GridData('analysis/av').get({
          id: attrs.hash
        }).$promise.then(
          function(response) {
            scope.av_results = response;
          },
          function(error) {
            notifications.showError(error.data);
          }
        );
      }
    };
  }])
  .directive('doDynamicAnalysisReport', ['VxStream', 'notifications', 'apiConfig', '$location', '$q', '$filter', '$sce', function(VxStream, notifications, apiConfig, $location, $q, $filter, $sce) {
    return {
      restrict: 'E',
      templateUrl: 'do/templates/do-dynamic-analysis-report.html',
      link: function(scope, elem, attrs) {
        VxStream.envs().$promise.then(function(resp) {
          scope.envs = resp.environments;
          var promises = [];
          for (var eid in resp.environments) {
            var envId = resp.environments[eid].id;
            promises.push(
              VxStream.get({
                sha256: attrs.hash,
                envId: envId
              }).$promise
            );
          }
          $q.all(promises).then(function(results) {
            for (var ridx in results) {
              if (results[ridx].response !== false) {
                var thisEnv = $filter('filter')(
                  scope.envs, {
                    id: results[ridx].response.environmentId
                  }
                );
                results[ridx].response.environmentName = thisEnv[0].name;
                if (results[ridx].response.analysis_start_time !== undefined) {
                  results[ridx].response.html_report = true;
                  //debugger;
                  results[ridx].response.html_report_url =
                    $sce.trustAsResourceUrl($location.protocol() + '://' + $location.host() + ':' + $location.$$port + apiConfig.urlPrefix +
                      '/analysis/vxstream/report/' +
                      attrs.hash + '/' + thisEnv[0].id + '/html');

                }
              }
            }
            scope.summaries = results;
            scope.dld = {
              html: 'HTML',
              json: 'JSON',
              bin: 'Binary',
              pcap: 'PCAP'

            };

          });
        }, function(error) {
          notifications.showError(error.data);
        });
      }
    };
  }])
  .directive('doFileSelect', [function() {
    return {
      link: function(scope, elem) {
        elem.bind('change', function(e) {
          scope.getFile(e.target.files[0]);
        });
      }
    };
  }])
  .directive('doScrollIf', ['$timeout', function($timeout) {
    return {
      restrict: 'A',
      scope: {
        scrollIf: '='
      },
      link: function(scope, elem) {
        $timeout(function() {
          if (!scope.scrollIf) {
            window.scrollTo(0, elem[0].offsetTop - 100);
          }
        });
      }
    };

  }])
  .directive('doOnEnter', function() {
    return function(scope, element, attrs) {
      element.bind("keydown keypress", function(event) {
        if (event.which === 13) {
          scope.$apply(function() {
            scope.$eval(attrs.doOnEnter);
          });
          event.preventDefault();
        }
      });
    };
  });

angular.module('Portal.templates', []).run(['$templateCache', 'apiConfig', function($templateCache, apiConfig) {
  $templateCache.put('do/templates/do-sample-details.html',
    '<h3>Details</h3>' +
    '<table class="table table-condensed table-plain">' +
    '<tbody>' +
    '<tr ng-repeat="(key, value) in sample">' +
    '<td><strong>{{ key }}</strong></td>' +
    '<td> {{ value }}</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>'
  );
  $templateCache.put('do/templates/do-static-analysis-report.html',
    '<h4>File identification (libmagic) ({{ static_report.created }})</h4><hr>' +
    '<table class="table table-condensed table-plain">' +
    '<tbody>' +
    '<tr ng-repeat="(key, value) in static_report.report_parsed.magic">' +
    '<td><strong>{{ key }}</strong></td>' +
    '<td> {{ value }}</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>' +
    '<h4>File identification (TrID)</h4><hr>' +
    '<table class="table table-condensed table-plain">' +
    '<tbody>' +
    '<tr ng-repeat="trid in static_report.report_parsed.trID">' +
    '<td><strong>{{ trid.extension }}</strong></td>' +
    '<td> {{ trid.description }} ({{ trid.probability}})</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>' +
    '<h4>Metadata</h4><hr>' +
    '<table class="table table-condensed table-plain">' +
    '<tbody>' +
    '<tr ng-repeat="(key, value) in static_report.report_parsed.exif[0]">' +
    '<td><strong>{{ key }}</strong></td>' +
    '<td> {{ value }}</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>' +
    '<h4>Hexdump (first 1024 bytes)</h4><hr>' +
    '<table class="table table-condensed table-plain">' +
    '<tbody>' +
    '<tr>' +
    '<td></td>' +
    '<td class="hexview">' +
    '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;' +
    '<span class="hexview" ng-repeat="b in bytes">' +
    '{{ b }} </span>' +
    '</td>' +
    '</tr>' +
    '<tr>' +
    '<td></td>' +
    '<td>' +
    '<span class="row linerow hexview" ng-repeat="line in hexdump_lines track by $index"> {{ line}}</span>' +
    '</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>'
  );
  $templateCache.put('do/templates/do-av-report.html',
    '<h4>AntiVirus scan results ({{ av_results.created }})</h4><hr>' +
    '<table class="table table-condensed table-plain">' +
    '<tbody>' +
    '<tr ng-repeat="(av, report) in av_results.report_parsed">' +
    '<td><strong>{{ av }}</strong></td>' +
    '<td ng-hide="report | isEmpty" class="danger">' +
    '<p ng-repeat="(path, details) in report">' +
    '<!--span>{{ path | pathsEnd }}</span-->' +
    '<span title="{{ path }}">{{ details }}</span>' +
    '</p>' +
    '</td>' +
    '<td ng-show="report | isEmpty" class="success">' +
    '<p>Clean</p>' +
    '</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>'
  );
  $templateCache.put('do/templates/do-dynamic-analysis-report.html',
    '<h4>Dynamic analysis report</h4><hr>' +
    '<uib-tabset>' +
    '<uib-tab ng-repeat="summary in summaries" ' +
    'heading="{{summary.response.environmentName}}">' +
    '<div ng-show="summary.response.html_report">Download: ' +
    '<a target="_blank" ng-repeat="(k, v) in dld" href="' + apiConfig.urlPrefix + '/analysis/vxstream/download/{{summary.response.sha256}}/{{summary.response.environmentId}}/{{k}}">{{ v }} | </a>' +
    '</div>' +
    '<table class="table table-condensed table-plain" ng-show="!summary.response.html_report">' +
    '<tbody>' +
    '<tr ng-repeat="(key, value) in summary.response" ng-show="key!=\'environmentId\'">' +
    '<td><strong>{{ key | humanize }}</strong></td>' +
    '<td>{{ value }}</td>' +
    '</tr>' +
    '</tbody>' +
    '</table>' +
    '<iframe ng-show="summary.response.html_report" width="100%" height="1000" frameborder="0" sandbox="allow-scripts allow-same-origin" ng-src="{{ summary.response.html_report_url }}">' +
    '</iframe>' +
    '</uib-tab>' +
    '</uib-tabset>'
  );
}]);
