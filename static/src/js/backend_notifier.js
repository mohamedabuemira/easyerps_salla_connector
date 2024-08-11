odoo.define('easyerps_salla_connector.NotificationManager', function (require) {
    "use strict";
    const core = require('web.core');
    const config = require('web.config');
    const Dialog = require('web.Dialog');
    const dom = require('web.dom');
    const realSession = require('web.session');
    const Widget = require('web.Widget');

    const {
        _t,
        _lt
    } = core;

    const NotificationManager = Widget.extend({
        //template: 'im_od_jahez_api.NotificationManager',

        /**
         * @constructor
         */
        init() {
            this._super(...arguments);
            this._create_webstite_audio();
        },
        /**
         * @override
         */
        start() {
            this.call('bus_service', 'onNotification', this, this._onLongpollingNotifications);
        },
        /**
         * @private
         * @param {Object[]} notifications
         * @param {string} [notifications[i].type]
         */
        async _onLongpollingNotifications(notifications) {
            var self = this;
            realSession.user_has_group('easyerps_salla_connector.salla_backend_sale').then(function (has_group) {
                if (has_group) {
                    for (const {
                        type,
                        payload
                    } of notifications) {
                        if (type === 'salla_webhook' && payload) {
                            self.displayNotification({
                                title: payload.name,
                                message: self.format_message(payload.details),
                                type: "warning",
                                sticky: true,
                            });
                            self._playNewOrder();
                        }
                    }
                }
            });
        },

        _create_webstite_audio() {
            this._audioNewWebsiteOrder = document.createElement('audio');
            this._audioNewWebsiteOrder.src = '/easyerps_salla_connector/static/src/sounds/loop.wav';
        },
        _playNewOrder() {
            this._audioNewWebsiteOrder.play().catch(() => { });
        },
        _stopNewOrder() {
            this._audioNewWebsiteOrder.pause();
        },
        format_message(details) {
            var mess = ''
            for (const {
                product,
                qty
            } of details) {
                mess += product + ' ' + qty + '\n';
            }
            return mess;
        }
    });
    return NotificationManager;
});