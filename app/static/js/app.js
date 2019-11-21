'use strict';
angular.module('Portal', ['Portal.services', 'Portal.controllers', 'Portal.filters',
  'Portal.directives', 'ui.router', 'ngSanitize', 'ngResource', 'ui.bootstrap',
  'ui.utils', 'ui.select', 'ngCsv', 'ngFileUpload', 'ngCookies', 'colorpicker.module', 'ngNotificationsBar', 'angular-loading-bar', 'ngAnimate', 'uiSwitch'])
    .config(['$stateProvider', '$urlRouterProvider', function ($stateProvider, $urlRouterProvider) {
      $stateProvider
        .state('login', {
          url: '/login',
          views: {
            content: {
              templateUrl: 'static/views/login.html',
              controller: 'LoginController'
            }
          }
        })
        .state('organizations', {
          url: '/organizations',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              template: '<do-organizations></do-organizations>'
            }
          }
        })
        .state('org-add', {
          url: '/organizations/add',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/organization-edit.html',
              controller: 'OrganizationEditController'
            }
          }
        })
        .state('org-edit', {
          url: '/organizations/:id',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/organization-edit.html',
              controller: 'OrganizationEditController'
            }
          }
        })
        .state('organization_groups', {
          url: '/organization_groups',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              template: '<do-organization-groups></do-organization-groups>',
              controller: 'OrganizationGroupsController'
            }
          }
        })
        .state('vulnerabilities', {
          url: '/vulnerabilities',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              template: '<do-vulnerabilities></do-vulnerabilities>'
            }
          }
        })
        .state('vuln-add', {
          url: '/vulnerabilities/add',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/vulnerability-edit.html',
              controller: 'VulnerabilityEditController'
            }
          }
        })
        .state('vuln-edit', {
          url: '/vulnerabilities/:id',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/vulnerability-edit.html',
              controller: 'VulnerabilityEditController'
            }
          }
        })
        .state('list-archive', {
          url: '/list-archive',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/messages.html',
              controller: 'ListArchiveController'
            }
          }
        })
        .state('deliverables', {
          url: '/deliverables',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/deliverables.html',
              controller: 'DeliverablesController'
            }
          }
        })
        .state('deliverable-files', {
          url: '/deliverable-files',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/deliverable-files.html',
              controller: 'DeliverableFilesController'
            }
          }
        })
        .state('account', {
          url: '/account',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              template: '<do-my-account></do-my-account>'
            }
          }
        })
        .state('samples', {
          url: '/samples',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/samples.html',
              controller: 'SamplesController'
            }
          }
        })
        .state('submit-sample', {
          url: '/samples/submit',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/sample-submit.html',
              controller: 'SamplesUploadController'
            }
          }
        })
        .state('submit-url', {
          url: '/urls/submit',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/submit-url.html',
              controller: 'URLsUploadController'
            }
          }
        })
        .state('viewReport', {
          url: '/report/:sha256/:id',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/report.html',
              controller: function ($scope, $stateParams) {
                $scope.sha256 = $stateParams.sha256;
                $scope.sid = $stateParams.id;
              }
            }
          }
        })
        .state('viewAllReports', {
          url: '/multiav/all/:sha256',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/multiav-all-reports.html',
              controller: 'MultiAVAllReportsController'
            }
          }
        })
        .state('lists', {
          url: '/lists',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/lists.html',
              controller: 'ListsController'
            }
          }
        })
        .state('editList', {
          url: '/lists/:id/edit',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/list-edit.html',
              controller: 'ListEditController'
            }
          }
        })
        .state('listSettings', {
          url: '/lists/:id/settings',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/list-settings.html',
              controller: 'ListSettingsController'
            }
          }
        })
        .state('investigation', {
          url: '/investigation/:room',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/investigation.html',
              controller: 'InvestigationController'
            }
          }
        })
        .state('bulk_ah_process', {
          url: '/bulk_ah_process',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/bulk_ah_process.html',
              controller: 'BulkAHProcessController'
            }
          }
        })
        .state('bulk_ip_check', {
          url: '/bulk_ip_check',
          views: {
            header: {
              templateUrl: 'static/views/header.html',
              controller: 'HeaderController'
            },
            content: {
              templateUrl: 'static/views/bulk_ip_check.html',
              controller: 'BulkIPCheckController'
            }
          }
        });
      $urlRouterProvider.otherwise('/organizations');
    }])
    .config(function ($logProvider) {
      $logProvider.debugEnabled(true);
    })
    .config(['notificationsConfigProvider', function (notificationsConfigProvider) {
      // auto hide
      notificationsConfigProvider.setAutoHide(true);

      // delay before hide
      notificationsConfigProvider.setHideDelay(3000);

      // support HTML
      notificationsConfigProvider.setAcceptHTML(false);

      // Set an animation for hiding the notification
      notificationsConfigProvider.setAutoHideAnimation('fadeOutNotifications');

      // delay between animation and removing the nofitication
      notificationsConfigProvider.setAutoHideAnimationDelay(1000);
    }])
    .config(['cfpLoadingBarProvider', function (cfpLoadingBarProvider) {
      //cfpLoadingBarProvider.includeSpinner = true;
      cfpLoadingBarProvider.latencyThreshold = 250; //ms
    }])
    .config(['$httpProvider', function ($httpProvider) {
      var authInterceptor = function ($q, $cookies, $location, notifications) {
        return {
          'request': function (config) {
            $cookies.put('rm', $cookies.get('rm'));
            return config;
          },
          'response': function (resp) {
            return resp;
          },
          'requestError': function (rejection) {
            return $q.reject(rejection);
          },
          'responseError': function (rejection) {
            if (rejection.status === 401) {
              if (rejection.data.validator === 'signature') {
                $cookies.remove('rm');
              }
              $location.path('/login');
              notifications.showWarning("Please login to continue");
              return $q.reject(rejection);
            }
            return $q.reject(rejection);
          }
        }
      };
      $httpProvider.interceptors.push(authInterceptor);
    }])
    .run(['$rootScope', function ($rootScope) {
      $rootScope.alerts = [];
      $rootScope.closeAlert = function (index) {
        $rootScope.alerts.splice(index, 1);
      };
    }])
    .value('version', '1.8.0');
