odoo.define("easyerps_salla_connector.ManyTagsLinkWidgets", function(require){
"use strict";

var core = require('web.core');
var dialogs = require('web.view_dialogs');
var _t = core._t;
var qweb = core.qweb;

var relational_fields = require('web.relational_fields');
relational_fields.FormFieldMany2ManyTags.include({
    events: _.extend({}, relational_fields.FieldMany2ManyTags.prototype.events, {
        'click :not(.dropdown-toggle):not(.o_input_dropdown):not(.o_input):not(:has(.o_input)):not(.o_delete):not(:has(.o_delete))': '_onClickLink',
        'click .dropdown-toggle': '_onOpenColorPicker',
        'mousedown .o_colorpicker a': '_onUpdateColor',
        'mousedown .o_colorpicker .o_hide_in_kanban': '_onUpdateColor',
    }),

    /**
     * @private
     * @param {jQuery} element
     */
    _getBadgeId: function(element){
            if ($(element).hasClass('badge')) return $(element).data('id');
            return $(element).closest('.badge').data('id');
    },

    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.hasDropdown = !!this.colorField;
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onClickLink: function (ev) {
        ev.preventDefault();
        if (this.nodeOptions.force_color || ev.shiftKey ) {
            return;
        }

        var self = this;
        var recordId = this._getBadgeId(ev.target);
        new dialogs.FormViewDialog(self, {
            res_model: self.field.relation,
            res_id: recordId,
            context: self.record.getContext(),
            title: _t('Open: ') + self.field.string,
            readonly: !self.attrs.can_write,
        }).on('write_completed', self, function () {
            self.dataset.cache[record_id].from_read = {};
            self.dataset.evict_record(record_id);
            self.render_value();
        }).open();

        ev.stopPropagation();
        return;
    },

    /**
     * @private
     * @param {MouseEvent} ev
     */
    _onOpenColorPicker: function (ev) {
        ev.preventDefault();

        if (this.nodeOptions.no_edit_color) {
            ev.stopPropagation();
            return;
        }
        var tagID = $(ev.currentTarget).parent().data('id');
        var tagColor = $(ev.currentTarget).parent().data('color');
        var tag = _.findWhere(this.value.data, { res_id: tagID });

        if (tag && this.colorField in tag.data) { // if there is a color field on the related model
            this.$color_picker = $(qweb.render('FieldMany2ManyTag.colorpicker', {
                'widget': this,
                'tag_id': tagID,
            }));

            $(ev.currentTarget).after(this.$color_picker);
            this.$color_picker.dropdown();
            this.$color_picker.attr("tabindex", 1).focus();
            if (!tagColor) {
                this.$('.custom-checkbox input').prop('checked', true);
            }
        }
    },
    /**
     * Update color based on target of ev
     * either by clicking on a color item or
     * by toggling the 'Hide in Kanban' checkbox.
     *
     * @private
     * @param {MouseEvent} ev
     */
    _onUpdateColor: function (ev) {
        ev.preventDefault();
        var $target = $(ev.currentTarget);
        var color = $target.data('color');
        var id = $target.data('id');
        var $tag = this.$(".badge[data-id='" + id + "']");
        var currentColor = $tag.data('color');
        var changes = {};

        if ($target.is('.o_hide_in_kanban')) {
            var $checkbox = $('.o_hide_in_kanban .custom-checkbox input');
            $checkbox.prop('checked', !$checkbox.prop('checked')); // toggle checkbox
            this.prevColors = this.prevColors ? this.prevColors : {};
            if ($checkbox.is(':checked')) {
                this.prevColors[id] = currentColor;
            } else {
                color = this.prevColors[id] ? this.prevColors[id] : 1;
            }
        } else if ($target.is('[class^="o_tag_color"]')) { // $target.is('o_tag_color_')
            if (color === currentColor) { return; }
        }

        changes[this.colorField] = color;

        this.trigger_up('field_changed', {
            dataPointID: _.findWhere(this.value.data, {res_id: id}).id,
            changes: changes,
            force_save: true,
        });
    },
});

return {
    FieldMany2ManyTags: relational_fields.FieldMany2ManyTags
}

});