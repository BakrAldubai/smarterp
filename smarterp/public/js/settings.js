frappe.ui.form.on('Settings Smarterp', {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button('Train Assigner', function() {frm.trigger('train')});
		}
    },
    train: function(frm) {
		frappe.call({
			method: "smarterp.assigner.autoassign.prepare_assigner_as_job",
			args: {},
			callback: function(response_json){
				frappe.msgprint(response_json)
			}
		});
    }
});