// Copyright (c) 2019, Marius Widmann
// MIT Licence

frappe.ui.form.on('Issue', {
	refresh: function (frm) {
		if (!frm.is_new()) {
			frm.add_custom_button('Assign', function() {frm.trigger('autoassign')});
		}
	},
	autoassign: function(frm){
		if (frm.is_new()) {
			show_alert(__('Save the document first.'));
			return;
		}

		frappe.call({
			method: "smarterp.assigner.autoassign.get_probabilities",
			args : {'data': {
					"frm" : JSON.stringify(frm.doc)
				}
			},
			callback: function(response){
				let probabilities = response["message"]
				let sorted = probabilities.sort((a,b) => {
					return  b["probability"] - a["probability"]
				});
				const user_id_01 = sorted[0]["name"]
				const user_id_02 = sorted[1]["name"]
				const user_id_03 = sorted[2]["name"]
				const assignment = new frappe.ui.Dialog({
					title: __('New Assignment'),
					fields: [
						
						{
							label: 'Select User',
							fieldname: 'user',
							fieldtype: 'Link',
							options: 'User', // name of doctype
							default: sorted[0]["name"]
						},
						{
							label: "Description",
							fieldname: "description",
							fieldtype: "Text",
						},
						{
							fieldtype: 'Section Break',
							fieldname: 'sb_1',
						},
						{
							fieldtype: 'HTML',
							fieldname: "chart",
						}
					],
					primary_action_label: 'Assign',
					primary_action(values){
						assignment.hide();
						console.log(values);
						let desc = " "
						if(values.hasOwnProperty("description")){
							desc = values["description"]
						}else{
							desc = "No Description"
						}
						frappe.db.insert({
							"doctype": "ToDo",
							"status": "Open",
							"priority": "Medium",
							"description": desc,
							"reference_type": frm.doc.doctype,
							"reference_name": frm.doc.name,
							"owner": values["user"]
						}).then( () => {
							frm.reload_doc();
						});
						
					}
				})
				let wrapper = $(assignment.fields_dict.chart.wrapper)
				wrapper.html('<canvas style="width: 80%;" id="chart_dom"></canvas>')
				$.getScript("https://cdn.jsdelivr.net/npm/chart.js@2.9.3/dist/Chart.min.js").done(function(){
					var options = {
						scales: {
							yAxes: [{
								display: true,
								ticks: {
									suggestedMin: 0,    // minimum will be 0, unless there is a lower value.
								}
							}]
						},
						title: {
							display: true,
							text: "This issue can likely be assigned to (percentage):"
						}
					}
					var barChart = new Chart(wrapper.find('#chart_dom')[0].getContext("2d"), {
						type: 'bar',
						data: {
							label: [sorted[0]["name"].split("@")[0],sorted[1]["name"].split("@")[0],sorted[2]["name"].split("@")[0]],
							datasets: [
								{
									label: sorted[0]["name"].split("@")[0],
									data: [sorted[0]["probability"].toFixed(2)*100],
									backgroundColor: ['rgba(106, 150, 125,0.8)']
								},
								{
									label: sorted[1]["name"].split("@")[0],
									data: [sorted[1]["probability"].toFixed(2)*100],
									backgroundColor: ['rgba(215, 180, 50,0.8)']
								},
								{
									label: sorted[2]["name"].split("@")[0],
									data: [sorted[2]["probability"].toFixed(2)*100],
									backgroundColor: ['rgba(217, 105, 65,0.8)']
								}
							]
						},
						options: options
					});
					//console.log(sorted)
					assignment.$wrapper.find('.modal-dialog').css("width","30%");
					assignment.show();
				})
			}
		});
	},
});
