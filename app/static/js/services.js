'use strict';

angular.module('Portal.services', ['ngCookies', 'Portal.configuration'])
    .factory('ErrorMapper', ['$rootScope', 'inflectorFilter', function ($rootScope, inflector) {
      var fieldNames = {
        abbreviation: 'Abbreviation',
        full_name: 'Address',
        cidr: 'CIDR',
        subject: 'Subject',
        list_id: 'Mailing list'
      };
      var validatorMessages = {
        // json schema validators
        '$ref': true,
        'additionalItems': true,
        'additionalProperties': true,
        'allOf': true,
        'anyOf': true,
        'dependencies': true,
        'enum': true,
        'format': {
          default: 'is invalid',
          cidr: 'is invalid'
        },
        'items': true,
        'maxItems': true,
        'maxLength': true,
        'maxProperties': true,
        'maximum': true,
        'minItems': true,
        'minLength': true,
        'minProperties': true,
        'minimum': true,
        'multipleOf': true,
        'not': true,
        'oneOf': true,
        'pattern': true,
        'patternProperties': true,
        'properties': true,
        required: {
          default: 'is required',
          terms: 'must be accepted'
        },
        'type': true,
        'uniqueItems': true

      };
      return {
        map: function (response) {
          if (!response.hasOwnProperty('validator')) {
            return response.msg;
          }
          var field = response.msg.split("'")[1];
          if (response.validator == 'format') {
            field = response.msg.split("'")[3];
          }
          if (!fieldNames.hasOwnProperty(field)) {
            fieldNames[field] = inflector(field, 'humanize');
          }
          //console.log(inflector(field, 'humanize'));
          if (validatorMessages[response['validator']][field] !== undefined) {
            return fieldNames[field] + " " + validatorMessages[response['validator']][field];
          }
          return fieldNames[field] + " " + validatorMessages[response['validator']]['default'];
        }
      }
    }])
    .factory('Session', ['$location', function ($location) {
      return {
        get: function (key) {
          return sessionStorage.getItem(key);
        },
        set: function (key, val) {
          return sessionStorage.setItem(key, val);
        },
        unset: function (key) {
          return sessionStorage.removeItem(key);
        }
      }
    }])
    .factory('Auth', ['$http', '$location', '$cookies', 'Session', 'notifications', function ($http, $location, $cookies, Session, notifications) {
      var cacheSession = function (response, status, headers) {
        // this is never used, we pass the cookie with all requests
        // using the authInterceptor
        Session.set('auth', $cookies.get('rm'));
      };
      var uncacheSession = function () {
        Session.unset('auth');
      };

      var loginError = function (response) {
        notifications.showError(response);
      };

      return {
        login: function (credentials) {
          var login = $http.post("/auth/login", credentials);
          login.error(loginError);
          login.success(cacheSession);
          return login;
        },
        logout: function () {
          var logout = $http.get("/auth/logout");
          logout.success(uncacheSession);
          return logout;
        },
        isLoggedIn: function () {
          return Session.get('auth');
        },
        registerCPAccount: function (userInfo) {
          return $http.post('/auth/register', userInfo);
        },
        unregisterCPAccount: function (userInfo) {
          return $http.post('/auth/unregister', userInfo);
        },
        getAccountInfo: function () {
          return $http.get('/auth/account');
        },
        resetAPIKey: function () {
          return $http.get('/auth/reset-api-key');
        }
      }
    }])
    .factory('Organization', ['$resource', 'apiConfig', function ($resource, apiConfig) {
      /**
       * PATH Verb POST Result
       * /organizations GET None All entries
       * /organizations POST JSON Create new entry
       * /organizations/:id GET None Return entry $id
       * /organizations/:id PUT JSON Update entry $id
       * /organizations/:id DELETE None Delete entry $id
       *
       */
      return $resource(apiConfig.urlPrefix + '/organizations/:id', {}, {
        query: {
          method: 'GET',
          isArray: false
        },
        update: {
          url: apiConfig.urlPrefix + '/organizations/:id',
          method: 'PUT',
          params: {id: '@id'}
        },
        check: {
          url: apiConfig.urlPrefix + '/organizations/check',
          method: 'PUT'
        }
      });
    }])
    .factory('List', ['$resource', 'apiConfig', function ($resource, apiConfig) {
      return $resource(apiConfig.urlPrefix + '/lists/:id', {}, {
        query: {
          method: 'GET',
          isArray: false
        },
        update: {
          url: apiConfig.urlPrefix + '/lists/:id',
          method: 'PUT',
          params: {id: '@id'}
        },
        unsubscribe: {
          url: apiConfig.urlPrefix + '/lists/:id/unsubscribe',
          method: 'PUT',
          params: {id: '@id'}
        },
        subscribe: {
          url: apiConfig.urlPrefix + '/lists/:id/subscribe',
          method: 'PUT',
          params: {id: '@id'}
        },
        post: {
          url: apiConfig.urlPrefix + '/lists/post',
          method: 'POST'
        },
        check_gpg: {
          url: apiConfig.urlPrefix + '/lists/:id/check_gpg',
          method: 'GET',
          params: {id: '@id'}
        }
      });
    }])
    .factory('GridData', ['$resource', 'apiConfig', function ($resource, apiConfig) {
      return function (endpoint) {
        return $resource(apiConfig.urlPrefix + '/' + endpoint + '/:id', {}, {
          query: {
            method: 'GET',
            isArray: false,
            params: {id: '@id'}
          },
          update: {
            url: apiConfig.urlPrefix + '/' + endpoint + '/:id',
            method: 'PUT',
            params: {id: '@id'}
          }
        });
      };
    }])
    .factory('FireEye', ['$resource', 'apiConfig', function ($resource, apiConfig) {
      return $resource(apiConfig.urlPrefix + '/analysis/fireeye/:sha256/:sid', {}, {
        query: {
          method: 'GET',
          isArray: false,
          params: {sha256: '@sha256', sid: '@sid'}
        },
        envs: {
          url: apiConfig.urlPrefix + '/analysis/fireeye/environments',
          method: 'GET',
          cache: true
        },
        report: {
          url: apiConfig.urlPrefix + '/analysis/fireeye/report/:sha256/:rid',
          method: 'GET',
          params: {sha256: '@sha256', rid: '@rid'},
          cache: true
        }
      });
    }])
    .factory('FileReader', ['$q', '$log', function ($q, $log) {
      var onLoad = function (reader, deferred, scope) {
        return function () {
          scope.$apply(function () {
            deferred.resolve(reader.result);
          });
        };
      };

      var onError = function (reader, deferred, scope) {
        return function () {
          scope.$apply(function () {
            deferred.reject(reader.result);
          });
        };
      };

      var onProgress = function (reader, scope) {
        return function (event) {
          scope.$broadcast("fileProgress",
              {total: event.total, loaded: event.loaded});
        };
      };

      var getReader = function (deferred, scope) {
        var reader = new FileReader();
        reader.onload = onLoad(reader, deferred, scope);
        reader.onerror = onError(reader, deferred, scope);
        reader.onprogress = onProgress(reader, scope);
        return reader;
      };

      var readAsDataURL = function (file, scope) {
        var deferred = $q.defer();

        var reader = getReader(deferred, scope);
        reader.readAsDataURL(file);

        return deferred.promise;
      };
      var readAsText = function (file, scope) {
        var deferred = $q.defer();

        var reader = getReader(deferred, scope);
        reader.readAsText(file);

        return deferred.promise;
      };

      return {
        readAsDataUrl: readAsDataURL,
        readAsText: readAsText
      };
    }])
    .factory('DOAPI', [function () {
      return {
        getAugmentKey: function (string) {
          var shaObj = new jsSHA(btoa(string), "B64");
          return shaObj.getHash("SHA-1", "HEX");
        },
        getId: function (length) {
          var len = (angular.isNumber(length)) ? length : 8;
          var text = "";
          var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";

          for (var i = 0; i < len; i++)
            text += possible.charAt(Math.floor(Math.random() * possible.length));

          return text;
        },
        getRandomInt: function (min, max) {
          return Math.floor(Math.random() * (max - min)) + min;
        },
        logRawInput: function (data) {
          $log.debug('RECV: ' + data);
        },
        logRawOutput: function (data) {
          $log.debug('SENT: ' + data);
        }
      }
    }])
    .factory('QueryCache', ['$cacheFactory', function ($cacheFactory) {
      return $cacheFactory('QueryCache');
    }])
    .factory('BOSH', ['$rootScope', '$cookies', 'boshConfig', function ($rootScope, $cookies, props) {

      return {
        getJid: function (obj) {
          var sess = $cookies.get('bosh_session');
          var jid = props.connection ? (props.connection.jid ||
          props.connection._proto.jid) : sess.jid;
          if (obj.bare) {
            return jid.split('/')[0];
          } else {
            return jid;
          }
        },
        hasPreviousSession: function () {
          return !!$cookies.get('bosh_session');
        },
        setSession: function () {
          var session = {};
          session.url = props.connection.service;
          session.jid = props.connection.jid || props.connection._proto.jid;
          session.sid = props.connection.sid || props.connection._proto.sid;
          session.rid = props.connection.rid || props.connection._proto.rid;
          $cookies.putObject('bosh_session', session);
        },
        deleteSession: function () {
          $cookies.remove('bosh_session');
        },
        storeSessionData: function () {
          if (props.connection) {
            this.setSession();
          } else {
            this.deleteSession();
          }
        },
        attach: function (sess) {
          props.connection = new Strophe.Connection(sess.service, {'keepalive': true});
          props.connection.attach(sess.jid, sess.sid, sess.rid, this.checkStatus, 60);
        },
        connect: function (obj) {
          props.connection = new Strophe.Connection(obj.url);
          props.connection.connect(obj.jid + props.resource, obj.passwd, this.checkStatus, 60);
        },
        disconnect: function () {
          if (props !== undefined && props.connection != null) {
            props.connection.flush();
            props.connection.options.sync = true;
            props.connection.disconnect();
          } else {
            console.log('props empty...');
          }

        },
        checkConnection: function () {
          return props.connection != null ? props.connection.connected : false;
        },

        checkStatus: function (status) {
          switch (status) {
            case Strophe.Status.CONNECTING:
              props.connectionStatus = 'Connecting';
              break;
            case Strophe.Status.CONNECTED:
              props.connectionStatus = 'Connected';
              $rootScope.$broadcast('bosh-connected');
              break;
            case Strophe.Status.CONNFAIL:
              props.connectionStatus = 'Failed to connect';
              break;
            case Strophe.Status.AUTHENTICATING:
              props.connectionStatus = 'Authenticating';
              break;
            case Strophe.Status.AUTHFAIL:
              props.connectionStatus = 'Failed to authenticate';
              break;
            case Strophe.Status.DISCONNECTING:
              props.connectionStatus = 'Disconnecting';
              break;
            case Strophe.Status.DISCONNECTED:
              props.connectionStatus = 'Disconnected';
              break;
            case Strophe.Status.ATTACHED:
              props.connectionStatus = 'Connected';
              $rootScope.$broadcast('bosh-attached');
              break;
            case Strophe.Status.ERROR:
              props.connectionStatus = 'Error';
              break;
            default:
              break;
          }
          return true;
        }
      }
    }]);
